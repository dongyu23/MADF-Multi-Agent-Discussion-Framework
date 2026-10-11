"""Push experiment artifacts to the research branch via GitHub API.

git clone/push is blocked on this machine (Xcode license), so we build the
commit tree with the API: blob -> tree -> commit -> update ref.
Pure stdlib (urllib). Usage: python push_to_branch.py <local_dir> <branch>
"""

import base64
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "dongyu23/MADF-Multi-Agent-Discussion-Framework"
API = "https://api.github.com"
TOK = subprocess.run(["gh", "auth", "token"], capture_output=True,
                     text=True, check=True).stdout.strip()


def api(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{API}{path}", data=data, method=method,
        headers={"Authorization": f"Bearer {TOK}",
                 "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"API error {e.code}: {e.read()[:300]}")
        raise


def main(local_dir: str, branch: str, message: str):
    root = Path(local_dir)
    ref = api("GET", f"/repos/{REPO}/git/ref/heads/{branch}")
    base_commit = ref["object"]["sha"]
    base_tree = api("GET",
                    f"/repos/{REPO}/git/commits/{base_commit}")["tree"]["sha"]

    tree_items = []
    for f in sorted(root.rglob("*")):
        if f.is_file() and "__pycache__" not in str(f) and ".venv" not in str(f):
            rel = str(f.relative_to(root))
            blob = api("POST", f"/repos/{REPO}/git/blobs",
                       {"content": base64.b64encode(f.read_bytes()).decode(),
                        "encoding": "base64"})
            tree_items.append({"path": rel, "mode": "100644",
                               "type": "blob", "sha": blob["sha"]})
            print(f"  + {rel}")

    tree = api("POST", f"/repos/{REPO}/git/trees",
               {"base_tree": base_tree, "tree": tree_items})
    commit = api("POST", f"/repos/{REPO}/git/commits",
                 {"message": message, "tree": tree["sha"],
                  "parents": [base_commit]})
    api("PATCH", f"/repos/{REPO}/git/refs/heads/{branch}",
        {"sha": commit["sha"]})
    print(f"Pushed {len(tree_items)} files to {branch}: {commit['sha'][:10]}")


if __name__ == "__main__":
    local, branch = sys.argv[1], sys.argv[2]
    msg = sys.argv[3] if len(sys.argv) > 3 else "research artifacts"
    main(local, branch, msg)
