"""Create a new library from the template.

Usage: priors init <dir> --owner NAME --domain "field name" [--run COMMAND]
"""

import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path

import yaml

from . import ENGINE
from .config import CONFIG

TEMPLATE = ENGINE / "template"


def fill(text, values):
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def main(argv=None):
    p = argparse.ArgumentParser(prog="priors init", description=__doc__)
    p.add_argument("dir")
    p.add_argument("--owner", required=True)
    p.add_argument("--domain", required=True, help='the field to carry ideas into, e.g. "breast imaging"')
    p.add_argument("--run", default="priors", help="how to run the priors command on this machine")
    a = p.parse_args(argv)

    dest = Path(a.dir).expanduser().resolve()
    if (dest / CONFIG).exists():
        sys.exit(f"{dest} already has {CONFIG}; not overwriting it.")
    today = datetime.date.today().isoformat()
    values = {
        "owner": a.owner,
        "domain": a.domain,
        "domain_title": a.domain[:1].upper() + a.domain[1:],
        "domain_slug": re.sub(r"[^a-z0-9]+", "-", a.domain.lower()).strip("-"),
        "engine": ENGINE,
        "run": a.run,
        "date": today,
    }

    for src in sorted((TEMPLATE / "library").rglob("*")):
        target = dest / src.relative_to(TEMPLATE / "library")
        if src.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            if src.name == ".gitkeep":
                shutil.copy(src, target)
            else:
                target.write_text(fill(src.read_text(), values))

    cfg = yaml.safe_load((dest / CONFIG).read_text())
    (dest / "map").mkdir(exist_ok=True)
    for area in cfg.get("areas", []):
        page = dest / "map" / f"{area['id']}.md"
        if not page.exists():
            page.write_text(fill((TEMPLATE / "area.md").read_text(), {**values, **area}))
    domain_page = dest / cfg["domain"]["page"]
    if not domain_page.exists():
        domain_page.write_text(fill((TEMPLATE / "domain.md").read_text(), values))

    print(f"Created a library in {dest}.")
    print(f"Next: edit {dest / CONFIG}, then run `priors index` there, then set up git:")
    print("  git init -b main && git lfs install --local")


if __name__ == "__main__":
    main()
