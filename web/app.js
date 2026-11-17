// The page. The build itself runs in worker.js; this only handles the files and the choices.
import { osOf, groupsFor, resolve, dependents, cpu, clashes } from "./engine/builder.js";

const $ = (id) => document.getElementById(id);
const LEGEND = {
  STABLE: "Has run on a real Syntakt for many builds without an open issue.",
  BETA: "Runs on a real Syntakt, but was changed recently or still has checks open.",
  EXPERIMENTAL: "Checked in an emulator; not yet confirmed on a real Syntakt. Keep a backup and the official OS at hand.",
};
const state = { cat: null, stock: null, stockName: "", osv: null, mode: "stock", chosen: new Set(), manifest: null,
                built: null };

const catalogP = fetch("catalog.json", { cache: "no-store" }).then((r) => {
  if (!r.ok) throw new Error("catalog.json missing");
  return r.json();
});

// ---- step 1: the OS file
function pickFile(input, drop, onFile) {
  drop.addEventListener("click", (e) => { if (e.target.tagName !== "A") input.click(); });
  drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  input.addEventListener("change", () => input.files[0] && onFile(input.files[0]));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("hover"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("hover"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault(); drop.classList.remove("hover");
    if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]);
  });
}

pickFile($("file"), $("drop"), async (f) => {
  const cat = (state.cat = await catalogP);
  const bytes = new Uint8Array(await f.arrayBuffer());
  const osv = await osOf(cat, bytes);
  $("osname").textContent = f.name;
  state.built = null; $("result").hidden = true; $("err").hidden = true;
  if (!osv) {
    state.stock = null; state.osv = null;
    $("osmsg").innerHTML = '<span class="bad">✗ Not an official Syntakt OS ' + Object.keys(cat.oses).join(" / ") +
      " file.</span> Use the unmodified file from elektron.se (a modded or renamed file won't match).";
    refresh();
    return;
  }
  state.stock = bytes; state.stockName = f.name; state.osv = osv;
  $("osmsg").innerHTML = `<span class="ok">✓ Recognised: official Syntakt OS ${osv}</span>`;
  if (cat.version) $("ver").textContent = "Mods version " + cat.version;
  renderMods();
  refresh();
});

// ---- step 2: the mods
function renderMods() {
  const cat = state.cat, osv = state.osv;
  const groups = groupsFor(cat, osv);
  if (!state.chosen.size) for (const g of groups) if (g.default) state.chosen.add(g.id);
  const box = $("mods");
  box.textContent = "";
  for (const g of groups) {
    const row = document.createElement("div");
    row.className = "mod";
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.id = "g-" + g.id;
    cb.checked = !!g.locked || state.chosen.has(g.id);
    cb.disabled = !!g.locked;
    cb.addEventListener("change", () => {
      if (cb.checked) state.chosen.add(g.id);
      else { state.chosen.delete(g.id); for (const d of dependents(cat, g.id)) state.chosen.delete(d); }
      renderMods(); refresh();
    });
    const body = document.createElement("div");
    const lab = document.createElement("label");
    lab.htmlFor = cb.id; lab.textContent = g.label;
    const info = (g.info || "").replace(/^TEST\w+\.\s*/, "");          // drop the internal test label
    const first = info.split(/(?<=\.)\s/)[0];
    const d = document.createElement("div"); d.className = "d"; d.textContent = first;
    body.append(lab, d);
    if (info.length > first.length) {
      const det = document.createElement("details");
      const sum = document.createElement("summary"); sum.textContent = "More";
      const p = document.createElement("p"); p.textContent = info;
      det.append(sum, p); body.append(det);
    }
    const badge = document.createElement("span");
    badge.className = "badge " + g.status; badge.textContent = g.status; badge.title = LEGEND[g.status] || "";
    row.append(cb, body, badge);
    box.append(row);
  }
  const sel = resolve(cat, state.chosen, osv);
  const c = cpu(cat, sel);
  $("cpu").textContent = `Estimated audio CPU: ${c.idle_pct.toFixed(1)} % at rest, up to ${c.busy_pct.toFixed(1)} % with everything engaged (stock ${c.stock_pct.toFixed(1)} %). An estimate from the emulator.`;
  const leg = $("legend"); leg.textContent = "";
  for (const [k, v] of Object.entries(LEGEND)) {
    const b = document.createElement("span"); b.className = "badge " + k; b.textContent = k;
    const t = document.createElement("span"); t.textContent = v;
    leg.append(b, t);
  }
}

for (const [id, mode] of [["tab-stock", "stock"], ["tab-max", "max"]]) {
  $(id).addEventListener("click", () => {
    state.mode = mode;
    $("tab-stock").setAttribute("aria-selected", mode === "stock");
    $("tab-max").setAttribute("aria-selected", mode === "max");
    $("pane-stock").hidden = mode !== "stock";
    $("pane-max").hidden = mode !== "max";
    refresh();
  });
}

