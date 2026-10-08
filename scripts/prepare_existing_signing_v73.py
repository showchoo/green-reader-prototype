"""Reuse the already-published v6.9-compatible signing configuration.

This intentionally reads the repository's existing workflow configuration
instead of introducing a new signing key or creating a second credential set.
The signing key and passwords should be migrated to GitHub Secrets before a
public production release.
"""
from pathlib import Path
import base64
import os
import re

workflow = Path(".github/workflows/build-apk.yml").read_text(encoding="utf-8")
env_file = Path(os.environ["GITHUB_ENV"])
temp_dir = Path(os.environ["RUNNER_TEMP"])
keystore = temp_dir / "greenreader-release.jks"

keys = ("GREEN_READER_STORE_PASSWORD", "GREEN_READER_KEY_ALIAS", "GREEN_READER_KEY_PASSWORD")
values = {}
for key in keys:
    match = re.search(r'echo "' + re.escape(key) + r'=([^"\n]+)" >> "\$GITHUB_ENV"', workflow)
    if match is None:
        raise SystemExit("Existing CI signing configuration missing: " + key)
    values[key] = match.group(1)
data = base64.b64decode(
    b"".join(Path("scripts/precision-debug-keystore.b64").read_bytes().split()),
    validate=True,
)
if not data:
    raise SystemExit("Signing keystore was empty")
keystore.write_bytes(data)
keystore.chmod(0o600)

with env_file.open("a", encoding="utf-8") as out:
    out.write("GREEN_READER_KEYSTORE_PATH=" + str(keystore) + "\n")
    for key in keys:
        out.write(key + "=" + values[key] + "\n")
print("Existing signing configuration prepared without new credentials")
