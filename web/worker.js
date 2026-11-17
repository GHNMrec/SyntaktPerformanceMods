// Runs the build off the page's main thread. Everything stays in this tab: no network, no device.
import * as B from "./engine/builder.js";

let eftP = null, catP = null;
const eft = () => (eftP ??= fetch(new URL("./engine/eft.wasm", import.meta.url), { cache: "no-store" }).then((r) => {
  if (!r.ok) throw new B.BuildError("could not load the firmware tool (eft.wasm)");
  return r.arrayBuffer();
}).then((b) => B.Eft.load(b)));
const catalog = () => (catP ??= fetch(new URL("./catalog.json", import.meta.url), { cache: "no-store" }).then((r) => r.json()));

const post = (type, data = {}, transfer = []) => self.postMessage({ type, ...data }, transfer);

self.onmessage = async ({ data }) => {
  try {
    const [tool, cat] = await Promise.all([eft(), catalog()]);
    const stock = new Uint8Array(data.stock);
    const progress = (text, frac) => post("progress", { text, frac });
    let res;
    if (data.mode === "stock") {
      res = await B.build(tool, cat, stock, new Set(data.groups), progress);
    } else {
      const man = data.manifest;
      await B.checkManifest(man, stock);
      if (man.golden_sha256) {
        const base = await B.assemble(tool, stock, man.mods, man.os,
          (t, f) => progress("Step 1/2, rebuilding your MAX as it is: " + t, f / 2));
        if (base.sha256 !== man.golden_sha256)
          throw new B.BuildError("your MAX does not rebuild to its own golden hash from this OS file, so nothing was added");
        post("note", { text: "Your MAX rebuilt byte for byte (matches its golden hash)." });
      } else {
        post("note", { text: "This manifest has no golden hash, so the rebuild check was skipped." });
      }
      const [osv, mods] = B.merge(man, cat, !!data.tripwire, (t) => post("note", { text: t }));
      res = await B.assemble(tool, stock, mods, osv,
        (t, f) => progress((man.golden_sha256 ? "Step 2/2, adding the Performance Mods: " : "") + t,
          man.golden_sha256 ? 0.5 + f / 2 : f));
      res.os = osv; res.known = null;
    }
    post("done", { bytes: res.bytes.buffer, sha256: res.sha256, margin: res.margin, os: res.os, known: res.known },
      [res.bytes.buffer]);
  } catch (e) {
    post("error", { text: e instanceof B.BuildError ? e.message : "Unexpected error: " + (e && e.message || e) });
  }
};
