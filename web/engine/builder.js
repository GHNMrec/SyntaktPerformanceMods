// The builder core, ported from builder/max_custom.py and addon/perfmods_addon.py.
// Same catalog, same order, same guards; the tests check it gives the same bytes as the Python builder.
// Runs in a Web Worker in the page, or in Node for the tests. Nothing here talks to a network or a device.
import { compress } from "./lz.js";
import { runWasi } from "./wasi.js";

export const LOAD = 0x40000400, MIN_MARGIN = 4096, S7_LIMIT = 393208;
const PATCHABLE = new Set([3, 7]);
const COUNT_OFF = 0x1C, TABLE_OFF = 0x20, ENTRY = 16, SRC = 0x40200000, DST = 0x40000400;

export class BuildError extends Error {}

const clone = (x) => JSON.parse(JSON.stringify(x));
const hexToBytes = (h) => {
  h = h.replace(/ /g, "");
  const out = new Uint8Array(h.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(h.substr(2 * i, 2), 16);
  return out;
};
const bytesToHex = (b) => Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
const intOf = (x) => (typeof x === "string" ? parseInt(x, 16) : x);

export async function sha256(bytes) {
  const d = await crypto.subtle.digest("SHA-256", bytes);
  return bytesToHex(new Uint8Array(d));
}

// ---- the firmware container tool (elektron-firmware-tool, WebAssembly)

export class Eft {
  constructor(module) { this.module = module; }
  static async load(wasmBytes) { return new Eft(await WebAssembly.compile(wasmBytes)); }
  run(args, files) {
    const r = runWasi(this.module, args, files);
    if (r.code) throw new BuildError("firmware container tool failed: " + (r.stderr.trim() || r.stdout.trim()));
    return r;
  }
  info(syx) {
    const out = this.run(["-i", "/w/in.syx"], new Map([["/w/in.syx", syx]])).stdout;
    const f = {};
    for (const m of out.matchAll(/^(device|version|container|checksums)\s*:\s*(.*)$/gm)) f[m[1]] = m[2].trim();
    return f;
  }
  unpack(syx, ids) {
    const args = ["-i", "/w/in.syx"];
    for (const s of ids) args.push("-d", String(s));
    const r = this.run([...args, "-o", "/w/out"], new Map([["/w/in.syx", syx]]));
    const ans = {};
    for (const s of ids) {
      const m = [...r.files.keys()].filter((k) => k.startsWith(`/w/out/section_${s}_`));
      if (m.length !== 1) throw new BuildError(`container did not unpack section ${s}`);
      ans[s] = r.files.get(m[0]);
    }
    return ans;
  }
  repack(syx, sections, level = 3) {
    const files = new Map([["/w/in.syx", syx]]);
    const args = ["-i", "/w/in.syx", "-l", String(level)];
    for (const sid of Object.keys(sections).map(Number).sort((a, b) => a - b)) {
      files.set(`/w/s${sid}.bin`, sections[sid]);
      args.push("-c", String(sid), `/w/s${sid}.bin`);
    }
    return this.run([...args, "-o", "/w/out.syx"], files).files.get("/w/out.syx");
  }
  container(syx) {
    return this.run(["-i", "/w/in.syx", "--emit-container", "/w/c.bin"], new Map([["/w/in.syx", syx]]))
      .files.get("/w/c.bin");
  }
}

// ---- selection (max_custom.py)

export async function osOf(cat, bytes) {
  const h = await sha256(bytes);
  return Object.keys(cat.oses).find((v) => cat.oses[v].stock_sha256 === h) || null;
}

export function groupsFor(cat, osv) {
  return cat.groups.filter((g) => (g.os || Object.keys(cat.oses)).includes(osv));
}

export function resolve(cat, chosen, osv) {
  const groups = Object.fromEntries(groupsFor(cat, osv).map((g) => [g.id, g]));
  const out = new Set(Object.keys(groups).filter((g) => groups[g].locked));
  for (const c of chosen) if (groups[c]) out.add(c);
  const todo = [...out];
  while (todo.length) {
    for (const r of groups[todo.pop()].requires || []) {
      if (!out.has(r)) { out.add(r); todo.push(r); }
    }
  }
  return out;
}

export function rivals(cat, gid) {
  const g = cat.groups.find((x) => x.id === gid) || {};
  const out = new Set(g.excludes || []);
  for (const h of cat.groups) if ((h.excludes || []).includes(gid)) out.add(h.id);
  return out;
}

export function clashes(cat, groups) {
  const seen = new Set(), out = [];
  for (const g of groups) for (const r of rivals(cat, g)) if (groups.has(r)) {
    const pair = [g, r].sort(), k = pair.join("|");
    if (!seen.has(k)) { seen.add(k); out.push(pair); }
  }
  return out.sort();
}

export function dependents(cat, gid) {
  const out = new Set();
  let changed = true;
  while (changed) {
    changed = false;
    for (const g of cat.groups) {
      const req = g.requires || [];
      if (!out.has(g.id) && (req.includes(gid) || req.some((r) => out.has(r)))) { out.add(g.id); changed = true; }
    }
  }
  return out;
}

const RANK = ["STABLE", "BETA", "EXPERIMENTAL"];
export function worstStatus(cat, groups, osv) {
  const st = cat.groups.filter((g) => groups.has(g.id)).map((g) => g.status);
  if (osv) st.push(...variantNotes(cat, groups, osv).map((v) => v[1]));
  return st.reduce((a, b) => (RANK.indexOf(b) > RANK.indexOf(a) ? b : a), "STABLE");
}

export function cpu(cat, groups) {
  const budget = cat.stock_block / (cat.stock_pct / 100);
  const sel = cat.groups.filter((g) => groups.has(g.id));
  const idle = sel.reduce((a, g) => a + g.idle, 0), busy = sel.reduce((a, g) => a + g.busy, 0);
  const pct = (extra) => (100 * (cat.stock_block + extra)) / budget;
  return { idle_pct: pct(idle), busy_pct: pct(busy), stock_pct: cat.stock_pct };
}

export function withCompat(mod, records, present) {
  mod = clone(mod);
  for (const r of records) {
    if (!present.has(r.when)) continue;
    const p = mod.patches.find((p) => p.addr === r.patch);
    const k = 2 * r.offset;
    if (p.hex.slice(k, k + r.old.length) !== r.old) throw new BuildError(`${mod.name}: compat record for ${r.when} does not match`);
    p.hex = p.hex.slice(0, k) + r.new + p.hex.slice(k + r.new.length);
  }
  return mod;
}

export function choose(cat, groups, osv) {
  const o = cat.oses[osv];
  const names = new Set();
  for (const g of groupsFor(cat, osv)) if (groups.has(g.id)) for (const m of g.mods) names.add(m);
  const flags = Object.fromEntries(cat.groups.map((g) => [g.id, groups.has(g.id)]));
  const out = [];
  for (const n of o.order) {
    if (!names.has(n)) continue;
    let mod = o.mods[n], rec = null;
    for (const v of o.variants[n] || []) {
      if (Object.entries(v.when).every(([k, x]) => flags[k] === x)) { mod = v.mod ?? null; rec = v; break; }
    }
    if (mod !== null && mod !== undefined) out.push([mod, rec]);
  }
  return out;
}

export function variantNotes(cat, groups, osv) {
  return choose(cat, groups, osv).filter(([, r]) => r && r.status).map(([m, r]) => [m.name, r.status, r.why]);
}

export function modList(cat, groups, osv) {
  for (const [a, b] of clashes(cat, groups)) throw new BuildError(`${a} and ${b} can't be in one build: pick one`);
  const o = cat.oses[osv];
  const out = choose(cat, groups, osv).map(([m]) => m);
  const present = new Set(out.map((m) => m.name));
  const by = Object.fromEntries(out.map((m) => [m.name, m]));
  out.forEach((m, i) => {
    if (!m.x_links) return;
    m = clone(m);
    for (const ln of m.x_links) {
      const [mod, sym] = ln.symbol.split(":");
      if (!by[mod]) throw new BuildError(`${m.name} links ${mod}, which is not in this build`);
      const p = m.patches[ln.patch], k = 2 * ln.offset;
      const v = (parseInt(by[mod][ln.field || "symbols"][sym], 16) + (ln.add || 0)) >>> 0;
      p.hex = p.hex.slice(0, k) + v.toString(16).padStart(8, "0") + p.hex.slice(k + 8);
    }
    out[i] = m;
  });
  out.forEach((m, i) => { if ((o.compat || {})[m.name]) out[i] = withCompat(m, o.compat[m.name], present); });
  for (const m of out) for (const r of m.requires || []) {
    if (!present.has(r)) throw new BuildError(`${m.name} needs ${r}, which is not in this build`);
  }
  return out;
}

export function knownBuild(cat, osv, sha) {
  return ((cat.oses[osv].known || []).find((k) => k.sha256 === sha) || {}).name || null;
}

// ---- build (guarded apply / SHLZ / repack / boot margin)

export async function apply(sections, mods, osv) {
  const patches = [];
  for (const mod of mods) {
    if (mod.os !== osv) throw new BuildError(`${mod.name}: written for OS ${mod.os}, not ${osv}`);
    for (const p of mod.patches) patches.push([mod.name, p]);
  }
  const seen = { 3: [], 7: [] }, stockLen = { 3: sections[3].length, 7: sections[7].length }, decoded = [];
  for (const [name, p] of patches) {
    const sid = Number(p.section);
    if (!PATCHABLE.has(sid)) throw new BuildError(`${name}: protected or unsupported section ${sid}`);
    const data = "hex" in p ? hexToBytes(p.hex || "") : new TextEncoder().encode(p.ascii);
    if (data.length !== p.len) throw new BuildError(`${name}: patch length mismatch`);
    const off = parseInt(p.addr, 16) - LOAD, end = off + data.length, append = !!p.append;
    if (append && off < stockLen[sid]) throw new BuildError(`${name}: append overlaps stock`);
    if (!append) {
      if (off < 0 || end > stockLen[sid]) throw new BuildError(`${name}: patch is outside stock section`);
      if ((await sha256(sections[sid].slice(off, end))) !== p.expect_sha256.toLowerCase())
        throw new BuildError(`${name}: stock patch guard rejected input`);
    }
    for (const [a, b, other] of seen[sid]) if (off < b && a < end) throw new BuildError(`${name}: overlaps ${other}`);
    seen[sid].push([off, end, name]); decoded.push([sid, off, end, data]);
  }
  for (const [sid, off, end, data] of decoded) {
    if (end > sections[sid].length) {
      const grown = new Uint8Array(end); grown.set(sections[sid]); sections[sid] = grown;
    }
    sections[sid].set(data, off);
  }
  if (sections[7].length > S7_LIMIT)
    throw new BuildError(`voice-CPU section too long: ${sections[7].length} B (the OS takes at most ${S7_LIMIT})`);
}

export function readStream(container) {
  const dv = new DataView(container.buffer, container.byteOffset, container.byteLength);
  const count = dv.getUint32(COUNT_OFF);
  for (let k = 0; k < count; k++) {
    const at = TABLE_OFF + ENTRY * k;
    const sid = dv.getUint32(at), off = dv.getUint32(at + 4), clen = dv.getUint32(at + 8);
    if (sid === 3) return container.slice(off, off + clen);
  }
  throw new BuildError("section 3 is missing");
}

export function margin(stream) {
  let ip = 8, op = 0, tag = 0, last = 1, worst = 2 ** 40;
  const END = {};
  const at = (i) => { if (i >= stream.length) throw END; return stream[i]; };
  const bit = () => {
    tag = (tag << 1) & 0xFFFF;
    if (!(tag & 0xFF)) { const by = at(ip); ip++; tag = (by << 1) | 1; return by >> 7; }
    return (tag >> 8) & 1;
  };
  const gamma = () => { let v = 1; for (;;) { v = (v << 1) + bit(); if (bit()) return v; } };
  try {
    while (ip < stream.length) {
      if (bit()) { ip++; op++; }
      else {
        const g = gamma();
        let off;
        if (g === 2) off = last;
        else {
          off = (g << 8) + at(ip); ip++;
          if (off === 767) break;
          off -= 767; last = off;
        }
        let length = 2 * bit() + bit();
        length = length ? length : gamma() + 2;
        if (off > 3328) length += 1;
        op += length + 1;
      }
      worst = Math.min(worst, (SRC - DST) + ip - op);
    }
  } catch (e) { if (e !== END) throw e; }
  return worst;
}

export async function assemble(eft, stock, mods, osv, progress = () => {}) {
  progress(`Validating firmware container (OS ${osv})`, 0.02);
  const meta = eft.info(stock);
  if (!(meta.device || "").includes("Syntakt") || meta.version !== osv || meta.checksums !== "ok")
    throw new BuildError("container validation failed");
  progress("Unpacking the OS", 0.05);
  const sections = eft.unpack(stock, [3, 7]);
  progress(`Applying ${mods.length} mods`, 0.1);
  await apply(sections, mods, osv);
  const layout = (mods.find((m) => (m.layout || {}).compress === "shlz") || {}).layout;
  if (!layout) throw new BuildError("mod-area layout missing (modarea not selected)");
  const img = parseInt(layout.img, 16), size = parseInt(layout.size, 16), off = img - LOAD;
  const area = sections[3].slice(off);
  if (area.length > size) throw new BuildError("mod area exceeds its reserved heap block");
  progress("Compressing the mod area", 0.15);
  const packed = compress(area);
  const s3 = new Uint8Array(off + packed.length); s3.set(sections[3].subarray(0, off)); s3.set(packed, off);
  sections[3] = s3;
  progress("Repacking the OS (this takes about half a minute)", 0.2);
  const cand = eft.repack(stock, sections, 3);
  progress("Verifying the output", 0.95);
  const built = eft.info(cand);
  if (built.checksums !== "ok" || built.version !== osv) throw new BuildError("output container checks failed");
  const m = margin(readStream(eft.container(cand)));
  if (m < MIN_MARGIN) throw new BuildError(`section 3 boot margin unsafe: ${m} bytes`);
  const sha = await sha256(cand);
  progress("Complete", 1);
  return { bytes: cand, sha256: sha, margin: m };
}

export async function build(eft, cat, stock, chosen, progress) {
  const osv = await osOf(cat, stock);
  if (!osv) throw new BuildError("this file is not an official Syntakt OS " + Object.keys(cat.oses).join(" / ") + " image");
  const groups = resolve(cat, chosen, osv);
  const mods = modList(cat, groups, osv);
  const r = await assemble(eft, stock, mods, osv, progress);
  return { ...r, os: osv, groups: [...groups].sort(), mods: mods.map((m) => m.name),
           status: worstStatus(cat, groups, osv), notes: variantNotes(cat, groups, osv),
           known: knownBuild(cat, osv, r.sha256) };
}

// ---- the add-on: put the Performance Mods on somebody's MAX manifest (perfmods_addon.py)

const JOG = "tempojog-nolink", PF = "perf-filter", OURS = [JOG, PF, "tempojog"];

function areaMap(mods, layout) {
  const img = intOf(layout.img), out = [];
  for (const m of mods) for (const p of m.patches) if (Number(p.section) === 3 && p.append) {
    const a = intOf(p.addr) - img; out.push([a, a + p.len, m.name]);
  }
  return out.sort((x, y) => x[0] - y[0] || x[1] - y[1]);
}

function u32(v) { return [(v >>> 24) & 255, (v >>> 16) & 255, (v >>> 8) & 255, v & 255]; }

function swapModarea(mods, ours) {
  const theirs = mods.find((m) => m.name === "modarea");
  if (!theirs) throw new BuildError("the manifest has no modarea mod, so there is no mod area to put the jog in");
  for (const k of ["img", "ram", "heap_block", "compress"]) {
    if (theirs.layout[k] !== ours.layout[k])
      throw new BuildError(`modarea layout differs in ${k} (${theirs.layout[k]} vs ${ours.layout[k]}): this is not the area the jog was built for`);
  }
  if (JSON.stringify(theirs.symbols) !== JSON.stringify(ours.symbols))
    throw new BuildError("modarea symbols differ: not the area the jog was built for");
  if (intOf(theirs.layout.size) >= intOf(ours.layout.size))
    return `already large enough (0x${intOf(theirs.layout.size).toString(16).toUpperCase()})`;
  const a = theirs.patches, b = ours.patches;
  const shape = (ps) => JSON.stringify(ps.map((p) => [p.addr.toUpperCase(), p.len]));
  if (shape(a) !== shape(b)) throw new BuildError("modarea patches are laid out differently");
  const ram = intOf(theirs.layout.ram), so = intOf(theirs.layout.size), sn = intOf(ours.layout.size);
  const swaps = [[u32(ram + so), u32(ram + sn), 2], [u32(so + 0x10), u32(sn + 0x10), 1]];
  const patched = clone(theirs);
  const data = hexToBytes(patched.patches[0].hex);
  for (const [old, neu, n] of swaps) {
    const at = [];
    for (let i = 0; i < data.length - 3; i++) if (old.every((x, k) => data[i + k] === x)) at.push(i);
    if (at.length !== n) throw new BuildError(`expected ${n} x ${bytesToHex(old)} in the area loader, found ${at.length}`);
    for (const i of at) data.set(neu, i);
  }
  patched.patches[0].hex = bytesToHex(data);
  if (patched.patches.some((x, i) => x.hex !== b[i].hex)) throw new BuildError("modarea loaders differ in more than the area size");
  theirs.patches = patched.patches;
  theirs.layout = clone(ours.layout);
  theirs.description = ((theirs.description || "") + " [area made 128 KB for the jog]").trim();
  return "64 KB -> 128 KB (the loader's three size constants only)";
}

export function merge(manifest, cat, tripwire = false, notes = () => {}) {
  const osv = manifest.os;
  if (!cat.oses[osv]) throw new BuildError(`this add-on has the jog for OS ${Object.keys(cat.oses).join(" / ")}, the manifest is OS ${osv}`);
  const o = cat.oses[osv];
  const mods = clone(manifest.mods);
  const names = new Set(mods.map((m) => m.name));
  const want = [...(names.has("master-filter") ? [] : [PF]), JOG, ...(tripwire ? ["tripwire"] : [])];
  for (const n of [...OURS, ...(tripwire ? ["tripwire"] : [])])
    if (names.has(n)) throw new BuildError(`the manifest already has a mod called ${n}`);
  if (names.has("master-filter")) notes("master-filter is in this build: PERFORM drives it (perf-filter not added)");
  notes("modarea: " + swapModarea(mods, o.mods.modarea));
  const layout = mods.find((m) => m.name === "modarea").layout;
  const before = areaMap(mods, layout);
  const top = before.reduce((a, [, b]) => Math.max(a, b), 0);
  for (const n of want) {
    const m = clone(o.mods[n]);
    for (const r of m.requires || []) if (!names.has(r) && !want.includes(r)) throw new BuildError(`${n} needs ${r}`);
    mods.push(m);
  }
  const present = new Set(mods.map((m) => m.name));
  mods.forEach((m, i) => {
    const rec = (o.compat || {})[m.name];
    if (!rec) return;
    mods[i] = withCompat(m, rec, present);
    const linked = rec.map((r) => r.when).filter((w) => present.has(w)).sort();
    if (linked.length) notes(`${m.name}: PERFORM linked to ${[...new Set(linked)].join(" / ")}`);
  });
  const after = areaMap(mods, layout);
  const size = intOf(layout.size);
  const jogLo = Math.min(...after.filter(([, , n]) => want.includes(n)).map(([a]) => a));
  if (jogLo < top) throw new BuildError(`the jog's chunks start at +0x${jogLo.toString(16)}, inside the other mods' area (+0x${top.toString(16)})`);
  notes(`mod area: other mods end at +0x${top.toString(16)}; the jog's chunks run +0x${jogLo.toString(16)}..+0x${Math.max(...after.map(([, b]) => b)).toString(16)} of +0x${size.toString(16)}`);
  return [osv, mods];
}

export async function checkManifest(manifest, stock) {
  if (manifest.format !== 1) throw new BuildError("only MAX manifests of format 1 are understood");
  if ((await sha256(stock)) !== manifest.stock_sha256)
    throw new BuildError("this OS file is not the official one this manifest was made for (SHA-256 differs)");
}
