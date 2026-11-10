"""Check that the passages a paper note quotes appear in the paper's text.

A quote is text in double quotes ("..." or “...”) inside the note's Claims
section. Bullets crediting a review ("per review") are skipped, because their
quotes come from the review, not the paper. A quote is split at ellipses and
bracketed insertions, and each fragment is looked for in `paper.txt` and any
`supplement*.txt` beside it.

Text extracted from PDFs breaks lines, hyphenates words and interleaves the
columns of two-column layouts, so the match ignores everything except letters
and digits, and searches the text twice: as extracted, and rebuilt column by
column with manuscript line numbers, watermarks and page numbers removed
(`columns`). A fragment of 30
characters or more is cut into 30-character chunks and counts as found when at
least half of them occur in the text: a break inside a quote costs one or two
chunks, while a passage the paper doesn't contain matches almost none. Shorter
fragments must occur whole. Numbers read off a figure are not in the text, so
they are reported as not found.
"""

import re
import unicodedata

MIN_FRAGMENT = 12
CHUNK = 30
FOUND_SHARE = 0.5

QUOTE = re.compile(r"[\"“]([^\"“”]{1,1500}?)[\"”]", re.S)
SPLIT = re.compile(r"\.\.\.|…|\[[^\]]*\]")


def squash(text):
    """Lower-case letters and digits only, after unfolding ligatures."""
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[^0-9a-z]", "", text)


SEGMENT = re.compile(r"\S(?:.*?\S)?(?=\s{3,}|\s*$)")
LINE_NUMBER = re.compile(r"^\s*\d{1,4}(?=\s{2,})")


def gutter(lines):
    """The column where most lines have a two-space gap with text to its right."""
    width = max((len(line) for line in lines), default=0)
    best, best_count = None, 0
    for x in range(int(0.25 * width), int(0.75 * width)):
        count = sum(line[x : x + 2] == "  " and line[x + 2 :].strip() != "" for line in lines)
        if count > best_count:
            best, best_count = x, count
    return best if best_count >= 5 else None


def columns(text):
    """`pdftotext -layout` text rebuilt as each page's left column, then its right.

    Two splits are returned joined, because each recovers columns the other
    misses: at the detected gutter, and at each text segment's start relative to
    45% of the page width (which survives pages whose gutter wanders).
    """
    by_gutter, by_start = [], []
    for page in text.split("\f"):
        lines = [LINE_NUMBER.sub("", line) for line in page.splitlines()]
        lines = [line for line in lines if len(line.strip()) > 3]
        x = gutter(lines)
        if x is None:
            by_gutter += lines
        else:
            by_gutter += [line[:x] for line in lines] + [line[x:] for line in lines]
        width = max((len(line) for line in lines), default=0)
        left, right = [], []
        for line in lines:
            for seg in SEGMENT.finditer(line):
                (left if seg.start() < 0.45 * width else right).append(seg.group())
        by_start += left + right
    return "\n".join(by_gutter + ["\f"] + by_start)


def claims_section(body):
    match = re.search(r"^## Claims\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    return match.group(1) if match else ""


def bullets(section):
    """Top-level bullets of a section, each with its wrapped lines joined."""
    items, current = [], []
    for line in section.splitlines():
        if line.startswith("- ") and current:
            items.append(" ".join(current))
            current = []
        if line.strip():
            current.append(line.strip())
    if current:
        items.append(" ".join(current))
    return items


def fragments(body):
    for item in bullets(claims_section(body)):
        if "per review" in item:
            continue
        for quote in QUOTE.findall(item):
            for piece in SPLIT.split(quote):
                if len(squash(piece)) >= MIN_FRAGMENT:
                    yield piece.strip()


def found(piece, haystack):
    needle = squash(piece)
    if needle in haystack:
        return True
    if len(needle) < CHUNK:
        return False
    chunks = [needle[i : i + CHUNK] for i in range(0, len(needle) - CHUNK + 1, CHUNK)]
    return sum(c in haystack for c in chunks) >= FOUND_SHARE * len(chunks)


def check(folder, body):
    """Return (checked, missing) for one note, or None when it has no paper.txt."""
    texts = [folder / "paper.txt", *sorted(folder.glob("supplement*.txt"))]
    if not texts[0].exists():
        return None
    raw = [t.read_text(errors="replace") for t in texts if t.exists()]
    haystack = "".join(squash(r) for r in raw) + "".join(squash(columns(r)) for r in raw)
    pieces = list(fragments(body))
    return len(pieces), [p for p in pieces if not found(p, haystack)]
