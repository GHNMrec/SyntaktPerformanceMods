// A tiny in-memory WASI (preview 1) for elektron-firmware-tool compiled to wasm32-wasi.
// Only the 13 calls the tool imports. Files live in a Map (path -> Uint8Array); nothing touches the disk or the
// network. One instance per run.

const E = { SUCCESS: 0, BADF: 8, EXIST: 20, INVAL: 28, ISDIR: 31, NOENT: 44, NOTDIR: 54 };
const FT = { CHAR: 2, DIR: 3, FILE: 4 };
const O = { CREAT: 1, DIRECTORY: 2, EXCL: 4, TRUNC: 8 };

class ExitTrap extends Error {
  constructor(code) { super(`exit ${code}`); this.code = code; }
}

export function runWasi(module, args, input) {
  // input: Map of absolute path ("/w/x.syx") -> Uint8Array. Returns every file afterwards (inputs + written).
  const files = new Map([...input].map(([k, v]) => [k, { buf: v, len: v.length }]));
  const dirs = new Set(["/", "/w"]);
  for (const p of files.keys()) {
    const parts = p.split("/");
    for (let i = 2; i < parts.length; i++) dirs.add(parts.slice(0, i).join("/"));
  }
  const fds = new Map();
  fds.set(0, { kind: "in" });
  fds.set(1, { kind: "out", chunks: [] });
  fds.set(2, { kind: "out", chunks: [] });
  fds.set(3, { kind: "dir", path: "/w", pre: "/w" });
  let nextFd = 4;
  let mem;
  const dec = new TextDecoder(), enc = new TextEncoder();
  const view = () => new DataView(mem.buffer);
  const u8 = () => new Uint8Array(mem.buffer);
  const str = (p, n) => dec.decode(u8().slice(p, p + n));
  const argv = ["eft", ...args].map((a) => enc.encode(a + "\0"));

  const join = (base, rel) => {
    const out = base.split("/").filter(Boolean);
    for (const s of rel.split("/")) {
      if (!s || s === ".") continue;
      if (s === "..") out.pop(); else out.push(s);
    }
    return "/" + out.join("/");
  };

  const imports = {
    args_sizes_get(pc, ps) {
      view().setUint32(pc, argv.length, true);
      view().setUint32(ps, argv.reduce((n, a) => n + a.length, 0), true);
      return E.SUCCESS;
    },
    args_get(pv, pb) {
      let at = pb;
      argv.forEach((a, i) => { view().setUint32(pv + 4 * i, at, true); u8().set(a, at); at += a.length; });
      return E.SUCCESS;
    },
    fd_prestat_get(fd, p) {
      const f = fds.get(fd);
      if (!f || !f.pre) return E.BADF;
      view().setUint8(p, 0); view().setUint32(p + 4, enc.encode(f.pre).length, true);
      return E.SUCCESS;
    },
    fd_prestat_dir_name(fd, p, n) {
      const f = fds.get(fd);
      if (!f || !f.pre) return E.BADF;
      u8().set(enc.encode(f.pre).slice(0, n), p);
      return E.SUCCESS;
    },
    fd_fdstat_get(fd, p) {
      const f = fds.get(fd);
      if (!f) return E.BADF;
      const v = view();
      v.setUint8(p, f.kind === "dir" ? FT.DIR : f.kind === "file" ? FT.FILE : FT.CHAR);
      v.setUint16(p + 2, 0, true);
      v.setBigUint64(p + 8, 0xFFFFFFFFFFFFFFFFn, true);
      v.setBigUint64(p + 16, 0xFFFFFFFFFFFFFFFFn, true);
      return E.SUCCESS;
    },
    fd_fdstat_set_flags() { return E.SUCCESS; },
    path_create_directory(fd, p, n) {
      const f = fds.get(fd);
      if (!f || f.kind !== "dir") return E.BADF;
      const path = join(f.path, str(p, n));
      if (dirs.has(path) || files.has(path)) return E.EXIST;
      dirs.add(path);
      return E.SUCCESS;
    },
    path_open(fd, _dirflags, p, n, oflags, _rb, _ri, fdflags, out) {
      const f = fds.get(fd);
      if (!f || f.kind !== "dir") return E.BADF;
      const path = join(f.path, str(p, n));
      if (dirs.has(path)) {
        if (oflags & (O.CREAT | O.TRUNC)) return E.ISDIR;
        fds.set(nextFd, { kind: "dir", path });
      } else {
        if (oflags & O.DIRECTORY) return files.has(path) ? E.NOTDIR : E.NOENT;
        if (!files.has(path)) {
          if (!(oflags & O.CREAT)) return E.NOENT;
          const parent = path.slice(0, path.lastIndexOf("/")) || "/";
          if (!dirs.has(parent)) return E.NOENT;
          files.set(path, { buf: new Uint8Array(0), len: 0 });
        } else if (oflags & O.EXCL) return E.EXIST;
        if (oflags & O.TRUNC) files.set(path, { buf: new Uint8Array(0), len: 0 });
        fds.set(nextFd, { kind: "file", path, pos: 0, append: !!(fdflags & 1) });
      }
      view().setUint32(out, nextFd++, true);
      return E.SUCCESS;
    },
    fd_close(fd) { return fds.delete(fd) ? E.SUCCESS : E.BADF; },
    fd_seek(fd, off, whence, out) {
      const f = fds.get(fd);
      if (!f || f.kind !== "file") return E.BADF;
      const size = files.get(f.path).len;
      const base = whence === 0 ? 0 : whence === 1 ? f.pos : size;
      const np = base + Number(off);
      if (np < 0) return E.INVAL;
      f.pos = np;
      view().setBigUint64(out, BigInt(np), true);
      return E.SUCCESS;
    },
    fd_read(fd, iovs, cnt, out) {
      const f = fds.get(fd);
      if (!f) return E.BADF;
      if (f.kind !== "file") { view().setUint32(out, 0, true); return E.SUCCESS; }
      const st = files.get(f.path);
      let total = 0;
      for (let i = 0; i < cnt; i++) {
        const ptr = view().getUint32(iovs + 8 * i, true), len = view().getUint32(iovs + 8 * i + 4, true);
        const take = Math.max(0, Math.min(len, st.len - f.pos));
        u8().set(st.buf.subarray(f.pos, f.pos + take), ptr);
        f.pos += take; total += take;
        if (take < len) break;
      }
      view().setUint32(out, total, true);
      return E.SUCCESS;
    },
    fd_write(fd, iovs, cnt, out) {
      const f = fds.get(fd);
      if (!f) return E.BADF;
      let total = 0;
      for (let i = 0; i < cnt; i++) {
        const ptr = view().getUint32(iovs + 8 * i, true), len = view().getUint32(iovs + 8 * i + 4, true);
        const chunk = u8().slice(ptr, ptr + len);
        total += len;
        if (f.kind === "out") { f.chunks.push(chunk); continue; }
        if (f.kind !== "file") return E.BADF;
        const st = files.get(f.path);
        if (f.append) f.pos = st.len;
        const end = f.pos + len;
        if (end > st.buf.length) {                       // grow by doubling: the tool writes in small pieces
          const grown = new Uint8Array(Math.max(end, 2 * st.buf.length, 4096));
          grown.set(st.buf.subarray(0, st.len)); st.buf = grown;
        }
        st.buf.set(chunk, f.pos); f.pos = end; st.len = Math.max(st.len, end);
      }
      view().setUint32(out, total, true);
      return E.SUCCESS;
    },
    proc_exit(code) { throw new ExitTrap(code); },
  };

  const instance = new WebAssembly.Instance(module, { wasi_snapshot_preview1: imports });
  mem = instance.exports.memory;
  let code = 0;
  try { instance.exports._start(); } catch (e) {
    if (e instanceof ExitTrap) code = e.code; else throw e;
  }
  const text = (fd) => dec.decode(concat(fds.get(fd).chunks));
  const out = new Map([...files].map(([k, v]) => [k, v.buf.slice(0, v.len)]));
  return { code, stdout: text(1), stderr: text(2), files: out, dirs };
}

function concat(chunks) {
  const n = chunks.reduce((a, c) => a + c.length, 0), out = new Uint8Array(n);
  let at = 0;
  for (const c of chunks) { out.set(c, at); at += c.length; }
  return out;
}
