"""Print a Markdown list of GitHub entries in README.md that are archived or have no recent commit.

Usage: GITHUB_TOKEN=... python3 scripts/stale.py README.md [days]
Prints nothing when every repo is fine.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

SKIP = {"Contents", "Unmaintained & Archived", "Contributing"}
ENTRY = re.compile(r"^- \[([^\]]+)\]\(https://github\.com/([\w.-]+)/([\w.-]+)(?:[/#][^)]*)?\)")


def entries(readme):
    section = None
    for line in open(readme, encoding="utf-8"):
        if line.startswith("## "):
            section = line[3:].strip()
        elif section not in SKIP and (m := ENTRY.match(line)):
            yield section, m.group(1), m.group(2), m.group(3)


def lookup(repos):
    fields = "isArchived defaultBranchRef { target { ... on Commit { committedDate } } }"
    query = " ".join(
        f'r{i}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{ {fields} }}'
        for i, (owner, name) in enumerate(repos)
    )
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": f"{{ {query} }}"}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}"},
    )
    with urllib.request.urlopen(request) as response:
        data = json.load(response)["data"]
    return [data[f"r{i}"] for i in range(len(repos))]


def main(readme, days=730):
    found = list(entries(readme))
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
    rows = []
    for (section, title, owner, name), repo in zip(found, lookup([(o, n) for _, _, o, n in found])):
        if repo is None:
            reason = "repository not found (renamed, deleted or private)"
        elif repo["isArchived"]:
            reason = "archived"
        else:
            last = repo["defaultBranchRef"]["target"]["committedDate"]
            if datetime.fromisoformat(last) >= cutoff:
                continue
            reason = f"last commit {last[:10]}"
        rows.append(f"- [ ] [{title}](https://github.com/{owner}/{name}) ({section}): {reason}")
    if rows:
        slug = os.environ.get("GITHUB_REPOSITORY", "leon-wbr/awesome-canada")
        print(
            f"These GitHub entries are archived or have had no commit in {days} days. "
            f"If one is still useful, move it to [Unmaintained & Archived](https://github.com/{slug}#unmaintained--archived) "
            "with the year of its last commit; otherwise remove it. Updated monthly by the stale-check workflow.\n"
        )
        print("\n".join(rows))
    print(f"Checked {len(found)} repositories, {len(rows)} flagged.", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:])
