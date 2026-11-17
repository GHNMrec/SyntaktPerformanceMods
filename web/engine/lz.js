// SHLZ codec: a line-for-line port of builder/lz.py (the mod-area compressor the OS's area loader unpacks).
// It must give the same bytes as the Python one; the tests compare them.
const MIN = 3, MAX_LEN = 130, MAX_LIT = 128, WINDOW = 0xFFFF;

export function compress(data) {
  const n = data.length;
  const out = [];
  let lits = [];
  const heads = new Map();                               // 3-byte key -> positions (ascending)
  const key = (k) => (data[k] << 16) | (data[k + 1] << 8) | data[k + 2];
  const flush = () => {
    for (let k = 0; k < lits.length; k += MAX_LIT) {
      const c = lits.slice(k, k + MAX_LIT);
      out.push(c.length - 1);
      for (const b of c) out.push(b);
    }
    lits = [];
  };
  let i = 0;
  while (i < n) {
    let bestLen = 0, bestOff = 0;
    if (i + MIN <= n) {
      const list = heads.get(key(i)) || [];
      const from = Math.max(0, list.length - 64);
      for (let q = list.length - 1; q >= from; q--) {    // reversed(heads[key][-64:])
        const j = list[q];
        if (i - j > WINDOW) break;
        let length = MIN;
        while (length < MAX_LEN && i + length < n && data[j + length] === data[i + length]) length++;
        if (length > bestLen) {
          bestLen = length; bestOff = i - j;
          if (length === MAX_LEN) break;
        }
      }
    }
    const step = bestLen >= MIN ? bestLen : 1;
    const stop = Math.min(i + step, n - MIN + 1);
    for (let k = i; k < stop; k++) {
      const kk = key(k);
      let l = heads.get(kk);
      if (!l) { l = []; heads.set(kk, l); }
      l.push(k);
    }
    if (bestLen >= MIN) {
      flush();
      out.push(0x80 | (bestLen - MIN), (bestOff >> 8) & 0xFF, bestOff & 0xFF);
    } else {
      lits.push(data[i]);
    }
    i += step;
  }
  flush();
  const body = Uint8Array.from(out);
  const res = new Uint8Array(12 + body.length);
  res.set([0x53, 0x48, 0x4C, 0x5A]);                     // "SHLZ"
  const dv = new DataView(res.buffer);
  dv.setUint32(4, n); dv.setUint32(8, body.length);
  res.set(body, 12);
  return res;
}
