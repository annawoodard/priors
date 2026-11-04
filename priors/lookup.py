"""Look papers up in OpenAlex (and arXiv), for ingest, citation checks and mentor mode.

Usage:
  priors lookup get <doi | arxiv:ID | W-id>       metadata and abstract, as YAML
  priors lookup match "<title>" [--year Y]         best title matches, with similarity
  priors lookup search "<query>" [--from Y] [--to Y] [-n N]
  priors lookup refs <id>                          works this one cites
  priors lookup citedby <id> [-n N]                works citing this one, most cited first
  priors lookup common-refs <id> <id> ... [-n N]   works cited by many of the given ones
  priors lookup common-citers <id> <id> ... [-n N] works citing many of the given ones

<id> is anything `get` accepts. Set OPENALEX_API_KEY if you have one.
"""

import argparse
import difflib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter

import yaml

API = "https://api.openalex.org"
FIELDS = "id,doi,title,publication_year,authorships,primary_location,cited_by_count,referenced_works,abstract_inverted_index,open_access,ids"


def fetch(url):
    key = os.environ.get("OPENALEX_API_KEY")
    if key and "api.openalex.org" in url:
        url += ("&" if "?" in url else "?") + "api_key=" + key
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return None
            if err.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(2**attempt)
                continue
            raise


def openalex(path, **params):
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    data = fetch(f"{API}/{path}" + (f"?{query}" if query else ""))
    return json.loads(data) if data else None


def work_path(ident):
    ident = ident.strip()
    if ident.lower().startswith("arxiv:"):
        return "works/doi:10.48550/arxiv." + ident.split(":", 1)[1]
    if ident.startswith("https://openalex.org/"):
        ident = ident.rsplit("/", 1)[1]
    if ident[:1] in "Ww" and ident[1:].isdigit():
        return "works/" + ident.upper()
    if ident.startswith("https://doi.org/"):
        ident = ident[len("https://doi.org/") :]
    return "works/doi:" + ident


def get_work(ident):
    return openalex(work_path(ident), select=FIELDS)


def arxiv_fallback(arxiv_id):
    data = fetch("https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(arxiv_id))
    if not data:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entry = ET.fromstring(data).find("a:entry", ns)
    if entry is None or entry.find("a:title", ns) is None:
        return None
    text = lambda tag: " ".join((entry.findtext(tag, "", ns) or "").split())
    return {
        "title": text("a:title"),
        "authors": [" ".join(a.findtext("a:name", "", ns).split()) for a in entry.findall("a:author", ns)],
        "year": int(text("a:published")[:4]) if text("a:published") else None,
        "arxiv": arxiv_id,
        "abstract": text("a:summary"),
        "source": "arXiv (not yet in OpenAlex)",
    }


def abstract(work):
    inv = work.get("abstract_inverted_index")
    if not inv:
        return None
    words = sorted((pos, word) for word, places in inv.items() for pos in places)
    return " ".join(word for _, word in words)


def summary(work, full=False):
    loc = work.get("primary_location") or {}
    out = {
        "openalex": (work.get("id") or "").rsplit("/", 1)[-1],
        "title": work.get("title"),
        "year": work.get("publication_year"),
        "authors": [a["author"]["display_name"] for a in work.get("authorships", [])][: None if full else 3],
        "venue": ((loc.get("source") or {}).get("display_name")),
        "doi": (work.get("doi") or "").replace("https://doi.org/", "") or None,
        "cited_by": work.get("cited_by_count"),
    }
    if full:
        out["open_access_pdf"] = (work.get("open_access") or {}).get("oa_url")
        out["abstract"] = abstract(work)
    return out


def batch(ids):
    ids = [i.rsplit("/", 1)[-1] for i in ids]
    works = []
    for start in range(0, len(ids), 50):
        chunk = "|".join(ids[start : start + 50])
        res = openalex("works", filter="openalex:" + chunk, select=FIELDS, **{"per-page": 50})
        works += res["results"] if res else []
    return {w["id"].rsplit("/", 1)[-1]: w for w in works}


def citers(ident, n):
    work = get_work(ident)
    if not work:
        sys.exit(f"not found: {ident}")
    wid = work["id"].rsplit("/", 1)[-1]
    res = openalex("works", filter="cites:" + wid, sort="cited_by_count:desc", select=FIELDS, **{"per-page": min(n, 200)})
    return res["results"] if res else []


def dump(obj):
    print(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=100).rstrip())


def main(argv=None):
    p = argparse.ArgumentParser(prog="priors lookup", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["get", "match", "search", "refs", "citedby", "common-refs", "common-citers"])
    p.add_argument("args", nargs="+")
    p.add_argument("-n", type=int, default=15)
    p.add_argument("--year", type=int)
    p.add_argument("--from", dest="from_year", type=int)
    p.add_argument("--to", dest="to_year", type=int)
    a = p.parse_args(argv)

    if a.command == "get":
        for ident in a.args:
            work = get_work(ident)
            if work:
                dump(summary(work, full=True))
            elif ident.lower().startswith("arxiv:") and (fallback := arxiv_fallback(ident.split(":", 1)[1])):
                dump(fallback)
            else:
                dump({"query": ident, "result": "not found"})
    elif a.command == "match":
        title = " ".join(a.args)
        filt = f"publication_year:{a.year - 1}-{a.year + 1}" if a.year else None
        res = openalex("works", search=title, filter=filt, select=FIELDS, **{"per-page": 5})
        rows = []
        for w in (res or {}).get("results", []):
            s = summary(w)
            s["title_similarity"] = round(difflib.SequenceMatcher(None, title.lower(), (w.get("title") or "").lower()).ratio(), 2)
            rows.append(s)
        dump(sorted(rows, key=lambda r: -r["title_similarity"]) or [{"query": title, "result": "not found"}])
    elif a.command == "search":
        filters = []
        if a.from_year:
            filters.append(f"from_publication_date:{a.from_year}-01-01")
        if a.to_year:
            filters.append(f"to_publication_date:{a.to_year}-12-31")
        res = openalex("works", search=" ".join(a.args), filter=",".join(filters) or None, select=FIELDS, **{"per-page": min(a.n, 200)})
        dump([summary(w) for w in (res or {}).get("results", [])])
    elif a.command == "refs":
        work = get_work(a.args[0]) or sys.exit(f"not found: {a.args[0]}")
        found = batch(work.get("referenced_works", []))
        dump(sorted((summary(w) for w in found.values()), key=lambda s: s["year"] or 0))
    elif a.command == "citedby":
        dump([summary(w) for w in citers(a.args[0], a.n)])
    elif a.command == "common-refs":
        counts = Counter()
        for ident in a.args:
            work = get_work(ident)
            if not work:
                print(f"# not found: {ident}", file=sys.stderr)
                continue
            counts.update(set(r.rsplit("/", 1)[-1] for r in work.get("referenced_works", [])))
        top = [(wid, c) for wid, c in counts.most_common(a.n) if c > 1]
        found = batch([wid for wid, _ in top])
        dump([{"cited_by_of_given": c, **summary(found[wid])} for wid, c in top if wid in found])
    elif a.command == "common-citers":
        counts, works = Counter(), {}
        for ident in a.args:
            for w in citers(ident, 200):
                wid = w["id"].rsplit("/", 1)[-1]
                counts[wid] += 1
                works[wid] = w
        top = [(wid, c) for wid, c in counts.most_common(a.n) if c > 1]
        dump([{"cites_of_given": c, **summary(works[wid])} for wid, c in top])


if __name__ == "__main__":
    main()
