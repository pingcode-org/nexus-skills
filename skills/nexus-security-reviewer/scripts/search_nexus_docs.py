#!/usr/bin/env python3
"""
Search Nexus developer documentation at https://developer.pingcode.com.

Preferred index (when published by the docs host):
  - /llms.txt           platform / Nexus docs
  - /restapi/llms.txt   RestAPI docs

If those indexes are unavailable, fall back to sitemap.xml + HTML extraction.

Default docs site is https://developer.pingcode.com. Override with --base-url
or NEXUS_DOCS_BASE_URL when pointing at another docs host.

Examples:
    python3 -m scripts.search_nexus_docs "custom ui react"
    python3 -m scripts.search_nexus_docs manifest permissions --max-pages 3
    python3 -m scripts.search_nexus_docs "work items" --source restapi
    python3 -m scripts.search_nexus_docs "resolver" --json
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse


DEFAULT_BASE_URL = "https://developer.pingcode.com"
DEFAULT_TIMEOUT = 20
LLMS_PLATFORM_PATH = "/llms.txt"
LLMS_RESTAPI_PATH = "/restapi/llms.txt"

# Mutable module state set by configure_base_url() / main().
BASE_URL = DEFAULT_BASE_URL
SITEMAP_URL = f"{DEFAULT_BASE_URL}/sitemap.xml"
USER_AGENT = f"nexus-docs-search/1.0 (+{DEFAULT_BASE_URL})"


def configure_base_url(base_url):
    """Set docs site base URL used for index fetch and URL scoring."""
    global BASE_URL, SITEMAP_URL, USER_AGENT
    base = (base_url or DEFAULT_BASE_URL).rstrip("/")
    BASE_URL = base
    SITEMAP_URL = f"{base}/sitemap.xml"
    USER_AGENT = f"nexus-docs-search/1.0 (+{base})"


def normalize_docs_url(url):
    """Rewrite absolute URLs onto the configured BASE_URL host.

    Keep path / query / fragment; only align scheme + netloc with BASE_URL.
    Relative paths are resolved against BASE_URL.
    """
    try:
        if not url:
            return url
        absolute = urljoin(BASE_URL + "/", url)
        target = urlparse(BASE_URL)
        src = urlparse(absolute)
        if not src.scheme or not src.netloc or not target.netloc:
            return absolute
        if src.netloc == target.netloc and src.scheme == (target.scheme or src.scheme):
            return absolute
        return urlunparse(
            (
                target.scheme or src.scheme,
                target.netloc,
                src.path,
                src.params,
                src.query,
                src.fragment,
            )
        )
    except Exception:
        return url


class TextExtractor(HTMLParser):
    """Minimal HTML-to-text extractor that tracks <title> and <main>."""

    SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "header", "footer"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_depth = 0
        self.main_depth = 0
        self.in_skip = 0
        self.title_parts = []
        self.parts = []
        self._href_stack = []

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t == "title":
            self.title_depth += 1
        elif t == "main":
            self.main_depth += 1
        elif t in self.SKIP_TAGS:
            self.in_skip += 1

        if t in ("p", "div", "section", "article", "br", "li", "h1", "h2",
                 "h3", "h4", "h5", "h6", "tr", "table", "ul", "ol"):
            self.parts.append("\n")
        if t == "td" or t == "th":
            self.parts.append("\t")
        if t == "a":
            href = dict(attrs).get("href")
            self._href_stack.append(href)

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == "title" and self.title_depth:
            self.title_depth -= 1
        elif t == "main" and self.main_depth:
            self.main_depth -= 1
        elif t in self.SKIP_TAGS and self.in_skip:
            self.in_skip -= 1
        if t == "a" and self._href_stack:
            self._href_stack.pop()

    def handle_data(self, data):
        if self.in_skip:
            return
        if self.title_depth:
            self.title_parts.append(data)
        if self.main_depth > 0:
            self.parts.append(data)

    def get_title(self):
        return _normalize_whitespace("".join(self.title_parts))

    def get_text(self):
        return _normalize_whitespace("".join(self.parts))


def _normalize_whitespace(text):
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def http_get(url, timeout=DEFAULT_TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def http_get_optional(url, timeout=DEFAULT_TIMEOUT):
    """Return body text, or None on HTTP/network errors (including 404)."""
    try:
        return http_get(url, timeout=timeout)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        return None


def tokenize(query):
    return [t for t in re.split(r"[\s_\-/,.]+", query.lower()) if t]


def score_url(url, terms):
    """Score a URL against search terms using its path segments."""
    path = (urlparse(url).path or "").lower()
    segments = [s for s in re.split(r"[/\-_.]", path) if s]

    score = 0
    for term in terms:
        if term in path:
            score += 5
        for seg in segments:
            if term == seg:
                score += 10
            elif term in seg:
                score += 3
    return score


def score_text_fields(text, terms, hit_weight=8):
    score = 0
    haystack = (text or "").lower()
    for term in terms:
        if term in haystack:
            score += hit_weight
    return score


def parse_llms_index(raw, source_name):
    """Parse an llms.txt markdown index into catalog entries.

    Supports common list forms:
      - [Title](/path.md): optional description
      - [Title](https://host/path.md)
    """
    entries = []
    for line in (raw or "").splitlines():
        m = re.search(r"\[([^\]]+)\]\(([^)]+)\)", line)
        if not m:
            continue
        title = m.group(1).strip()
        href = m.group(2).strip()
        if not href:
            continue
        desc = ""
        after = line[m.end():].strip()
        if after.startswith(":"):
            desc = after[1:].strip()
        url = normalize_docs_url(href)
        entries.append(
            {
                "url": url,
                "title": title,
                "description": desc,
                "source": source_name,
                "lastmod": "",
            }
        )
    return entries


def fetch_llms_catalog(kinds):
    """Fetch and merge llms.txt catalogs for the requested kinds.

    kinds: iterable of 'platform' and/or 'restapi'
    Returns (entries, used_sources). used_sources empty means unavailable.
    """
    path_by_kind = {
        "platform": LLMS_PLATFORM_PATH,
        "restapi": LLMS_RESTAPI_PATH,
    }
    entries = []
    used = []
    for kind in kinds:
        path = path_by_kind[kind]
        raw = http_get_optional(BASE_URL + path)
        if raw is None:
            continue
        parsed = parse_llms_index(raw, kind)
        if not parsed:
            continue
        entries.extend(parsed)
        used.append(kind)
    return entries, used


def fetch_sitemap():
    """Return list of catalog dicts from the sitemap fallback."""
    raw = http_get(SITEMAP_URL)
    entries = []
    for block in re.findall(r"<url>(.*?)</url>", raw, re.S):
        loc = re.search(r"<loc>(.*?)</loc>", block, re.S)
        if not loc:
            continue
        url = normalize_docs_url(html.unescape(loc.group(1).strip()))
        lastmod = ""
        m = re.search(r"<lastmod>(.*?)</lastmod>", block, re.S)
        if m:
            lastmod = m.group(1).strip()
        entries.append(
            {
                "url": url,
                "title": "",
                "description": "",
                "source": "sitemap",
                "lastmod": lastmod,
            }
        )
    return entries


def fetch_page_meta(url):
    """Fetch a page and return (title, description, html_length)."""
    try:
        raw = http_get(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return "", "", 0

    title = ""
    m = re.search(r"<title>(.*?)</title>", raw, re.S | re.I)
    if m:
        title = html.unescape(m.group(1).strip())

    desc = ""
    m = re.search(
        r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']',
        raw, re.S | re.I,
    )
    if not m:
        m = re.search(
            r'<meta\s+[^>]*content=["\'](.*?)["\'][^>]*name=["\']description["\']',
            raw, re.S | re.I,
        )
    if m:
        desc = html.unescape(m.group(1).strip())

    return title, desc, len(raw)


def extract_text_from_html(raw_html):
    parser = TextExtractor()
    try:
        parser.feed(raw_html)
        parser.close()
    except Exception:
        pass
    return parser.get_title(), parser.get_text()


def extract_page_content(url, raw):
    """Return (title, text) for markdown or HTML bodies."""
    path = (urlparse(url).path or "").lower()
    if path.endswith(".md") or path.endswith(".markdown") or path.endswith(".txt"):
        title = ""
        for line in raw.splitlines():
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                break
        return title, _normalize_whitespace(raw)
    return extract_text_from_html(raw)


def snippet_for(text, terms, max_len=500):
    """Pick a snippet around the first term match, otherwise the beginning."""
    if not text:
        return ""
    lowered = text.lower()
    positions = []
    for term in terms:
        idx = lowered.find(term)
        if idx >= 0:
            positions.append(idx)
    if positions:
        center = min(positions)
        start = max(0, center - 150)
        end = min(len(text), center + max_len - 150)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return prefix + text[start:end].strip() + suffix
    return text[:max_len].strip()


def infer_source_kinds(query, source):
    """Map --source to llms index kinds. 'sitemap' bypasses llms."""
    if source == "sitemap":
        return []
    if source == "platform":
        return ["platform"]
    if source == "restapi":
        return ["restapi"]
    # auto
    q = (query or "").lower()
    rest_hints = (
        "restapi", "rest api", "/v1/", "/v2/", "openapi", "access_token",
        "work_item", "workitem", "scope", "oauth", "grant_type",
    )
    platform_hints = (
        "manifest", "resolver", "bridge", "nexus", "extension", "custom ui",
        "native ui", "deploy", "distribute", "webhook", "exposer",
    )
    wants_rest = any(h in q for h in rest_hints)
    wants_platform = any(h in q for h in platform_hints)
    if wants_rest and not wants_platform:
        return ["restapi", "platform"]
    if wants_platform and not wants_rest:
        return ["platform", "restapi"]
    return ["platform", "restapi"]


def score_catalog_entry(entry, terms):
    score = score_url(entry["url"], terms)
    score += score_text_fields(
        f"{entry.get('title', '')} {entry.get('description', '')}",
        terms,
        hit_weight=10,
    )
    # Prefer markdown resource pages from llms indexes when tied.
    if entry.get("source") in ("platform", "restapi"):
        score += 1
    return score


def search(query, max_pages=3, max_snippet=600, min_score=1, source="auto"):
    terms = tokenize(query)
    if not terms:
        return {"query": query, "results": [], "error": "empty query"}

    index_mode = "sitemap"
    catalog = []
    used_llms = []

    if source != "sitemap":
        kinds = infer_source_kinds(query, source)
        catalog, used_llms = fetch_llms_catalog(kinds)
        if catalog:
            index_mode = "llms:" + "+".join(used_llms)

    if not catalog:
        catalog = fetch_sitemap()
        index_mode = "sitemap"

    scored = []
    for entry in catalog:
        score = score_catalog_entry(entry, terms)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: (-x[0], x[1]["url"]))

    # For sitemap fallback, refine top URL hits with HTML title/description.
    candidates = scored[: max(max_pages * 4, 10)]
    if index_mode == "sitemap":
        refined = []
        for score, entry in candidates:
            title, desc, _ = fetch_page_meta(entry["url"])
            merged_title = title or entry.get("title", "")
            merged_desc = desc or entry.get("description", "")
            final_score = score_url(entry["url"], terms) + score_text_fields(
                f"{merged_title} {merged_desc}", terms, hit_weight=8
            )
            refined.append(
                (
                    final_score,
                    {
                        **entry,
                        "title": merged_title,
                        "description": merged_desc,
                    },
                )
            )
        refined.sort(key=lambda x: (-x[0], x[1]["url"]))
        candidates = refined

    results = []
    seen = set()
    for score, entry in candidates:
        if len(results) >= max_pages:
            break
        if score < min_score:
            continue
        url = entry["url"]
        if url in seen:
            continue
        seen.add(url)

        try:
            raw = http_get(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            results.append(
                {
                    "url": url,
                    "title": entry.get("title") or "",
                    "score": score,
                    "source": entry.get("source"),
                    "error": str(exc),
                }
            )
            continue

        page_title, text = extract_page_content(url, raw)
        final_title = page_title or entry.get("title") or ""
        body_score = 0
        lowered_text = text.lower()
        for term in terms:
            body_score += lowered_text.count(term)
        total_score = score + min(body_score, 50)

        results.append(
            {
                "url": url,
                "title": final_title,
                "description": entry.get("description") or "",
                "score": total_score,
                "source": entry.get("source"),
                "lastmod": entry.get("lastmod") or "",
                "snippet": snippet_for(text, terms, max_snippet),
                "content_length": len(text),
            }
        )

    return {
        "query": query,
        "terms": terms,
        "index": index_mode,
        "base_url": BASE_URL,
        "results": results,
    }


def format_text(result):
    lines = []
    lines.append(f"# Search: {result['query']}")
    lines.append(f"Terms: {', '.join(result['terms'])}")
    lines.append(f"Index: {result.get('index', 'unknown')}")
    lines.append(f"Base: {result.get('base_url', BASE_URL)}")
    lines.append(f"Results: {len(result['results'])}\n")
    for i, r in enumerate(result["results"], 1):
        lines.append(f"## {i}. {r.get('title') or '(no title)'}")
        lines.append(f"URL: {r['url']}")
        lines.append(f"Score: {r['score']}")
        if r.get("source"):
            lines.append(f"Source: {r['source']}")
        if r.get("lastmod"):
            lines.append(f"Last modified: {r['lastmod']}")
        if r.get("description"):
            lines.append(f"Description: {r['description']}")
        if r.get("error"):
            lines.append(f"Error: {r['error']}")
        lines.append("")
        lines.append(r.get("snippet", ""))
        lines.append("\n" + "-" * 80 + "\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Search Nexus developer documentation online "
            "(llms.txt when available, otherwise sitemap)."
        ),
    )
    parser.add_argument("query", help="Search keywords (e.g. 'custom ui react')")
    parser.add_argument(
        "--max-pages", type=int, default=3,
        help="Maximum number of pages to return (default: 3)",
    )
    parser.add_argument(
        "--max-snippet", type=int, default=600,
        help="Maximum snippet length per page (default: 600)",
    )
    parser.add_argument(
        "--source",
        choices=("auto", "platform", "restapi", "sitemap"),
        default="auto",
        help=(
            "Index selection: auto (prefer llms.txt), platform (/llms.txt), "
            "restapi (/restapi/llms.txt), or sitemap (force sitemap fallback)"
        ),
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("NEXUS_DOCS_BASE_URL", DEFAULT_BASE_URL),
        help="Docs site base URL (default: https://developer.pingcode.com; "
             "override with NEXUS_DOCS_BASE_URL)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    configure_base_url(args.base_url)

    try:
        result = search(
            args.query,
            args.max_pages,
            args.max_snippet,
            source=args.source,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_text(result))

    if not result["results"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
