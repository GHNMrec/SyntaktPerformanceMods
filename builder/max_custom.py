"""Syntakt MAX custom builder core (v2): pick mods from resources/catalog.json, build a .syx from YOUR official
OS 1.41 or OS 1.42 file (recognised by its SHA-256). Offline; it never sends anything to a device. Same guards as the MAX 1.0 builder: stock hash,
container checks, guarded patches (each patch checks the stock bytes it replaces), sections 2 and 6 never
touched, mod area size, boot margin >= 4096."""
from __future__ import annotations
import hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path
import lz

LOAD = 0x40000400; PATCHABLE = {3, 7}; MIN_MARGIN = 4096
S7_LIMIT = 393_208          # the main CPU takes section 7 only while its length + 5 <= 393,216 (0x40082D66)
COUNT_OFF, TABLE_OFF, ENTRY = 0x1C, 0x20, 16; SRC, DST = 0x40200000, 0x40000400


class BuildError(RuntimeError):
    pass


def here() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def catalog() -> dict:
    return json.loads((here() / "resources" / "catalog.json").read_text(encoding="utf-8"))


def digest_path(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def eft() -> Path:
    env = os.environ.get("EFT_BIN")                 # an explicit path wins (the tests and Linux use it)
    exe = Path(env) if env else here() / "resources" / ("elektron-firmware-tool.exe" if os.name == "nt"
                                                          else "elektron-firmware-tool")
    if not exe.is_file():
        raise BuildError(f"{exe.name} is missing: copy it into builder/resources (see README: SETUP), "
                         "or point EFT_BIN at it")
    return exe


def run_eft(*args) -> str:
    p = subprocess.run([str(eft()), *map(str, args)], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if p.returncode:
        raise BuildError("firmware container tool failed: " + (p.stderr.strip() or p.stdout.strip()))
    return p.stdout


def info(p) -> dict:
    f = dict(re.findall(r"^(device|version|container|checksums)\s*:\s*(.*)$", run_eft("-i", p), re.M))
    return {k: v.strip() for k, v in f.items()}


# ---- selection

def os_of(cat: dict, path) -> str | None:
    """the OS version whose official file this is, by SHA-256; None if it is not one of them."""
    h = digest_path(path)
    return next((v for v, o in cat["oses"].items() if o["stock_sha256"] == h), None)


def groups_for(cat: dict, osv: str) -> list[dict]:
    return [g for g in cat["groups"] if osv in g.get("os", list(cat["oses"]))]


def resolve(cat: dict, chosen: set[str], osv: str) -> set[str]:
    """chosen group ids + locked groups + everything they require (transitively), on this OS."""
    groups = {g["id"]: g for g in groups_for(cat, osv)}
    out = {g for g in groups if groups[g].get("locked")} | (set(chosen) & set(groups))
    todo = list(out)
    while todo:
        for r in groups[todo.pop()].get("requires", []):
            if r not in out:
                out.add(r)
                todo.append(r)
    return out


def rivals(cat: dict, gid: str) -> set[str]:
    """groups that can't be in one build with gid (its "excludes", and the groups that exclude it)"""
    g = next((g for g in cat["groups"] if g["id"] == gid), {})
    return set(g.get("excludes", [])) | {h["id"] for h in cat["groups"] if gid in h.get("excludes", [])}


def clashes(cat: dict, groups: set[str]) -> list[tuple[str, str]]:
    """pairs of selected groups that exclude each other (e.g. the JOG page with and without LINK)"""
    return sorted({tuple(sorted((g, r))) for g in groups for r in rivals(cat, g) if r in groups})


def dependents(cat: dict, gid: str) -> set[str]:
    """groups that need gid (transitively)."""
    out, changed = set(), True
    while changed:
        changed = False
        for g in cat["groups"]:
            if g["id"] not in out and (gid in g.get("requires", []) or out & set(g.get("requires", []))):
                out.add(g["id"])
                changed = True
    return out


def worst_status(cat: dict, groups: set[str], osv: str | None = None) -> str:
    """the least proven label among the selected groups and the variants the selection uses"""
    rank = ["STABLE", "BETA", "EXPERIMENTAL"]
    st = [g["status"] for g in cat["groups"] if g["id"] in groups]
    if osv:
        st += [s for _, s, _ in variant_notes(cat, groups, osv)]
    return max(st, key=rank.index, default="STABLE")


def cpu(cat: dict, groups: set[str]) -> dict:
    """estimated audio-interrupt share (percent of the CPU) idle and with every selected effect engaged."""
    budget = cat["stock_block"] / (cat["stock_pct"] / 100)
    sel = [g for g in cat["groups"] if g["id"] in groups]
    idle = sum(g["idle"] for g in sel)
    busy = sum(g["busy"] for g in sel)
    pct = lambda extra: 100 * (cat["stock_block"] + extra) / budget  # noqa: E731
    return {"idle_pct": pct(idle), "busy_pct": pct(busy), "stock_pct": cat["stock_pct"],
            "idle_ui": 100 - pct(idle), "busy_ui": 100 - pct(busy), "stock_ui": 100 - cat["stock_pct"]}


def _with_compat(mod: dict, records: list[dict], present: set[str]) -> dict:
    """a copy of mod with each compat record applied whose owner is in the build."""
    mod = json.loads(json.dumps(mod))
    for r in records:
        if r["when"] not in present:
            continue
        p = next(p for p in mod["patches"] if p["addr"] == r["patch"])
        k = 2 * r["offset"]
        if p["hex"][k:k + len(r["old"])] != r["old"]:
            raise BuildError(f"{mod['name']}: compat record for {r['when']} does not match")
        p["hex"] = p["hex"][:k] + r["new"] + p["hex"][k + len(r["new"]):]
    return mod


def choose(cat: dict, groups: set[str], osv: str) -> list[tuple[dict, dict | None]]:
    """(mod, the variant record it came from or None) for every mod of the selected groups, in build order.
    A variant applies when every group it names is in (True) or out (False) of the selection; first match wins."""
    o = cat["oses"][osv]
    names = {m for g in groups_for(cat, osv) if g["id"] in groups for m in g["mods"]}
    flags = {g["id"]: g["id"] in groups for g in cat["groups"]}
    out = []
    for n in o["order"]:
        if n not in names:
            continue
        mod, rec = o["mods"][n], None
        for v in o["variants"].get(n, []):
            if all(flags.get(k) == x for k, x in v["when"].items()):
                mod, rec = v.get("mod"), v
                break
        if mod is not None:                                       # TEST35a: a "skip" variant leaves the mod out
            out.append((mod, rec))
    return out


def variant_notes(cat: dict, groups: set[str], osv: str) -> list[tuple[str, str, str]]:
    """(mod, status, why) for every variant this selection uses that carries a status of its own."""
    return [(m["name"], r["status"], r["why"]) for m, r in choose(cat, groups, osv) if r and r.get("status")]


def mod_list(cat: dict, groups: set[str], osv: str) -> list[dict]:
    for a, b in clashes(cat, groups):
        raise BuildError(f"{a} and {b} can't be in one build: pick one")
    o = cat["oses"][osv]
    out = [m for m, _ in choose(cat, groups, osv)]
    present = {m["name"] for m in out}
    by = {m["name"]: m for m in out}
    for i, m in enumerate(out):                                   # link sites: another mod's symbol, by name
        if m.get("x_links"):
            m = json.loads(json.dumps(m))
            for ln in m["x_links"]:
                mod, sym = ln["symbol"].split(":")
                if mod not in by:
                    raise BuildError(f"{m['name']} links {mod}, which is not in this build")
                p = m["patches"][ln["patch"]]
                k = 2 * ln["offset"]
                v = int(by[mod][ln.get("field", "symbols")][sym], 16) + ln.get("add", 0)
                p["hex"] = p["hex"][:k] + f"{v & 0xFFFFFFFF:08x}" + p["hex"][k + 8:]
            out[i] = m
    for i, m in enumerate(out):
        if m["name"] in o.get("compat", {}):
            out[i] = _with_compat(m, o["compat"][m["name"]], present)
    for m in out:                                                 # every mod's own requirements are in the build
        for r in m.get("requires", []):
            if r not in present:
                raise BuildError(f"{m['name']} needs {r}, which is not in this build")
    return out


def known_build(cat: dict, osv: str, sha: str) -> str | None:
    return next((k["name"] for k in cat["oses"][osv].get("known", []) if k["sha256"] == sha), None)


# ---- build (the MAX 1.0 builder's guarded apply / SHLZ / repack / margin)

def unpack(syx, outdir: Path, ids) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    args = ["-i", syx]
    for sid in ids:
        args += ["-d", str(sid)]
    run_eft(*args, "-o", outdir)
    ans = {}
    for sid in ids:
        m = list(outdir.glob(f"section_{sid}_*"))
        if len(m) != 1:
            raise BuildError(f"container did not unpack section {sid}")
        ans[sid] = m[0]
    return ans


def read_stream(syx) -> bytes:
    with tempfile.TemporaryDirectory(prefix="max-container-", dir=Path(syx).parent) as d:
        c = Path(d) / "container.bin"
        run_eft("-i", syx, "--emit-container", c)
        data = c.read_bytes()
    count = int.from_bytes(data[COUNT_OFF:COUNT_OFF + 4], "big")
    for k in range(count):
        at = TABLE_OFF + ENTRY * k
        sid, off, clen, _ = (int.from_bytes(data[at + i:at + i + 4], "big") for i in range(0, 16, 4))
        if sid == 3:
            return data[off:off + clen]
    raise BuildError("section 3 is missing")


def margin(syx) -> int:
    stream = read_stream(syx); ip = 8; op = tag = 0; last = 1; worst = 1 << 40

    def bit():
        nonlocal tag, ip
        tag = (tag << 1) & 0xFFFF
        if not tag & 0xFF:
            by = stream[ip]; ip += 1; tag = (by << 1) | 1
            return by >> 7
        return (tag >> 8) & 1

    def gamma():
        v = 1
        while True:
            v = (v << 1) + bit()
            if bit():
                return v
    try:
        while ip < len(stream):
            if bit():
                ip += 1; op += 1
            else:
                g = gamma()
                if g == 2:
                    off = last
                else:
                    off = (g << 8) + stream[ip]; ip += 1
                    if off == 767:
                        break
                    off -= 767; last = off
                length = 2 * bit() + bit()
                length = length if length else gamma() + 2
                if off > 3328:
                    length += 1
                op += length + 1
            worst = min(worst, (SRC - DST) + ip - op)
    except IndexError:
        pass
    return worst


def apply(sections: dict, mods: list[dict], osv: str) -> None:
    patches = []
    for mod in mods:
        if mod.get("os") != osv:
            raise BuildError(f"{mod.get('name')}: written for OS {mod.get('os')}, not {osv}")
        patches += [(mod["name"], p) for p in mod["patches"]]
    seen = {sid: [] for sid in PATCHABLE}; stock_len = {sid: len(x) for sid, x in sections.items()}; decoded = []
    for name, p in patches:
        sid = p["section"]
        if sid not in PATCHABLE:
            raise BuildError(f"{name}: protected or unsupported section {sid}")
        data = bytes.fromhex(p.get("hex", "").replace(" ", "")) if "hex" in p else p["ascii"].encode("ascii")
        if len(data) != p["len"]:
            raise BuildError(f"{name}: patch length mismatch")
        off = int(p["addr"], 16) - LOAD; end = off + len(data); append = p.get("append", False)
        if append and off < stock_len[sid]:
            raise BuildError(f"{name}: append overlaps stock")
        if not append:
            if off < 0 or end > stock_len[sid]:
                raise BuildError(f"{name}: patch is outside stock section")
            if hashlib.sha256(sections[sid][off:end]).hexdigest() != p["expect_sha256"].lower():
                raise BuildError(f"{name}: stock patch guard rejected input")
        for a, b, other in seen[sid]:
            if off < b and a < end:
                raise BuildError(f"{name}: overlaps {other}")
        seen[sid].append((off, end, name)); decoded.append((sid, off, end, data))
    for sid, off, end, data in decoded:
        if end > len(sections[sid]):
            sections[sid].extend(b"\0" * (end - len(sections[sid])))
        sections[sid][off:end] = data
    if len(sections[7]) > S7_LIMIT:
        raise BuildError(f"voice-CPU section too long: {len(sections[7])} B (the OS takes at most {S7_LIMIT})")


def assemble(stock, destination, mods: list[dict], osv: str, progress=lambda _: None) -> tuple[str, int]:
    """apply `mods` (already resolved, in build order) to the official `stock` file and write `destination`.
    Returns (sha256, boot margin). The add-on uses this directly with another MAX's mod list."""
    stock = Path(stock); destination = Path(destination)
    progress(f"Validating firmware container (OS {osv})"); meta = info(stock)
    if "Syntakt" not in meta.get("device", "") or meta.get("version") != osv or meta.get("checksums") != "ok":
        raise BuildError("container validation failed")
    if destination.suffix.lower() != ".syx":
        destination = destination.with_suffix(".syx")
    if destination.exists():
        raise BuildError("destination already exists; choose a new filename")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".maxc-", dir=destination.parent) as td:
        td = Path(td); files = unpack(stock, td / "stock", [3, 7])
        sections = {k: bytearray(v.read_bytes()) for k, v in files.items()}
        progress(f"Applying {len(mods)} mods"); apply(sections, mods, osv)
        layout = next((m["layout"] for m in mods if m.get("layout", {}).get("compress") == "shlz"), None)
        if not layout:
            raise BuildError("mod-area layout missing (modarea not selected)")
        img = int(layout["img"], 16); size = int(layout["size"], 16); off = img - LOAD
        area = bytes(sections[3][off:])
        if len(area) > size:
            raise BuildError("mod area exceeds its reserved heap block")
        del sections[3][off:]; sections[3].extend(lz.compress(area))
        repl = {}
        for sid, data in sections.items():
            p = td / f"section_{sid}.bin"; p.write_bytes(data); repl[sid] = p
        cand = td / "candidate.syx"; progress("Repacking firmware container"); args = ["-i", stock, "-l", "3"]
        for sid, p in sorted(repl.items()):
            args += ["-c", str(sid), p]
        run_eft(*args, "-o", cand); progress("Verifying output"); built = info(cand)
        if built.get("checksums") != "ok" or built.get("version") != osv:
            raise BuildError("output container checks failed")
        m = margin(cand)
        if m < MIN_MARGIN:
            raise BuildError(f"section 3 boot margin unsafe: {m} bytes")
        got = digest_path(cand)
        cand.replace(destination)
    progress("Complete")
    return got, m


def build(stock, destination, groups: set[str], progress=lambda _: None) -> dict:
    cat = catalog()
    stock = Path(stock); destination = Path(destination)
    osv = os_of(cat, stock)
    if not osv:
        raise BuildError("selected file is not an official Syntakt OS " + " / ".join(cat["oses"]) + " image")
    groups = resolve(cat, groups, osv)
    mods = mod_list(cat, groups, osv)
    if destination.suffix.lower() != ".syx":
        destination = destination.with_suffix(".syx")
    got, m = assemble(stock, destination, mods, osv, progress)
    return {"output": str(destination), "sha256": got, "boot_margin": m, "mods": [x["name"] for x in mods],
            "groups": sorted(groups), "os": osv, "status": worst_status(cat, groups, osv),
            "notes": variant_notes(cat, groups, osv),
            "known": known_build(cat, osv, got)}