pickFile($("mfile"), $("mdrop"), async (f) => {
  $("mname").textContent = f.name;
  try {
    const m = JSON.parse(await f.text());
    if (m.format !== 1 || !Array.isArray(m.mods)) throw new Error("not a MAX manifest (format 1)");
    state.manifest = m;
    const okOs = state.osv && m.os === state.osv;
    $("mmsg").innerHTML = okOs
      ? `<span class="ok">✓ ${escapeHtml(m.name || "MAX")} for OS ${escapeHtml(m.os)}, ${m.mods.length} mods</span>`
      : `<span class="bad">✗ This manifest is for OS ${escapeHtml(m.os)}; step 1 has ${state.osv ? "OS " + state.osv : "no OS file yet"}.</span>`;
  } catch (e) {
    state.manifest = null;
    $("mmsg").innerHTML = `<span class="bad">✗ ${escapeHtml(e.message)}</span>`;
  }
  refresh();
});

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---- step 3: build and save
function ready() {
  if (!state.stock) return "Pick your OS file first.";
  if (state.mode === "stock") {
    const sel = resolve(state.cat, state.chosen, state.osv);
    const cl = clashes(state.cat, sel);
    if (cl.length) return `${cl[0][0]} and ${cl[0][1]} can't be in one build.`;
    if (![...sel].some((g) => !state.cat.groups.find((x) => x.id === g).locked)) return "Tick at least one mod.";
    return "";
  }
  if (!state.manifest) return "Drop your MAX manifest in step 2.";
  if (state.manifest.os !== state.osv) return "The manifest and the OS file are for different OS versions.";
  return "";
}

let busy = false;
function refresh() {
  $("s2").classList.toggle("off", !state.stock);
  $("s3").classList.toggle("off", !state.stock);
  const why = ready();
  $("build").disabled = busy || !!why;
  if (!busy && !state.built) $("status").textContent = why || "Ready. Building takes about half a minute (a minute when adding to MAX).";
}

$("build").addEventListener("click", () => {
  busy = true; state.built = null; refresh();
  $("result").hidden = true; $("err").hidden = true; $("notes").textContent = "";
  $("bar").style.width = "0";
  const w = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
  const stockCopy = state.stock.slice().buffer;
  w.postMessage({ mode: state.mode, stock: stockCopy, groups: [...state.chosen], manifest: state.manifest,
                  tripwire: $("mtrip").checked }, [stockCopy]);
  w.onmessage = ({ data }) => {
    if (data.type === "progress") {
      $("status").textContent = data.text;
      $("bar").style.width = Math.round(100 * data.frac) + "%";
    } else if (data.type === "note") {
      const li = document.createElement("li"); li.textContent = data.text; $("notes").append(li);
    } else if (data.type === "done") {
      busy = false; w.terminate();
      state.built = { bytes: new Uint8Array(data.bytes), sha256: data.sha256, os: data.os,
                      name: outName(data.os) };
      $("status").textContent = "Done. Every patch guard passed, no byte is patched twice, and the boot margin is safe.";
      $("rinfo").textContent = (state.cat.version ? state.cat.version + ", " : "") + `OS ${data.os}, boot margin ${data.margin.toLocaleString()} bytes` + (data.known ? `, known build: ${data.known}` : "");
      $("rsha").textContent = data.sha256;
      $("result").hidden = false;
      refresh();
    } else if (data.type === "error") {
      busy = false; w.terminate();
      $("bar").style.width = "0";
      $("status").textContent = "Nothing was built.";
      $("err").textContent = "Refused: " + data.text; $("err").hidden = false;
      refresh();
    }
  };
  w.onerror = (e) => {
    busy = false; w.terminate();
    $("err").textContent = "The builder stopped unexpectedly: " + (e.message || "unknown error"); $("err").hidden = false;
    refresh();
  };
});

function outName(osv) {
  const trip = state.mode === "max" ? $("mtrip").checked : state.chosen.has("tripwire");
  const base = state.mode === "max" ? "Syntakt_MAX_PerfMods" : (state.chosen.has("perfmods") ? "Syntakt_PerfMods" : "Syntakt_custom");
  return `${base}_OS${osv}${trip ? "_tripwire" : ""}.syx`;
}

$("save").addEventListener("click", () => {
  const b = state.built;
  if (!b) return;
  const url = URL.createObjectURL(new Blob([b.bytes], { type: "application/octet-stream" }));
  const a = document.createElement("a");
  a.href = url; a.download = b.name;
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
});

refresh();
