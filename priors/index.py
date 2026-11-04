"""Rebuild index.md from page headers and report problems with the tree.

Usage: priors index [--check]

A page is a tree node if its YAML header has a `type` of map, topic, paper or
review. A node is named by its path without `.md`, with a trailing `/note` or
`/review` dropped, so `papers/<id>/note.md` is `papers/<id>`. Parents are listed
by those names. With --check, nothing is written. Exits 1 if any error is found.
"""

import re
import sys

import yaml

from . import config

ROOT = None
TYPES = {"map", "topic", "paper", "review"}
STATUSES = {"known", "skimmed", "read", "core"}
TOPIC_PAPER_LIMIT = 20
SKIP_DIRS = {"inbox", ".git", "digests"}
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def node_name(path):
    rel = path.relative_to(ROOT).with_suffix("").as_posix()
    for suffix in ("/note", "/review"):
        if rel.endswith(suffix):
            return rel[: -len(suffix)]
    return rel


def read_header(path):
    text = path.read_text(errors="replace")
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end < 0:
        return None, text
    try:
        header = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as err:
        return {"_error": str(err)}, text
    return header, text[end + 4 :]


def load_nodes():
    nodes, errors = {}, []
    for path in sorted(ROOT.rglob("*.md")):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in SKIP_DIRS or path.name == "original.md":
            continue
        header, body = read_header(path)
        if not isinstance(header, dict) or header.get("type") not in TYPES:
            if isinstance(header, dict) and "_error" in header:
                errors.append(f"{rel}: header isn't valid YAML: {header['_error']}")
            continue
        parents = header.get("parents") or []
        if isinstance(parents, str):
            parents = [parents]
        nodes[node_name(path)] = {
            "path": rel,
            "header": header,
            "body": body,
            "parents": [p.removesuffix(".md").rstrip("/") for p in parents],
            "children": [],
        }
    return nodes, errors


def check(nodes):
    errors, warnings = [], []
    for name, node in nodes.items():
        h, rel = node["header"], node["path"]
        if not str(h.get("summary") or "").strip():
            errors.append(f"{rel}: no summary")
        if h["type"] == "paper":
            if h.get("status") not in STATUSES:
                errors.append(f"{rel}: status must be one of {sorted(STATUSES)}")
            folder = rel.parent.name
            if str(h.get("id", folder)) != folder:
                warnings.append(f"{rel}: id {h.get('id')!r} doesn't match folder {folder!r}")
        if h["type"] != "map" and not node["parents"]:
            errors.append(f"{rel}: no parents, so it isn't reachable from the map")
        for parent in node["parents"]:
            if parent == name:
                errors.append(f"{rel}: lists itself as a parent")
            elif parent not in nodes:
                errors.append(f"{rel}: parent {parent!r} doesn't exist")
            else:
                nodes[parent]["children"].append(name)
                pu, cu = nodes[parent]["header"].get("updated"), h.get("updated")
                if pu and cu and str(cu) > str(pu):
                    warnings.append(
                        f"{nodes[parent]['path']}: summary may be stale; child {rel} updated {cu}, parent {pu}"
                    )
        for target in LINK.findall(node["body"]):
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (ROOT / rel.parent / target).exists() and not (ROOT / target).exists():
                errors.append(f"{rel}: broken link to {target}")
    for name, node in nodes.items():
        papers = [c for c in node["children"] if nodes[c]["header"]["type"] == "paper"]
        if node["header"]["type"] == "topic" and len(papers) > TOPIC_PAPER_LIMIT:
            warnings.append(
                f"{node['path']}: lists {len(papers)} papers, over {TOPIC_PAPER_LIMIT}; consider subtopics"
            )
    return errors, warnings


def describe(name, node):
    h = node["header"]
    link = node["path"].as_posix()
    extra = ""
    if h["type"] == "paper":
        extra = f" ({h.get('year', '?')}, {h.get('status')})"
    elif h["type"] == "review":
        extra = " (review)"
    return f"[{name}]({link}){extra}: {str(h.get('summary', '')).strip()}"


def outline(nodes):
    lines, seen = [], set()

    def walk(name, depth, path):
        node = nodes[name]
        again = name in seen
        lines.append("  " * depth + "- " + describe(name, node) + (" (also listed above)" if again else ""))
        if again:
            return
        seen.add(name)
        order = {"topic": 0, "map": 0, "review": 1, "paper": 2}
        kids = sorted(node["children"], key=lambda c: (order[nodes[c]["header"]["type"]], c))
        for child in kids:
            if child not in path:
                walk(child, depth + 1, path | {child})

    for name in sorted(n for n, v in nodes.items() if v["header"]["type"] == "map"):
        walk(name, 0, {name})
    unplaced = sorted(n for n in nodes if n not in seen)
    if unplaced:
        lines += ["", "## Not reachable from the map", ""]
        lines += ["- " + describe(n, nodes[n]) for n in unplaced]
    return lines


def main(argv=None):
    global ROOT, TOPIC_PAPER_LIMIT
    argv = sys.argv[1:] if argv is None else argv
    ROOT = config.find_library()
    cfg = config.load(ROOT)
    TOPIC_PAPER_LIMIT = int(cfg["topic_paper_limit"])
    write = "--check" not in argv
    nodes, errors = load_nodes()
    more_errors, warnings = check(nodes)
    errors += more_errors
    papers = [v["header"] for v in nodes.values() if v["header"]["type"] == "paper"]
    counts = ", ".join(f"{sum(p.get('status') == s for p in papers)} {s}" for s in sorted(STATUSES))
    if write:
        text = [
            "# Index",
            "",
            "Generated by `priors index` from page headers. Don't edit by hand.",
            "",
            f"Papers: {len(papers)} ({counts}).",
            "",
            *outline(nodes),
            "",
        ]
        (ROOT / "index.md").write_text("\n".join(text))
    for line in errors:
        print("ERROR  " + line)
    for line in warnings:
        print("WARN   " + line)
    print(f"{len(nodes)} pages, {len(papers)} papers, {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
