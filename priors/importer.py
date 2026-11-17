"""Merge a share bundle from another library into this one.

Usage: priors import <bundle> [--map NAME] [--dry-run]

A bundle is untrusted input. Page names must be `map/<x>`, `topics/<x>` or
`papers/<x>` with plain file names, nothing in it may be a symlink, and only a
paper's paper.pdf, paper.txt and supplement files are copied.

Papers are matched by every DOI, arXiv ID (without prefix or version) and
normalised title they carry.
- A paper this library already has keeps its note. The incoming note is saved
  beside it as `shared-<owner>.md` (type `shared-note`, which the index skips),
  its files are copied only where this library has none, and the incoming
  topics it sat under are added to the note's parents.
- A new paper is copied in with status `known` (the sharer's reading status
  is theirs, not the owner's) and `imported_from` naming the bundle. If its id
  is taken by a different paper, the id gets the sharer's name as a suffix.
- A paper that an earlier import of this sharer's bundles brought in is
  updated in place only if this bundle is newer.

Topic pages are merged by name. If this library has the topic, the incoming
body is appended under `## From <owner>'s library (bundle <date>)` for an
agent to fold in; a section for the same bundle is never added twice. If not,
the topic is created at the same path. Map pages are never written: an
incoming map is matched to this library's map of the same name, or to --map,
and topics that hang from it hang from that map instead.

Every destination is worked out and checked before anything is written; if a
write then fails, the files already written are restored. --dry-run prints
the plan. Afterwards run `priors index` and follow procedures/import-share.md.
"""

import datetime
import posixpath
import re
import shutil
import sys
from pathlib import Path

import yaml

from . import config, index, share

NAME = re.compile(r"^(map|topics|papers)/[A-Za-z0-9][A-Za-z0-9._-]*$")
KINDS = {"map": "map", "topic": "topics", "paper": "papers"}


def norm_doi(value):
    value = str(value or "").strip().lower()
    value = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", value)
    return f"doi:{value}" if value else None


def norm_arxiv(value):
    value = str(value or "").strip().lower()
    value = re.sub(r"^(arxiv:|https?://arxiv\.org/abs/)", "", value)
    value = re.sub(r"v\d+$", "", value)
    return f"arxiv:{value}" if value else None


def norm_title(value):
    value = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    return f"title:{value}" if len(value) > 20 else None


def keys(header):
    return [k for k in (norm_doi(header.get("doi")), norm_arxiv(header.get("arxiv")), norm_title(header.get("title"))) if k]


def owner_slug(owner):
    return re.sub(r"[^a-z0-9]+", "-", str(owner).lower()).strip("-") or "shared"


def read_page(path):
    header_text, body = share.split_header(path.read_text(errors="replace"))
    header = (yaml.safe_load(header_text) or {}) if header_text is not None else {}
    return header, header_text, body


def render(header, body):
    return "---\n" + yaml.safe_dump(header, sort_keys=False, allow_unicode=True, width=1000) + "---\n\n" + body.lstrip("\n")


def add_parents_text(text, new):
    """Add parents to a page's header by editing the text, so the owner's formatting and comments survive."""
    if not new:
        return text
    head_end = text.find("\n---", 4)
    head, rest = text[:head_end], text[head_end:]
    flow = re.search(r"^parents:\s*\[(.*?)\](\s*(#.*)?)$", head, re.M)
    if flow:
        items = [p.strip() for p in flow.group(1).split(",") if p.strip()]
        line = "parents: [" + ", ".join(items + new) + "]" + flow.group(2)
        return head[: flow.start()] + line + head[flow.end():] + rest
    if re.search(r"^parents:", head, re.M) and not re.search(r"^parents:\s*(#.*)?$", head, re.M):
        sys.exit("can't add parents to a header whose parents line isn't a [list] or a block list")
    block = re.search(r"^parents:\s*\n((?:\s+- .*\n?)+)", head + "\n", re.M)
    if block:
        indent = re.match(r"(\s+)-", block.group(1)).group(1)
        insert = "".join(f"{indent}- {p}\n" for p in new)
        end = block.end()
        return (head + "\n")[:end] + insert + (head + "\n")[end:].rstrip("\n") + rest
    return head + "\nparents: [" + ", ".join(new) + "]" + rest


