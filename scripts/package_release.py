"""Create a clean ZIP without credentials, caches, virtualenvs or QA temp files."""
from pathlib import Path
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
target = Path(sys.argv[1]).resolve()
if root == target or root in target.parents:
    raise SystemExit("Store the release ZIP outside the source tree.")
excluded_dirs = {".git", ".venv", ".verify-venv", ".pytest_cache", "__pycache__", "tmp", "sapphire-preview"}
target.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
    for file in sorted(root.rglob("*")):
        rel = file.relative_to(root)
        if not file.is_file() or excluded_dirs.intersection(rel.parts):
            continue
        if file.name in {".env", ".DS_Store"} or file.suffix in {".pyc", ".pyo"} or file.name.startswith(".env.") and file.name != ".env.example":
            continue
        archive.write(file, str(Path(root.name) / rel))
with zipfile.ZipFile(target) as archive:
    if archive.testzip() is not None:
        raise SystemExit("Archive integrity check failed")
    print(f"{target}: {len(archive.namelist())} files, {target.stat().st_size} bytes; CRC OK")
