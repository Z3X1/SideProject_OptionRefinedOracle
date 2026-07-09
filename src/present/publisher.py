#!/usr/bin/env python3
"""
[LAYER: L6 PRESENT]
職責：GitHub API 發佈：SHA-fetch→PUT 更新（dashboard wrap 驗證防裸推、狀態文件批次同步）。
"""
import requests, base64, os
TOKEN = os.environ.get("GH_TOKEN", "")
REPO  = os.environ.get("GH_REPO", "")
API   = f"https://api.github.com/repos/{REPO}/contents"
H     = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}

def get_sha(path):
    r = requests.get(
        f"https://api.github.com/repos/{REPO}/contents/{path}",
        headers=HEADERS
    )
    return r.json().get("sha") if r.status_code == 200 else None

def push_bytes(gh_path, content_bytes, message):
    sha = get_sha(gh_path)
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode()
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(
        f"https://api.github.com/repos/{REPO}/contents/{gh_path}",
        headers=HEADERS, json=payload
    )
    ok = r.status_code in [200, 201]
    print(f"{'OK' if ok else 'FAIL'} {gh_path}: {r.status_code}")
    return ok

def publish_all():
    from present.protect import wrap_password
    local = "docs/oracle/index.html"
    if os.path.exists(local):
        with open(local, "r", encoding="utf-8") as f:
            html = f.read()
        if "createObjectURL" in html and "const B64=" in html:
            protected = html
            print("HTML already wrapped, skipping wrap_password")
        else:
            protected = wrap_password(html)
            if "createObjectURL" not in protected or "const B64=" not in protected:
                print("ERROR: wrap failed, pushing raw as fallback"); protected = html
            else:
                print(f"wrap_password OK: {len(protected):,} bytes (inner: {len(html):,})")
        push_bytes("docs/oracle/index.html", protected.encode("utf-8"), "auto: GEX Oracle dashboard")
    else:
        print(f"NOT FOUND: {local}")
    for fname in ["data/oracle_market_data.json", "data/snapshot_counter.json",
                  "data/settlement_log.json", "data/skew_history.json"]:
        if os.path.exists(fname):
            with open(fname, "rb") as f:
                push_bytes(fname, f.read(), f"auto: {fname.split('/')[-1]}")

if __name__ == "__main__":
    publish_all()
