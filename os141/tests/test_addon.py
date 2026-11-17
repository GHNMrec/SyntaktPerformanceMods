"""The add-on (addon/perfmods_addon.py): Performance Mods (the jog + perf-filter) merged into another MAX's mod list,
booted through the real area loader.

Needs a MAX manifest (format 1, OS 1.41): set MAX_MANIFEST=path/to/max-1.0-manifest.json. Without it these tests skip.
- the merge: only the area size constants change in the MAX modarea, the jog's chunks sit above every MAX chunk,
  no byte is patched twice;
- the boot: section 3 with the merged mods and the compressed 128 KB area is run through the OS's own area loader
  (0x400004B2). Every chunk of every mod, MAX's and the jog's, ends up at its RAM address, the rest of the area is
  zero and the BSS around it is cleared."""
import copy
import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("unicorn")
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT.parent / "builder"), str(ROOT.parent / "addon")]
import perfmods_addon as A  # noqa: E402
import max_custom as M  # noqa: E402
import test_modarea as TM  # noqa: E402

MAN = os.environ.get("MAX_MANIFEST")
SEC3 = ROOT / "unpacked" / "Syntakt_OS1.41" / "section_3_MAIN_OS.bin"
SEC7 = next((ROOT / "unpacked" / "Syntakt_OS1.41").glob("section_7_*"), None) if (ROOT / "unpacked").exists() else None
pytestmark = pytest.mark.skipif(not (MAN and Path(MAN).exists() and SEC3.exists() and SEC7 and ROOT.name == "os141"),
                                reason="needs MAX_MANIFEST and the unpacked stock image (OS 1.41)")


@pytest.fixture(scope="module", params=[False, True], ids=["perfmods", "perfmods+tripwire"])
def merged(request):
    if request.param and not any(g["id"] == "tripwire" for g in M.catalog()["groups"]):
        pytest.skip("this build has no crash tripwire")
    man = json.loads(Path(MAN).read_text(encoding="utf-8"))
    osv, mods = A.merge(man, M.catalog(), tripwire=request.param, notes=lambda *_: None)
    return man, mods


@pytest.fixture(scope="module")
def image(merged):
    _, mods = merged
    sections = {3: bytearray(SEC3.read_bytes()), 7: bytearray(SEC7.read_bytes())}
    M.apply(sections, mods, "1.41")
    layout = next(m["layout"] for m in mods if m["name"] == "modarea")
    off = int(layout["img"], 16) - M.LOAD
    area = bytes(sections[3][off:])
    del sections[3][off:]
    sections[3].extend(M.lz.compress(area))
    return bytes(sections[3]), area


def test_only_the_area_size_changes_in_the_max_modarea(merged):
    man, mods = merged
    old = next(m for m in man["mods"] if m["name"] == "modarea")
    new = next(m for m in mods if m["name"] == "modarea")
    assert (old["layout"]["size"], new["layout"]["size"]) == ("0xfff0", "0x1fff0")
    diff = [i for p, q in zip(old["patches"], new["patches"])
            for i, (x, y) in enumerate(zip(bytes.fromhex(p["hex"]), bytes.fromhex(q["hex"]))) if x != y]
    assert len(diff) == 3                                         # RAM+SIZE twice, the heap block size once
    others = [m for m in man["mods"] if m["name"] != "modarea"]
    assert [m for m in mods if m["name"] not in ("modarea", A.JOG, A.PF, "tripwire")] == others


def test_the_jog_sits_above_every_max_chunk(merged):
    man, mods = merged
    lay = next(m["layout"] for m in mods if m["name"] == "modarea")
    spans = A.area_map(mods, lay)
    jog = [s for s in spans if s[2] in (A.JOG, A.PF, "tripwire")]
    rest = [s for s in spans if s[2] not in (A.JOG, A.PF, "tripwire")]
    assert jog and max(b for _, b, _ in rest) <= min(a for a, _, _ in jog)
    assert max(b for _, b, _ in spans) <= int(lay["size"], 16)


def test_boot_puts_every_chunk_at_its_ram_address(merged, image):
    _, mods = merged
    sec3, area = image
    uc, _ = TM.boot(sec3)
    ram = bytes(uc.mem_read(TM.RAM, TM.SIZE))
    assert ram[:len(area)] == area
    assert not any(ram[len(area):])
    for m in mods:
        for p in m["patches"]:
            if p["section"] == 3 and p.get("append"):
                at = int(p["ram"], 16)
                assert bytes(uc.mem_read(at, p["len"])) == bytes.fromhex(p["hex"]), (m["name"], hex(at))
    assert not any(uc.mem_read(TM.RAM + TM.SIZE, 0x1000))         # the BSS after the area is cleared


def test_perform_is_linked_to_perf_filter(merged):
    _, mods = merged
    by = {m["name"]: m for m in mods}
    assert A.PF in by and "master-filter" not in by
    tj = by[A.JOG]
    main = tj["patches"][0]
    k = int(tj["symbols"]["tj_mfp"], 16) - int(main["ram"], 16)
    assert int(main["hex"][2 * k:2 * k + 8], 16) == int(by[A.PF]["symbols"]["pf_p"], 16)
    sites = {int(p["addr"], 16) for m in mods for p in m["patches"] if not p.get("append") and m["name"] != A.PF}
    assert 0x400A_4F24 not in sites                              # nothing in that MAX build hooks the FX CV call
