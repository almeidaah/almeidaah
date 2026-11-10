"""Refresh a self-hosted profile card using only public GitHub data."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USERNAME = "almeidaah"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "github-stats.svg"


def github_json(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"{USERNAME}-profile-stats",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/{path}", headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        raise SystemExit(f"GitHub API request failed: HTTP {error.code} ({path})") from None
    except URLError as error:
        raise SystemExit(f"GitHub API connection failed: {error.reason}") from None


def main():
    profile = github_json(f"users/{USERNAME}")
    repositories = []
    page = 1
    while True:
        batch = github_json(
            f"users/{USERNAME}/repos?type=owner&per_page=100&page={page}"
        )
        if not isinstance(batch, list):
            raise SystemExit("GitHub API returned an invalid repository list.")
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    owned_public = [
        repo for repo in repositories if not repo["private"] and not repo["fork"]
    ]
    counts = (
        profile["public_repos"],
        sum(repo["stargazers_count"] for repo in owned_public),
        profile["followers"],
    )
    if any(type(value) is not int or value < 0 for value in counts):
        raise SystemExit("GitHub API returned an invalid statistics count.")

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    repositories_count, stars, followers = counts
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="204" viewBox="0 0 900 204" role="img" aria-labelledby="title desc">
  <title id="title">Public GitHub statistics for {USERNAME}</title>
  <desc id="desc">{repositories_count} public repositories, {stars} stars on owned non-fork public repositories, {followers} followers. Updated {updated}.</desc>
  <style>text {{ font-family: "Courier New", Courier, monospace; }}</style>
  <rect x="1" y="1" width="898" height="202" rx="8" fill="#07180f" stroke="#244733"/>
  <text x="30" y="34" fill="#67eea1" font-size="12" letter-spacing="2">GITHUB / PUBLIC SNAPSHOT</text>
  <path d="M302 58V143 M600 58V143" stroke="#244733"/>
  <g fill="#67eea1" font-size="40" font-weight="bold">
    <text x="30" y="104">{repositories_count}</text>
    <text x="332" y="104">{stars}</text>
    <text x="630" y="104">{followers}</text>
  </g>
  <g fill="#b9cbbf" font-size="12">
    <text x="30" y="133">PUBLIC REPOSITORIES</text>
    <text x="332" y="133">STARS / OWN NON-FORK REPOS</text>
    <text x="630" y="133">FOLLOWERS</text>
  </g>
  <text x="30" y="179" fill="#91ab9a" font-size="11">Updated {updated} / refreshed daily via GitHub Actions</text>
</svg>
"""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"Updated public statistics: {repositories_count} repos, {stars} stars, {followers} followers.")


if __name__ == "__main__":
    main()
