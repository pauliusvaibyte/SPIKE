"""One-off audit: verify data_snapshot files against SNAPSHOT_MANIFEST.json."""
import hashlib
import json
import sys
from pathlib import Path

snap = Path(__file__).resolve().parent.parent / "data_snapshot"
man = json.loads((snap / "SNAPSHOT_MANIFEST.json").read_text())
ok = bad = miss = 0
extra = {str(p.relative_to(snap)) for p in snap.rglob("*") if p.is_file()}
extra.discard("SNAPSHOT_MANIFEST.json")
for f in man["files"]:
    p = snap / f["path"].replace("\\", "/")
    extra.discard(str(p.relative_to(snap)))
    if not p.exists():
        miss += 1
        print("MISSING:", f["path"])
        continue
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if h == f["sha256"] and p.stat().st_size == f["bytes"]:
        ok += 1
    else:
        bad += 1
        print("MISMATCH:", f["path"])
print(f"verified ok={ok} mismatch={bad} missing={miss} of n_files={man['n_files']}")
print(f"extra files not in manifest: {len(extra)}")
for e in sorted(extra):
    print("  EXTRA:", e)
sys.exit(0 if bad == 0 and miss == 0 else 1)