def set_field_text(text, key, value):
    """Set a scalar header field by editing the text."""
    head_end = text.find("\n---", 4)
    head, rest = text[:head_end], text[head_end:]
    pattern = re.compile(rf"^{key}:.*$", re.M)
    line = f"{key}: {value}"
    head = pattern.sub(line, head, count=1) if pattern.search(head) else head + "\n" + line
    return head + rest


def parse(argv):
    if not argv or argv[0].startswith("-"):
        sys.exit(__doc__.strip())
    opts = {"bundle": Path(argv[0]).expanduser().resolve(), "map": None, "dry_run": False}
    i = 1
    while i < len(argv):
        if argv[i] == "--map":
            if i + 1 >= len(argv):
                sys.exit("--map needs a map page, such as map/methods")
            opts["map"] = argv[i + 1].removesuffix(".md")
            i += 2
        elif argv[i] == "--dry-run":
            opts["dry_run"] = True
            i += 1
        else:
            sys.exit(f"unknown argument {argv[i]!r}\n\n" + __doc__.strip())
    return opts


def load_bundle(bundle):
    manifest_path = bundle / "manifest.yaml"
    if not manifest_path.is_file():
        sys.exit(f"{bundle} has no manifest.yaml; is it a share bundle?")
    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    if manifest.get("format") != share.FORMAT:
        sys.exit(f"unsupported bundle format {manifest.get('format')!r}")
    for key in ("owner", "root", "created", "pages"):
        if not manifest.get(key):
            sys.exit(f"manifest.yaml has no {key}")
    problems, incoming = [], {}
    for page in manifest["pages"]:
        name, kind = str(page.get("name")), page.get("type")
        if kind not in KINDS or not NAME.match(name) or name.split("/")[0] != KINDS[kind] or ".." in name:
            problems.append(f"manifest: page {name!r} of type {kind!r} is not a plain map, topic or paper name")
            continue
        path = bundle / (f"{name}/note.md" if kind == "paper" else f"{name}.md")
        if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
            problems.append(f"{name}: missing, or a symlink")
            continue
        header, _, body = read_page(path)
        if header.get("type") != kind:
            problems.append(f"{name}: header type {header.get('type')!r} doesn't match the manifest")
            continue
        files = []
        if kind == "paper":
            for f in sorted(path.parent.iterdir()):
                if f.is_symlink():
                    problems.append(f"{name}/{f.name}: symlink")
                elif f.is_file() and share.PAPER_FILES.match(f.name):
                    files.append(f)
        incoming[name] = {"kind": kind, "header": header, "body": body, "files": files}
    if problems:
        sys.exit("Nothing imported; the bundle is malformed:\n" + "\n".join(problems))
    return manifest, incoming


