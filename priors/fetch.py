"""Write a prompt asking a local agent (on a laptop with library access) to download PDFs.

Usage: priors fetch-prompt [<page>]

With no page, the prompt covers every paper with status `requested`. With a
map, topic or paper page, it covers every paper in what `priors share <page>`
would bundle (private sections included) that has no paper.pdf.

Where the agent saves each PDF and what it does afterwards come from
`fetch_prompt` in priors.yaml: `save_to` (with {id} filled in) and `then`.
`priors share` writes the same prompt into each bundle as fetch-pdfs.md, with
paths inside the bundle folder, so a collaborator's agent can fill in the PDFs
the owner doesn't have.
"""

import sys

from . import config, index


def missing(root, nodes, names):
    """Paper nodes among `names` whose folder has no paper.pdf, in the given order."""
    out = []
    for name in names:
        node = nodes[name]
        if node["header"]["type"] == "paper" and not (root / node["path"].parent / "paper.pdf").exists():
            out.append(name)
    return out


def where_to_get(header):
    doi = str(header.get("doi") or "").strip()
    arxiv = str(header.get("arxiv") or "").strip()
    parts = []
    if doi:
        parts.append(f"https://doi.org/{doi.removeprefix('https://doi.org/')}")
    if arxiv:
        parts.append(f"https://arxiv.org/pdf/{arxiv.removeprefix('arXiv:')}")
    return ", ".join(parts) or "no DOI or arXiv id; search by title"


def prompt(entries, intro, then):
    """The prompt text. `entries` is a list of (header, destination path)."""
    lines = [
        intro,
        "",
        "Prefer the publisher's typeset version, open access or through the university",
        "library's subscription. Fall back to an author manuscript (PubMed Central) or a",
        "preprint (arXiv, medRxiv).",
        "",
    ]
    for header, dest in entries:
        title = str(header.get("title") or header.get("summary") or "").strip()
        year = f" ({header['year']})" if header.get("year") else ""
        lines.append(f"- {title}{year}: {where_to_get(header)}\n  -> {dest}")
    lines += [
        "",
        "Check each file is a real PDF whose title matches the paper, not a login or",
        "error page saved under that name. Don't rename or change anything else.",
    ]
    if then:
        lines += ["", then.strip()]
    lines += ["", "Then say which version each PDF is (publisher, author manuscript or preprint),", "and which papers you couldn't get and why."]
    return "\n".join(lines) + "\n"


def owner_prompt(cfg, nodes, names):
    settings = cfg["fetch_prompt"]
    entries = [(nodes[n]["header"], settings["save_to"].format(id=nodes[n]["path"].parent.name)) for n in names]
    intro = "Download these papers and save each PDF at the path shown, creating folders as needed."
    return prompt(entries, intro, settings.get("then"))


def bundle_prompt(nodes, names):
    entries = [(nodes[n]["header"], f"{nodes[n]['path'].parent.as_posix()}/paper.pdf") for n in names]
    intro = (
        "This folder is a literature bundle. Some of its papers came without a PDF.\n"
        "Download each one and save it at the path shown, relative to this folder\n"
        "(the folder holding this file and manifest.yaml); each folder already exists."
    )
    then = (
        "If this machine has a priors library, run `priors import <this folder>` from\n"
        "inside it afterwards; it copies PDFs that arrived after an earlier import."
    )
    return prompt(entries, intro, then)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) > 1 or (argv and argv[0].startswith("-")):
        sys.exit(__doc__.strip())
    root = index.ROOT = config.find_library()
    cfg = config.load(root)
    nodes, errors = index.load_nodes()
    if errors:
        sys.exit("fix these first (priors index):\n" + "\n".join(errors))
    if argv:
        from . import share

        start = share.page_name(root, argv[0])
        if start not in nodes:
            sys.exit(f"{argv[0]!r} isn't a page in this library")

        def body(name):
            return share.split_header((root / nodes[name]["path"]).read_text(errors="replace"))[1]

        names = missing(root, nodes, share.select(nodes, start, [], [], body))
    else:
        names = [
            n for n in sorted(nodes) if nodes[n]["header"]["type"] == "paper" and nodes[n]["header"].get("status") == "requested"
        ]
    if not names:
        print(f"Every paper under {argv[0]} has its PDF." if argv else "No paper has status requested.")
        return
    print(owner_prompt(cfg, nodes, names), end="")
