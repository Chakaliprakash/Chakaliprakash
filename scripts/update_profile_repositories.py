#!/usr/bin/env python3
"""Refresh the profile README's featured projects and repository map."""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import quote

OWNER = "Chakaliprakash"
PROFILE_REPO = f"{OWNER}/{OWNER}"
README_PATH = "README.md"
API_ROOT = "https://api.github.com"
GOLD = "C9B58A"
TEXT = "E8E1D6"
BG = "111111"

def github_get(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-repository-auto-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

def get_public_repositories():
    repos = []
    page = 1
    while True:
        url = f"{API_ROOT}/users/{OWNER}/repos?type=public&sort=updated&per_page=100&page={page}"
        batch = github_get(url)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return [
        repo for repo in repos
        if not repo.get("fork", False)
        and repo.get("full_name", "").lower() != PROFILE_REPO.lower()
        and not repo.get("archived", False)
    ]

def focus_for(repo):
    description = (repo.get("description") or "").strip()
    if description:
        return description.replace("|", "\\|").replace("\n", " ")[:140]
    language = repo.get("language")
    if language:
        return f"{language} project"
    return "Project repository"

def make_featured(repos):
    if not repos:
        return "<sub>No public repositories found yet.</sub>"
    cards = []
    for repo in repos[:4]:
        name = repo["name"]
        encoded_name = quote(name, safe="")
        url = repo["html_url"]
        image = (
            f"https://github-readme-stats.vercel.app/api/pin/?username={OWNER}"
            f"&repo={encoded_name}&hide_border=true&bg_color={BG}"
            f"&title_color={GOLD}&icon_color={GOLD}&text_color={TEXT}"
        )
        cards.append(
            f'<a href="{url}">\n'
            f'<img src="{image}" alt="{name} repository card"/>\n'
            f'</a>'
        )
    return '<div align="center">\n\n' + "\n".join(cards) + '\n\n</div>'

def make_repository_map(repos):
    if not repos:
        return "| No public repositories yet | Create your first public repository |"
    rows = ["| Repository | Focus |", "|---|---|"]
    for repo in repos:
        name = repo["name"].replace("|", "\\|")
        url = repo["html_url"]
        rows.append(f"| [{name}]({url}) | {focus_for(repo)} |")
    return "\n".join(rows)

def replace_section(text, start_marker, end_marker, replacement):
    pattern = re.compile(
        re.escape(start_marker) + r".*?" + re.escape(end_marker),
        flags=re.DOTALL,
    )
    if not pattern.search(text):
        raise RuntimeError(f"Missing README markers: {start_marker} / {end_marker}")
    return pattern.sub(
        lambda _: f"{start_marker}\n{replacement}\n{end_marker}",
        text,
        count=1,
    )

def main():
    repos = get_public_repositories()
    readme_url = f"{API_ROOT}/repos/{OWNER}/{OWNER}/contents/{README_PATH}"
    readme_data = github_get(readme_url)
    import base64
    readme = base64.b64decode(readme_data["content"]).decode("utf-8")

    updated = replace_section(
        readme,
        "<!-- AUTO-FEATURED-REPOS:START -->",
        "<!-- AUTO-FEATURED-REPOS:END -->",
        make_featured(repos),
    )
    updated = replace_section(
        updated,
        "<!-- AUTO-REPOSITORY-MAP:START -->",
        "<!-- AUTO-REPOSITORY-MAP:END -->",
        make_repository_map(repos),
    )
    if updated == readme:
        print(f"README already up to date ({len(repos)} public repositories).")
        return

    body = {
        "message": "chore: auto-update featured repositories and repository map",
        "content": __import__("base64").b64encode(updated.encode("utf-8")).decode("ascii"),
        "sha": readme_data["sha"],
        "branch": "main",
    }
    payload = json.dumps(body).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "User-Agent": "profile-repository-auto-updater",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(
        readme_url, data=payload, headers=headers, method="PUT"
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
            print(f"Updated README for {len(repos)} public repositories.")
            print(f"Commit: {result['commit']['html_url']}")
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        print(f"GitHub API update failed ({error.code}): {details}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()