class Writes:
    """Files to write, applied together; on failure every file already written is restored."""

    def __init__(self, root):
        self.root, self.ops = root, []

    def text(self, rel, content):
        self.ops.append((rel, content, None))

    def copy(self, rel, src):
        self.ops.append((rel, None, src))

    def inside(self, rel):
        dest = (self.root / rel).resolve()
        try:
            dest.relative_to(self.root)
        except ValueError:
            sys.exit(f"refusing to write outside the library: {rel}")
        return dest

    def apply(self):
        done = []  # (path, previous bytes or None)
        try:
            for rel, content, src in self.ops:
                dest = self.inside(rel)
                previous = dest.read_bytes() if dest.exists() else None
                dest.parent.mkdir(parents=True, exist_ok=True)
                done.append((dest, previous))
                if src is not None:
                    shutil.copy2(src, dest)
                else:
                    dest.write_text(content)
        except BaseException:
            for dest, previous in reversed(done):
                if previous is None:
                    dest.unlink(missing_ok=True)
                else:
                    dest.write_bytes(previous)
            raise


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    opts = parse(argv)
    manifest, incoming = load_bundle(opts["bundle"])
    root = index.ROOT = config.find_library()
    nodes, errors = index.load_nodes()
    if errors:
        sys.exit("fix these first (priors index):\n" + "\n".join(errors))
    owner, created = str(manifest["owner"]), str(manifest["created"])
    slug = owner_slug(owner)
    stamp = f"{owner}, {created}"  # compared as text: same owner prefix, then ISO dates sort correctly
    if opts["map"] and (opts["map"] not in nodes or nodes[opts["map"]]["header"]["type"] != "map"):
        sys.exit(f"--map {opts['map']!r} isn't a map page in this library")

    local_by_key = {}
    for name, node in nodes.items():
        if node["header"]["type"] == "paper":
            for k in keys(node["header"]):
                local_by_key.setdefault(k, name)

    # Where each incoming page lands.
    target, problems, taken = {}, [], set(nodes)
    for name, page in incoming.items():
        kind, header = page["kind"], page["header"]
        if kind == "map":
            dest = name if name in nodes and nodes[name]["header"]["type"] == "map" else opts["map"]
            if not dest:
                problems.append(f"{name}: no map of that name here; pass --map <one of this library's maps>")
            target[name] = dest
            continue
        if kind == "topic":
            on_disk = (root / f"{name}.md").exists()
            if on_disk and (name not in nodes or nodes[name]["header"]["type"] != "topic"):
                problems.append(f"{name}.md exists here but isn't a topic page; not touching it")
            target[name] = name
            continue
        match = next((local_by_key[k] for k in keys(header) if k in local_by_key), None)
        if match:
            target[name] = match
            continue
        dest = name
        n = 1
        while dest in taken or (root / dest).exists():
            dest = f"{name}-{slug}" if n == 1 else f"{name}-{slug}-{n}"
            n += 1
        taken.add(dest)
        target[name] = dest

    def place(parents):
        mapped = [target.get(p, p) for p in parents]
        return [p for p in dict.fromkeys(mapped) if p and (p in nodes or p in target.values())]

    for name, page in incoming.items():
        if page["kind"] == "map":
            continue
        parents = place(page["header"].get("parents") or [])
        if not parents and opts["map"]:
            parents = [opts["map"]]
        if not parents:
            problems.append(f"{name}: none of its parents exist here; pass --map <one of this library's maps>")
        page["parents"] = parents
    if problems:
        sys.exit("Nothing imported:\n" + "\n".join(problems))

    def relink(text, page_from, page_to):
        """Repoint relative links after a page moves, or links to papers that landed under another name."""

        def sub(m):
            bang, label, link = m.groups()
            if "://" in link or link.startswith(("mailto:", "#")):
                return m.group(0)
            path, _, frag = link.partition("#")
            rel = posixpath.normpath(posixpath.join(posixpath.dirname(page_from), path))
            if rel.startswith(".."):
                return label
            for old, new in target.items():
                if new and (rel == old or rel.startswith(old + "/") or rel == old + ".md"):
                    rel = new + rel[len(old):]
                    break
            new_link = posixpath.relpath(rel, posixpath.dirname(page_to) or ".")
            return f"{bang}[{label}]({new_link}{'#' + frag if frag else ''})"

        return share.MD_LINK.sub(sub, text)

    writes, lines = Writes(root), []
    date = datetime.date.today().isoformat()
    for name, page in incoming.items():
        kind, header, body, dest = page["kind"], page["header"], page["body"], target[name]
        if kind == "map":
            continue
        parents = page["parents"]
        if kind == "topic":
            local_path = f"{dest}.md"
            if dest in nodes:
                text = (root / local_path).read_text()
                local_header = nodes[dest]["header"]
                heading = f"## From {owner}'s library (bundle {created})"
                if str(local_header.get("imported_from") or "").startswith(f"{owner},"):
                    if str(local_header.get("imported_from")) >= stamp:
                        lines.append(f"skip    {local_path}: already imported from this or a newer bundle")
                        continue
                    lines.append(f"update  {local_path}")
                    header.update(parents=parents, updated=date, imported_from=stamp)
                    writes.text(local_path, render(header, relink(body, f"{name}.md", local_path)))
                    continue
                if heading in text:
                    lines.append(f"skip    {local_path}: has the section for this bundle")
                    continue
                appended = relink(share.shift_headings(share.drop_first_heading(body), 1), f"{name}.md", local_path)
                text = set_field_text(text, "updated", date).rstrip("\n") + (
                    f"\n\n{heading}\n\n"
                    "<!-- Added by priors import. Fold this into the page's own sections, then delete it. -->\n\n"
                    + appended.strip() + "\n"
                )
                lines.append(f"merge   {local_path}: append {heading[3:]}")
                writes.text(local_path, text)
            else:
                header.update(parents=parents, updated=date, imported_from=stamp)
                lines.append(f"create  {local_path}")
                writes.text(local_path, render(header, relink(body, f"{name}.md", local_path)))
            continue
        local_note = f"{dest}/note.md"
        if dest in nodes:
            local_header = nodes[dest]["header"]
            if str(local_header.get("imported_from") or "").startswith(f"{owner},"):
                if str(local_header.get("imported_from")) >= stamp:
                    lines.append(f"skip    {dest}: already imported from this or a newer bundle")
                    continue
                header.update(id=dest.split("/")[-1], parents=parents, imported_from=stamp)
                if header.get("status") != "requested":
                    header["status"] = "known"
                lines.append(f"update  {local_note}")
                writes.text(local_note, render(header, relink(body, f"{name}/note.md", local_note)))
                for f in page["files"]:
                    writes.copy(f"{dest}/{f.name}", f)
                continue
            shared_note = f"{dest}/shared-{slug}.md"
            copies = [f for f in page["files"] if not (root / dest / f.name).exists()]
            new_parents = [p for p in parents if p not in nodes[dest]["parents"]]
            lines.append(
                f"match   {dest}: save shared-{slug}.md"
                + (f", copy {', '.join(f.name for f in copies)}" if copies else "")
                + (f", add parents {', '.join(new_parents)}" if new_parents else "")
            )
            shared = dict(header, type="shared-note", shared_by=owner, shared_bundle=stamp, parents=parents)
            writes.text(shared_note, render(shared, relink(body, f"{name}/note.md", local_note)))
            for f in copies:
                writes.copy(f"{dest}/{f.name}", f)
            if new_parents:
                writes.text(local_note, add_parents_text((root / local_note).read_text(), new_parents))
        else:
            header.update(id=dest.split("/")[-1], parents=parents, imported_from=stamp)
            if header.get("status") != "requested":
                header["status"] = "known"
            lines.append(f"create  {local_note}")
            writes.text(local_note, render(header, relink(body, f"{name}/note.md", local_note)))
            for f in page["files"]:
                writes.copy(f"{dest}/{f.name}", f)

    print("\n".join(lines))
    if opts["dry_run"]:
        print("(dry run: nothing written)")
        return
    counts = {k: sum(x.startswith(k) for x in lines) for k in ("create", "merge", "match", "update", "skip")}
    log_text = (root / "log.md").read_text() if (root / "log.md").exists() else ""
    writes.text(
        "log.md",
        log_text.rstrip("\n")
        + f"\n\n## {date} import | {manifest['root']} from {owner}\n\n"
        f"Bundle of {created} from {owner}'s library at {manifest.get('source_commit')}. "
        f"{counts['create']} pages created, {counts['merge']} topics merged, {counts['match']} papers already here, "
        f"{counts['update']} updated from an earlier import, {counts['skip']} skipped. Merged sections await folding in.\n",
    )
    writes.apply()
    print("Next: priors index, then procedures/import-share.md")
