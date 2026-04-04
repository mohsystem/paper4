import requests

# ==============================
# CONFIG
# ==============================

import os
import sys
import requests

API = "https://api.github.com"
GITHUB_TOKEN = ""


def die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    sys.exit(code)

def gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def get_username(headers: dict) -> str:
    r = requests.get(f"{API}/user", headers=headers, timeout=30)
    if r.status_code == 401:
        die("401 Bad credentials. Your GITHUB_TOKEN is invalid/revoked or pasted incorrectly.")
    if r.status_code != 200:
        die(f"Failed to read /user: {r.status_code} {r.text}")
    return r.json()["login"]

def repo_exists(owner: str, name: str, headers: dict) -> bool:
    r = requests.get(f"{API}/repos/{owner}/{name}", headers=headers, timeout=30)
    if r.status_code == 200:
        return True
    if r.status_code == 404:
        return False
    if r.status_code == 401:
        die("401 Bad credentials while checking repos. Token issue.")
    die(f"Unexpected response checking repo {owner}/{name}: {r.status_code} {r.text}")

def create_repo(name: str, headers: dict) -> str:
    payload = {"name": name, "private": False, "auto_init": True}
    r = requests.post(f"{API}/user/repos", json=payload, headers=headers, timeout=30)

    if r.status_code == 201:
        return "created"
    if r.status_code == 422:
        return "exists"
    if r.status_code == 401:
        die("401 Bad credentials while creating repos. Token issue.")
    return f"error {r.status_code}: {r.text}"

def main():
    token = GITHUB_TOKEN
    if not token:
        die("Missing GITHUB_TOKEN env var. Set it first, then rerun.")

    headers = gh_headers(token)
    owner = get_username(headers)
    base_url = f"https://github.com/{owner}"

    # Create 42 repos
    for i in range(1, 15):
        n = f"{i:02d}"
        for suffix in ("pre", "post", "api"):
            repo = f"study-{n}-{suffix}"
            status = create_repo(repo, headers)
            print(f"{repo}: {status}", file=sys.stderr)

    # Print markdown table (4 columns)
    print()
    print("| number | pre | post | API |")
    print("|---:|---|---|---|")
    for i in range(1, 15):
        n = f"{i:02d}"
        pre = f"llm-study-{n}-pre"
        post = f"llm-study-{n}-post"
        api = f"llm-study-{n}-api"
        print(
            f"| {n} | [{pre}]({base_url}/{pre}) | [{post}]({base_url}/{post}) | [{api}]({base_url}/{api}) |"
        )

if __name__ == "__main__":
    main()