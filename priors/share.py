"""Build a share bundle: one map or topic page, the pages under it, and their papers.

Usage: priors share <page> [--out DIR] [--add NAME ...] [--drop NAME ...]
                           [--keep-private] [--no-digest]

<page> is a node name (`topics/foo`, `map/bar`) or a path to its file. The
bundle holds the page, every map, topic and paper below it, and every paper its
topic pages link to, with each paper's paper.pdf, paper.txt and supplement
files. Reviews are left out. --add takes paper ids or node names; --drop
removes a page and everything below it.

Unless --keep-private is given, each page loses:
- every section whose heading contains the owner's take heading or an entry of
  `share.strip_headings` (case-insensitive, any heading level or style), and
  every bold-led paragraph that opens with one;
- text between `<!-- private -->` and `<!-- /private -->`, and every other
  HTML comment;
- header fields outside a fixed list of bibliographic ones.
Links to pages outside the bundle become plain text, and papers linked only
from stripped text are not pulled in.

The build fails closed. It refuses a page with an unbalanced code fence or
private marker, or with a reference-style or HTML link it can't rewrite.
After the bundle is assembled, every text file in it (pages, manifest, README,
the digest's source, paper text) is searched for `share.forbidden` patterns,
across line breaks. A match in anything but a paper's own text stops the
build; matches in paper text are listed for the owner to look at.

The bundle is a folder in the library's own layout (map/, topics/, papers/),
with manifest.yaml, README.md and, unless --no-digest, digest.pdf: the pages
in reading order with links between them, built with pandoc.
"""

import datetime
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from . import config, index

FORMAT = "priors-share 1"
HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
SETEXT = re.compile(r"^ {0,3}(=+|-+)\s*$")
FENCE = re.compile(r"^ {0,3}(```|~~~)")
PRIVATE_OPEN = re.compile(r"<!--\s*private\s*-->", re.I)
PRIVATE_CLOSE = re.compile(r"<!--\s*/\s*private\s*-->", re.I)
PRIVATE = re.compile(r"<!--\s*private\s*-->.*?<!--\s*/\s*private\s*-->", re.I | re.S)
COMMENT = re.compile(r"<!--.*?-->", re.S)
MD_LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
REF_DEF = re.compile(r"^ {0,3}\[[^\]]+\]:\s*\S+", re.M)
HTML_LINK = re.compile(r"<a\s[^>]*href=", re.I)
NODE_TYPES = {"map", "topic", "paper"}
HEADER_KEYS = [
    "type", "id", "title", "summary", "authors", "venue", "year", "doi", "arxiv",
    "openalex", "parents", "status", "updated", "ingested", "coverage", "version",
]
PAPER_FILES = re.compile(r"^(paper\.pdf|paper\.txt|supplement[^/]*)$")


