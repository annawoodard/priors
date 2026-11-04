"""Find a library and read its priors.yaml."""

import os
import sys
from pathlib import Path

import yaml

CONFIG = "priors.yaml"
DEFAULTS = {
    "owner": "the owner",
    "take_heading": None,
    "domain": {"name": None, "page": None, "note_section": "Translation"},
    "areas": [],
    "topic_paper_limit": 20,
    "run": "priors",
    "fetch": "No fetch method configured. Download open-access PDFs directly and ask the owner for the rest.",
    "review_source": "a deep-research tool",
}


def find_library(start=None):
    """The library root: $PRIORS_LIBRARY, else the nearest folder above `start` holding priors.yaml."""
    env = os.environ.get("PRIORS_LIBRARY")
    if env:
        root = Path(env).expanduser().resolve()
        if not (root / CONFIG).exists():
            sys.exit(f"PRIORS_LIBRARY={env} has no {CONFIG}")
        return root
    here = Path(start or os.getcwd()).resolve()
    for folder in (here, *here.parents):
        if (folder / CONFIG).exists():
            return folder
    sys.exit(f"No {CONFIG} found above {here}. Run inside a library or set PRIORS_LIBRARY.")


def load(root):
    data = yaml.safe_load((Path(root) / CONFIG).read_text()) or {}
    cfg = {**DEFAULTS, **data}
    cfg["domain"] = {**DEFAULTS["domain"], **(data.get("domain") or {})}
    if not cfg["take_heading"]:
        cfg["take_heading"] = f"{cfg['owner']}'s take"
    return cfg
