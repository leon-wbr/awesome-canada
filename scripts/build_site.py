"""Build the GitHub Pages view of README.md, with a prefilled "report broken link" link per entry,
plus the social image and a sitemap beside it.

Usage: python3 scripts/build_site.py README.md site/index.html
"""

import os
import re
import shutil
import sys
from html import escape
from urllib.parse import urlencode

REPO = os.environ.get("GITHUB_REPOSITORY", "leon-wbr/awesome-canada")
OWNER, NAME = REPO.split("/")
SITE = f"https://{OWNER}.github.io/{NAME}/"
IMAGE = "media/social.png"
SKIP = {"Contents", "Contributing"}
ENTRY = re.compile(r"^- \[([^\]]+)\]\(([^)]+)\) - (.+)$")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
HEADER_IMAGE = re.compile(r'<img [^>]*alt="([^"]+)"')

STYLE = """
:root { --red:#c8102e; --ink:#1d1d1f; --muted:#5b5b66; --line:#e3e1dc; }
* { box-sizing:border-box; }
body { margin:0; background:#faf9f6; color:var(--ink); font:16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
main { max-width:860px; margin:0 auto; padding:40px 20px 80px; }
h1 { font-size:34px; margin:0 0 8px; } h1 span { color:var(--red); }
h2 { font-size:20px; margin:40px 0 10px; padding-top:16px; border-top:1px solid var(--line); }
a { color:#0b57d0; }
nav { display:flex; flex-wrap:wrap; gap:6px 14px; font-size:14px; margin:20px 0; }
.help { display:flex; flex-wrap:wrap; gap:10px; margin:20px 0; }
.help a { background:#fff; border:1px solid var(--line); border-radius:6px; padding:6px 12px; text-decoration:none; font-size:14px; }
ul { list-style:none; padding:0; margin:0; }
li { padding:8px 0; border-bottom:1px solid var(--line); } li:last-child { border:0; }
li > a:first-child { font-weight:600; }
.report { font-size:13px; color:var(--muted); margin-left:6px; white-space:nowrap; }
p.lead { font-size:18px; color:var(--muted); margin:0; }
"""


def inline(text):
    return LINK.sub(lambda m: f'<a href="{escape(m[2])}">{m[1]}</a>', escape(text, quote=False))


def report_url(name, url):
    query = urlencode({"template": "dead-link.yml", "title": f"Dead link: {name}", "entry": name, "url": url})
    return f"https://github.com/{REPO}/issues/new?{query}"


def build(readme):
    body, nav, in_list, skip, title = [], [], False, False, None
    for line in open(readme, encoding="utf-8").read().splitlines():
        entry = ENTRY.match(line)
        if in_list and not entry:
            body.append("</ul>")
            in_list = False
        header_image = HEADER_IMAGE.search(line) if line.startswith(("<", "\t")) else None
        if line.startswith("# ") or (header_image and not title):
            title = header_image[1] if header_image else line[2:].split(" [")[0]
            body.append(f"<h1><span>🍁</span> {escape(title)}</h1>")
        elif line.startswith(("<", "\t")) or SITE in line:
            continue
        elif line.startswith("> "):
            lead = LINK.sub(r"\1", line[2:])
            body.append(f'<p class="lead">{inline(line[2:])}</p>')
        elif line.startswith("## "):
            section = line[3:].strip()
            skip = section in SKIP
            if not skip:
                anchor = re.sub(r"[^\w -]", "", section.lower()).replace(" ", "-")
                nav.append(f'<a href="#{anchor}">{escape(section)}</a>')
                body.append(f'<h2 id="{anchor}">{escape(section)}</h2>')
        elif skip or not line.strip():
            continue
        elif entry:
            name, url, description = entry.groups()
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(
                f'<li><a href="{escape(url)}">{escape(name)}</a> – {inline(description)}'
                f' <a class="report" href="{escape(report_url(name, url))}">Report broken link</a></li>'
            )
        else:
            body.append(f"<p>{inline(line)}</p>")
    if in_list:
        body.append("</ul>")
    help_links = (
        f'<div class="help"><a href="https://github.com/{REPO}/issues/new?template=dead-link.yml">Report a dead link</a>'
        f'<a href="https://github.com/{REPO}/issues/new?template=suggest-entry.yml">Suggest an entry</a>'
        f'<a href="https://github.com/{REPO}/edit/main/README.md">Edit the list</a>'
        f'<a href="https://github.com/{REPO}">GitHub</a></div>'
    )
    first = next(i for i, part in enumerate(body) if part.startswith("<h2"))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title>"
        f'<meta name="description" content="{escape(lead)}">'
        f'<link rel="canonical" href="{SITE}">'
        f'<meta property="og:type" content="website"><meta property="og:url" content="{SITE}">'
        f'<meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{escape(lead)}">'
        f'<meta property="og:image" content="{SITE}social.png"><meta property="og:image:alt" content="{escape(title)}">'
        '<meta property="og:image:width" content="1280"><meta property="og:image:height" content="640">'
        '<meta name="twitter:card" content="summary_large_image">'
        f"<style>{STYLE}</style></head><body><main>"
        + "\n".join(body[:first]) + help_links + f"<nav>{''.join(nav)}</nav>" + "\n".join(body[first:])
        + "</main></body></html>\n"
    )


if __name__ == "__main__":
    readme, out = sys.argv[1:]
    site = os.path.dirname(out) or "."
    os.makedirs(site, exist_ok=True)
    open(out, "w", encoding="utf-8").write(build(readme))
    shutil.copy(os.path.join(os.path.dirname(readme), IMAGE), os.path.join(site, "social.png"))
    open(os.path.join(site, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{SITE}</loc></url></urlset>\n'
    )