def split_header(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    return text[4:end], text[end + 4 :].lstrip("\n")


def normalise(text):
    return text.replace("’", "'").replace("‘", "'").replace("*", "").replace("_", " ").casefold()


def is_private_title(title, needles):
    """True if the heading contains a needle as whole words, after normalising case, quotes and emphasis."""
    title = normalise(title)
    return any(re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", title) for n in needles)


def check_structure(rel, body):
    """Reasons this page can't be cleaned safely; the build refuses on any."""
    problems = []
    if sum(bool(FENCE.match(line)) for line in body.splitlines()) % 2:
        problems.append(f"{rel}: unbalanced code fence")
    if len(PRIVATE_OPEN.findall(body)) != len(PRIVATE_CLOSE.findall(body)):
        problems.append(f"{rel}: unbalanced <!-- private --> markers")
    if REF_DEF.search(body):
        problems.append(f"{rel}: reference-style link definition; write it as an inline link")
    if HTML_LINK.search(body):
        problems.append(f"{rel}: HTML <a href> link; write it as a markdown link")
    return problems


def strip_sections(body, needles):
    """Drop sections whose heading names private content, and bold-led paragraphs that open with it."""
    lines = body.splitlines(keepends=True)
    out, skip_level, fenced, i = [], None, False, 0
    while i < len(lines):
        line = lines[i]
        if FENCE.match(line):
            fenced = not fenced
        level = title = None
        if not fenced:
            m = HEADING.match(line)
            if m:
                level, title = len(m.group(1)), m.group(2)
            elif line.strip() and i + 1 < len(lines) and SETEXT.match(lines[i + 1]) and not line.lstrip().startswith(("- ", "* ", "|")):
                level, title = (1 if "=" in lines[i + 1] else 2), line.strip()
        if level is not None:
            if skip_level is not None and level <= skip_level:
                skip_level = None
            if skip_level is None and is_private_title(title, needles):
                skip_level = level
            if skip_level is not None:
                i += 2 if not HEADING.match(line) else 1
                continue
        if skip_level is not None:
            i += 1
            continue
        if not fenced and line.lstrip().startswith("**") and is_private_title(line.split("**")[1] if line.count("**") >= 2 else line, needles):
            while i < len(lines) and lines[i].strip():  # drop the whole paragraph
                i += 1
            continue
        out.append(line)
        i += 1
    return "".join(out)


def clean(body, needles, keep_private):
    """The body with private content removed (headings, bold paragraphs, markers, comments)."""
    if keep_private:
        return body
    body = PRIVATE.sub("", body)
    body = COMMENT.sub("", body)
    return strip_sections(body, needles)


def resolve(root, page_path, target):
    """The library-relative path a relative link points at, or None if it leaves the library or is external."""
    if "://" in target or target.startswith(("mailto:", "#")):
        return None
    target = target.split("#", 1)[0]
    try:
        return (root / page_path.parent / target).resolve().relative_to(root)
    except ValueError:
        return None


def select(nodes, start, add, drop, cleaned):
    """Node names in the bundle, in reading order: depth first from `start`, then papers linked from its cleaned topics."""
    children = {}
    for name, node in nodes.items():
        for parent in node["parents"]:
            children.setdefault(parent, []).append(name)
    dropped = {d if d in nodes else f"papers/{d}" for d in drop}
    if start in dropped:
        sys.exit("can't drop the page being shared")
    order, seen = [], set()

    def walk(name):
        if name in seen or name in dropped or nodes[name]["header"]["type"] not in NODE_TYPES:
            return
        seen.add(name)
        order.append(name)
        kids = sorted(children.get(name, []), key=lambda c: (nodes[c]["header"]["type"] == "paper", c))
        for child in kids:
            walk(child)

    walk(start)
    by_path = {v["path"].as_posix(): k for k, v in nodes.items()}
    for name in list(order):
        if nodes[name]["header"]["type"] == "paper":
            continue
        for _, _, target in MD_LINK.findall(cleaned(name)):
            rel = resolve(index.ROOT, nodes[name]["path"], target)
            linked = by_path.get(rel.as_posix()) if rel else None
            if linked and linked not in seen and linked not in dropped and nodes[linked]["header"]["type"] == "paper":
                seen.add(linked)
                order.append(linked)
    for item in add:
        name = item if item in nodes else f"papers/{item}"
        if name not in nodes:
            sys.exit(f"--add {item!r}: no such page")
        if name not in seen:
            seen.add(name)
            order.append(name)
    return order


def rewrite_links(body, page_path, kept_files, anchor_for=None):
    """Keep links to files in the bundle and external links; turn the rest into plain text.

    With `anchor_for` (path -> anchor), links to pages in the bundle become in-document anchors, for the digest.
    """

    def sub(m):
        bang, text, target = m.groups()
        if "://" in target or target.startswith(("mailto:", "#")):
            return m.group(0)
        rel = resolve(index.ROOT, page_path, target)
        if rel is None or rel.as_posix() not in kept_files:
            return text
        if anchor_for is not None:
            anchor_ = anchor_for.get(rel.as_posix())
            return f"{bang}[{text}](#{anchor_})" if anchor_ else f"{bang}[{text}]({rel.as_posix()})"
        return f"{bang}[{text}]({target})"

    return MD_LINK.sub(sub, body)


def prune_links_section(body):
    """Drop `## Links` lines whose target was left out of the bundle, since each line must keep its link."""
    out, inside = [], False
    for line in body.splitlines(keepends=True):
        m = HEADING.match(line)
        if m:
            inside = len(m.group(1)) == 2 and m.group(2) == "Links"
        if inside and line.startswith("- ") and "](" not in line:
            continue
        out.append(line)
    return "".join(out)


def anchor(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def digest_markdown(start, order, nodes, pages, anchors, headers):
    summary = str(headers[start].get("summary") or "").strip()
    lines = [f"*{summary}*", ""] if summary else []
    for name in order:
        node, body, h = nodes[name], pages[name], headers[name]
        heading = first_heading(body) or name
        body = drop_first_heading(body)  # the page's title becomes the section heading below
        lines += [f"# {heading} {{#{anchors[node['path'].as_posix()]}}}", ""]
        if h["type"] == "paper":
            folder = node["path"].parent.as_posix()
            authors = h.get("authors") or []
            meta = ", ".join(str(a) for a in authors[:6]) + (" et al." if len(authors) > 6 else "")
            bits = [b for b in (meta, str(h.get("venue") or ""), str(h.get("year") or "")) if b]
            lines.append("; ".join(bits) + ".")
            refs = []
            if h.get("doi"):
                refs.append(f"[doi:{h['doi']}](https://doi.org/{h['doi']})")
            if h.get("arxiv"):
                refs.append(f"[arXiv:{h['arxiv']}](https://arxiv.org/abs/{h['arxiv']})")
            if (index.ROOT / folder / "paper.pdf").exists():
                refs.append(f"[PDF]({folder}/paper.pdf)")
            if refs:
                lines += ["", " · ".join(refs)]
            lines.append("")
        lines += [body.strip(), "", "```{=latex}", "\\newpage", "```", ""]
    return "\n".join(lines)


def first_heading(body):
    for line in body.splitlines():
        m = HEADING.match(line)
        if m and len(m.group(1)) == 1:
            return m.group(2)
    return None


def drop_first_heading(body):
    out, dropped = [], False
    for line in body.splitlines(keepends=True):
        m = HEADING.match(line)
        if not dropped and m and len(m.group(1)) == 1:
            dropped = True
            continue
        out.append(line)
    return "".join(out)


def shift_headings(body, by):
    out, fenced = [], False
    for line in body.splitlines(keepends=True):
        if FENCE.match(line):
            fenced = not fenced
        m = None if fenced else HEADING.match(line)
        if m:
            line = "#" * min(6, len(m.group(1)) + by) + " " + m.group(2) + "\n"
        out.append(line)
    return "".join(out)


def leak_hits(patterns, files):
    """Every match of a forbidden pattern, searched across line breaks, reported at the line where it starts."""
    hits = []
    compiled = [re.compile(p) for p in patterns]
    for rel, text in files.items():
        flat = re.sub(r"\s+", " ", text)
        # map each character of `flat` back to a line number in `text`
        line_of = []
        number = 1
        prev_space = False
        for ch in text:
            if ch.isspace():
                if not prev_space:
                    line_of.append(number)
                prev_space = True
            else:
                line_of.append(number)
                prev_space = False
            if ch == "\n":
                number += 1
        lines = text.splitlines()
        for pattern in compiled:
            for m in pattern.finditer(flat):
                n = line_of[min(m.start(), len(line_of) - 1)] if line_of else 1
                snippet = lines[n - 1].strip()[:100] if n - 1 < len(lines) else ""
                hits.append(f"{rel}:{n}: {pattern.pattern!r} in {snippet!r}")
    return hits


def build_digest(cfg, out, markdown, title, date):
    share = cfg["share"]
    src = out / "digest.md"
    src.write_text(markdown)
    command = [
        share["pandoc"], src.name, "-o", "digest.pdf",
        "--from=commonmark_x",  # pages are written as CommonMark: lists need no blank line before them
        "--toc", "--toc-depth=1",
        "-M", f"title={title}",
        "-M", f"subtitle=Shared from {cfg['owner']}'s library, {date}",
        "-V", "colorlinks=true",
        "-V", "geometry=margin=2.2cm",
        f"--pdf-engine={share['pdf_engine']}",
        "-V", f"mainfont={share['mainfont']}",
        "-V", f"monofont={share['monofont']}",
    ]
    result = subprocess.run(command, cwd=out, capture_output=True, text=True)
    src.unlink()
    if result.returncode != 0:
        sys.exit("pandoc failed building digest.pdf:\n" + (result.stderr or result.stdout)[-2000:])


def git_commit(root):
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True)
    return result.stdout.strip() or None


def parse(argv):
    if not argv or argv[0].startswith("-"):
        sys.exit(__doc__.strip())
    opts = {"page": argv[0], "out": None, "add": [], "drop": [], "keep_private": False, "digest": True}
    i, current = 1, None
    while i < len(argv):
        arg = argv[i]
        if arg == "--out":
            if i + 1 >= len(argv):
                sys.exit("--out needs a folder")
            opts["out"], current = argv[i + 1], None
            i += 2
            continue
        if arg in ("--add", "--drop"):
            current = arg[2:]
        elif arg == "--keep-private":
            opts["keep_private"], current = True, None
        elif arg == "--no-digest":
            opts["digest"], current = False, None
        elif current and not arg.startswith("-"):
            opts[current].append(arg)
        else:
            sys.exit(f"unknown argument {arg!r}\n\n" + __doc__.strip())
        i += 1
    return opts


def page_name(root, given):
    path = Path(given)
    if path.is_absolute() or given.startswith("."):
        try:
            given = path.resolve().relative_to(root).as_posix()
        except ValueError:
            sys.exit(f"{given!r} is outside the library")
    return given.removesuffix(".md").removesuffix("/note").rstrip("/")


def replace_bundle(tmp, final):
    """Move the new bundle into place, keeping the old one until the move succeeds."""
    old = None
    if final.exists() or final.is_symlink():
        manifest = final / "manifest.yaml"
        fmt = (yaml.safe_load(manifest.read_text()) or {}).get("format") if manifest.is_file() else None
        if final.is_symlink() or fmt != FORMAT:
            sys.exit(f"{final} exists and isn't a share bundle; choose another --out")
        old = final.with_name(f".{final.name}.old")
        if old.exists():
            shutil.rmtree(old)
        final.rename(old)
    try:
        tmp.rename(final)
    except BaseException:
        if old is not None:
            old.rename(final)
        raise
    if old is not None:
        shutil.rmtree(old)  # the previous build of this bundle, replaced whole


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    opts = parse(argv)
    root = index.ROOT = config.find_library()
    cfg = config.load(root)
    share = cfg["share"]
    nodes, errors = index.load_nodes()
    if errors:
        sys.exit("fix these first (priors index):\n" + "\n".join(errors))
    start = page_name(root, opts["page"])
    if start not in nodes:
        sys.exit(f"{opts['page']!r} isn't a page in this library")
    if nodes[start]["header"]["type"] not in NODE_TYPES:
        sys.exit("share a map, topic or paper page")

    needles = [normalise(s) for s in [cfg["take_heading"], *share["strip_headings"]]]
    raw, cleaned_cache, problems = {}, {}, []

    def cleaned(name):
        if name not in cleaned_cache:
            header_text, body = split_header((root / nodes[name]["path"]).read_text(errors="replace"))
            problems.extend(check_structure(nodes[name]["path"].as_posix(), body))
            raw[name] = header_text
            cleaned_cache[name] = clean(body, needles, opts["keep_private"])
        return cleaned_cache[name]

    order = select(nodes, start, opts["add"], opts["drop"], cleaned)
    for name in order:
        cleaned(name)
    if problems:
        sys.exit("Stopped: these pages can't be cleaned safely:\n" + "\n".join(sorted(set(problems))))
    chosen = set(order)

    kept_files = set()
    copies = {}
    for name in order:
        path = nodes[name]["path"]
        kept_files.add(path.as_posix())
        if nodes[name]["header"]["type"] == "paper":
            for f in sorted((root / path.parent).iterdir()):
                if f.is_file() and not f.is_symlink() and PAPER_FILES.match(f.name):
                    rel = (path.parent / f.name).as_posix()
                    kept_files.add(rel)
                    copies[rel] = f

    pages, headers, files = {}, {}, {}
    for name in order:
        node = nodes[name]
        body = prune_links_section(rewrite_links(cleaned(name), node["path"], kept_files))
        full = yaml.safe_load(raw[name] or "") or {}
        header = {k: full[k] for k in HEADER_KEYS if k in full}
        if name != start:
            header["parents"] = [p for p in node["parents"] if p in chosen] or [start]
        pages[name], headers[name] = body, header
        files[node["path"].as_posix()] = "---\n" + yaml.safe_dump(header, sort_keys=False, allow_unicode=True, width=1000) + "---\n\n" + body

    date = datetime.date.today().isoformat()
    papers = sum(nodes[n]["header"]["type"] == "paper" for n in order)
    root_title = first_heading(pages[start]) or start
    manifest = {
        "format": FORMAT,
        "owner": cfg["owner"],
        "root": start,
        "created": date,
        "source_commit": git_commit(root),
        "private_sections_kept": opts["keep_private"],
        "pages": [
            {"name": n, "type": headers[n]["type"], **{k: headers[n][k] for k in ("doi", "arxiv", "title") if headers[n].get(k)}}
            for n in order
        ],
    }
    files["manifest.yaml"] = yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True)
    files["README.md"] = (
        f"# {root_title}\n\n"
        f"Shared from {cfg['owner']}'s literature library on {date}: "
        f"{len(order) - papers} map/topic pages and {papers} paper notes, with the papers' PDFs.\n\n"
        "- To read: open `digest.pdf`, or start at "
        f"[`{nodes[start]['path'].as_posix()}`]({nodes[start]['path'].as_posix()}).\n"
        "- To add it to your own priors library: `priors import <this folder>`.\n"
    )
    anchors = {nodes[n]["path"].as_posix(): anchor(n) for n in order}
    digest_src = None
    if opts["digest"]:
        digest_pages = {n: rewrite_links(pages[n], nodes[n]["path"], kept_files, anchors) for n in order}
        digest_src = digest_markdown(start, order, nodes, digest_pages, anchors, headers)
        files["digest.pdf (source)"] = digest_src

    hits = leak_hits(share["forbidden"], files)
    text_hits = leak_hits(
        share["forbidden"],
        {rel: f.read_text(errors="replace") for rel, f in copies.items() if f.suffix == ".txt"},
    )
    if hits:
        print("Stopped: these lines match share.forbidden. Reword them, or wrap them in <!-- private --> ... <!-- /private -->:")
        print("\n".join(hits))
        sys.exit(1)
    files.pop("digest.pdf (source)", None)

    out_root = Path(opts["out"] or root / share["out"]).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    final = out_root / start.split("/")[-1]
    tmp = Path(tempfile.mkdtemp(prefix=f".{final.name}.", dir=out_root))
    try:
        for rel, text in files.items():
            dest = tmp / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
        for rel, f in copies.items():
            shutil.copy2(f, tmp / rel)
        if digest_src is not None:
            build_digest(cfg, tmp, digest_src, root_title, date)
        replace_bundle(tmp, final)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    print(f"Bundle: {final} ({len(order)} pages, {papers} papers)")
    if text_hits:
        print("Forbidden patterns also appear in paper text (the papers' own words; shipped). Check these are the paper's:")
        print("\n".join(text_hits))
    if share.get("download"):
        print("Download: " + share["download"].format(path=final, name=final.name))
