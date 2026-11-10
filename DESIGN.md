# priors: design

How the system is meant to work. Decisions carry who made them and when;
Anna is the engine's author. "Planned" means decided but not built. Lines
starting with "Open:" are choices nobody has approved yet. Choices an owner
makes for their own library go in that library's `DECISIONS.md`.

## Purpose

priors helps one researcher know the literature of their field through an
agent they can question directly, with whatever model they choose.

- The problem it solves: you read a paper, like it and forget it, and
  literature reviews from deep-research tools get read once and lost.
- The reason to build it instead of using ResearchRabbit, Litmaps or Connected
  Papers is model choice. Any model you can run in Claude Code or Codex can
  read the library, because it's plain markdown in git (Anna, 2026-10-30).
- It runs wherever the owner's work is, for example an HPC cluster, so agents
  can see experiments and results next to the papers (Anna, 2026-10-29).

## Two repos

The engine and each library are separate repos (Anna, 2026-11-03).

| Repo | Holds | Shared? |
|---|---|---|
| the engine, `priors` | the `priors` command, the agent procedures, the template for new libraries, this document | public |
| a library | one owner's `priors.yaml`, pages, PDFs and decisions | private if it holds publisher PDFs |

`priors init` creates a library from the template. Engine updates reach every
library with a `git pull` of the engine, because libraries point at the engine
instead of copying it.

## What's configurable

Everything specific to one owner is in the library's `priors.yaml`.

| Setting | Means |
|---|---|
| `owner` | who the library belongs to; procedures say "the owner" |
| `take_heading` | the title of the owner's own section in each note, which agents never write in |
| `domain.name`, `domain.page`, `domain.note_section` | the field the owner carries ideas into, the page saying what makes it different, and the title of the matching section in each note |
| `areas` | the top-level map pages `init` creates |
| `topic_paper_limit` | how many papers a topic can list before `priors index` warns |
| `run` | how to run the `priors` command on this machine |
| `fetch` | how paywalled PDFs, which agents can't download, get into the library |
| `review_source` | where pasted reviews come from |

The library's `AGENTS.md` comes from the template and tells agents to read
`priors.yaml` first.

## Goals

The system has six goals.

1. **Field map.** One page per area. Each covers the subproblems, the key
   papers, what's settled and what's contested, the datasets, the groups, and
   the open problems.
2. **Weekly intake.** A digest of new papers, sorted into tiers. The owner's
   ratings steer later digests.
3. **Mentor mode.** The owner describes a problem and gets back approaches
   from any field and any decade, each with a note on how it would carry over
   to their domain.
4. **Translation watch.** Methods from neighboring fields, flagged with what
   it would take to use them in the owner's domain.
5. **Answers from anywhere.** Agents in the owner's other repos can ask the
   library questions.
6. **A small core in the owner's head.** The map at a coarse level and a few
   dozen papers per area they should understand themselves. Remembering
   everything isn't the goal (Anna, 2026-10-29).

Open: the order of priority. The list above is a proposal.

## What lives where

A library is a tree: areas at the top, then topics, then papers, then each
paper's full text. Every kind of record has one home.

```
<library>/
├── priors.yaml           owner, domain, areas, how to run and fetch
├── AGENTS.md             instructions for agents, from the template
├── DECISIONS.md          the owner's choices and open questions
├── index.md              the whole tree, one line per page (generated)
├── queue.md              papers waiting to be read, with their tier
├── log.md                append-only record of ingests, digests, queries, sessions
├── watch.md              authors, search terms and nearby fields the digest follows
├── inbox/                pastes waiting to be ingested
├── map/                  level 1: one page per area, plus the domain page
├── topics/               level 2: one page per topic, listing its papers
│   └── <topic>.md        split into topics/<topic>/<subtopic>.md when it grows
├── papers/<id>/          levels 3 and 4: one paper
│   ├── note.md           everything we know about it
│   ├── paper.txt         text extracted from the PDF
│   ├── paper.pdf         as downloaded, never edited
│   └── supplement*.pdf   supplementary material, never edited, with supplement*.txt
├── reviews/<slug>/       one pasted review
│   ├── original.md       exactly as pasted, never edited
│   ├── review.md         cleaned up
│   └── citations.md      each citation: confirmed, mismatched or not found
├── digests/<date>.md     one weekly digest with the owner's ratings
└── projects/<name>.md    one of the owner's projects: its repo path and open questions
```

Who writes what:

- **The owner**: `priors.yaml`, `DECISIONS.md`, `inbox/`, `watch.md`,
  `projects/`, the domain page, the ratings in each digest, and their own
  section of every note. They also shape the map pages.
- **Whoever `fetch` names**: PDFs agents can't download.
- **The agent**: everything else, including open-access PDFs.

`<id>` is the arXiv ID or DOI plus a short name, for example
`2610.14136-correction-training`. `<slug>` is the review's date plus a short
name for its question.

## What a paper note holds

Every paper note has the same sections, from the engine's `template/note.md`,
so agents and scripts know where each kind of content is.

- **Header**: title, authors, year, venue, DOI or arXiv ID, OpenAlex ID, dates,
  `coverage`, which says what the agent read (including which parts of any
  supplement), and `version`: whether `paper.pdf` is the `publisher`'s
  version of record, an `accepted` author manuscript or a `preprint`. A
  preprint's numbers can differ from the published paper's (Anna,
  2026-11-10).
- **Status**: one of `requested` (a stub waiting for its PDF), `known` (we
  know it exists, from its abstract or a review), `skimmed`, `read`, or
  `core` (the owner should understand it themselves). The agent can propose
  `core`. Only the owner sets it.
- **Supplements** sit beside the paper as `supplement*.pdf`. Papers often
  put the methods a claim depends on there, so a note says in `coverage`
  whether it was read (Anna, 2026-11-10).
- **Purpose and mechanism**: what problem the paper solves, and how. Mentor
  mode searches these.
- **Claims**: what the authors show, each tied to a section, table, figure or
  equation with the passage quoted.
- **Speculation**: what the authors suggest but don't show.
- **Our inferences**: what we conclude ourselves, labeled as ours.
- **The domain section**: what it would take to use this in the owner's
  domain, checked against the domain page.
- **The owner's section**: their own takeaway and doubts. Agents never write
  here. They can ask for it.

## How agents find things

An agent answers a question by walking the tree from `index.md` down, and can
grep any level directly when it already knows what it's looking for.

A personal library is small enough that this needs no database and no
embeddings. At 500 papers, `index.md` would be around 20,000 tokens, which
fits in one read. Published work points the same way:

- Agents do well loading files on demand by path instead of having chunks
  retrieved for them ([Anthropic,
  2025](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
- On small plain-text collections, grep holds up against vector search. The
  evidence is thin: mainly one unrefereed preprint on chat-memory questions.
- RAPTOR (Sarthi et al., ICLR 2024, arXiv:2401.18059) found a tree of
  summaries beat flat retrieval on questions that span a document, and that
  searching every level at once beat walking down from the root. LATTICE
  (Gupta et al., arXiv:2510.13217) and PageIndex have an LLM choose branches
  from node summaries. We've read summaries of these papers, not the papers.

**Every page starts with a short header.** The header is what the index, the
parents and grep read.

```yaml
---
id: 2610.14136-correction-training
type: paper            # map | topic | paper | review
summary: One line shown in the parent and in index.md.
parents: [topics/motion-correction]
status: read           # papers only: known | skimmed | read | core
year: 2026
updated: 2026-11-03    # bump on every change; priors index warns if a parent is older than a child
---
```

The tree's rules:

- A page's one-line summary is what its parents and `index.md` show, so an
  agent can choose a branch without opening it.
- A page can have several parents. A paper can sit under a methods topic and
  an application topic.
- Upper pages summarize, lower pages hold the evidence. Claims on upper pages
  link down to quoted claims on paper notes.
- A topic that lists more than `topic_paper_limit` papers gets split into
  subtopics, so every page can be read in one pass.
- Ingesting a paper updates the summaries of its parents.
- A topic page (`template/topic.md`) lists its papers, then says how they
  connect: what they share, where they disagree, and what one result means
  for another, linked down to the notes. Then its open questions. The owner
  may not have time to read the papers, so the topic page is where the
  connections are drawn for them (Anna, 2026-11-10).
- A paper requested but not yet fetched has a stub note with status
  `requested`, so the request is tracked in git and `priors index` lists all
  of them under "Requested PDFs" in `index.md`. An empty folder or a line of
  prose on a topic page gets lost: git doesn't keep empty folders (Anna,
  2026-11-10).

**`priors index` keeps the tree honest.** It reads every header and rewrites
`index.md` as an outline of the tree, so the index can't drift from the
pages. It refuses (exits with an error) on a page with no summary, a missing
or unknown parent, a paper with no parent, a bad status or version, a
requested paper with no DOI or arXiv ID, or a broken link. It warns about
topics past the size limit, parents whose `updated` date is older than a
child's, a paper with a PDF but no `version`, a supplement that `coverage`
doesn't mention, and a requested paper whose PDF has arrived. Agents run it after every change.

Open: when to add a search engine. The trigger would be grep missing papers
that word the same idea differently ("dropout" against "random masking"),
which mentor mode will hit first, since older papers and other fields use
other words. The likely choice is qmd: a local search tool for markdown that
combines keyword and meaning-based search, reranks with a small local model,
and can be called from Claude Code. It needs Node and about 2 GB of models.

Open: whether to suggest topics by clustering papers automatically, as RAPTOR
and LATTICE build their trees. The proposal is that the owner and the agent
choose topics by hand, and clustering only suggests missing topics during the
monthly check.

## Rules every page obeys

Every claim traces back to a quoted passage in the paper, because summaries of
summaries drift. `priors index` enforces the structural rules now; the
monthly check will enforce the rest (Planned).

- Originals are never edited. That covers PDFs and pasted reviews. The monthly
  check will flag any change git shows to one.
- Every claim on a map or topic page links to a claim on a paper note, and
  that claim quotes the paper. The monthly check will flag claims that don't.
- What the authors show, what they speculate and what we infer stay in
  separate sections.
- A claim taken from a pasted review is credited to the review until someone
  checks it against the paper. The monthly check will list the ones still
  unchecked.
- A citation that can't be found in OpenAlex or PubMed is marked `not found`.
  A citation that exists but says something else is marked `mismatched`.
  Neither is ever silently dropped or fixed.
- An answer to a question cites the notes it used, and says so when the
  library doesn't cover the question.
- PDFs and pasted text are untrusted data. Agents never run code found in them.

## Operations

Each built operation has a procedure in `procedures/`.

| Operation | Procedure | State |
|---|---|---|
| ingest a paper | `ingest-paper.md` | built |
| ingest a pasted review | `ingest-review.md` | built, untested on a real review |
| get PDFs | `fetch-pdfs.md` | built |
| mentor mode | `mentor.md` | built |
| answer a question | `ask.md` | built |
| weekly digest | none yet | Planned |
| monthly check | none yet | Planned |

**Ingest a pasted review.** The owner pastes the review into a file in
`inbox/`, not the chat, so the original stays exact and scripts can read it
(Anna, 2026-10-30). The agent moves it to `reviews/<slug>/original.md`,
cleans it, checks every citation, adds confirmed papers as `known` notes, and
links the review into the map.

Open: which copy method keeps the most links. Pasting into a terminal loses
hyperlinks. A chat interface's copy button and a saved HTML page should be
compared on one real review.

**Weekly digest.** Planned. The agent searches the sources and terms in
`watch.md`, plus new papers citing the library's `core` papers and new
papers by authors in `watch.md`. Each paper is sorted into one of four tiers:

- ignore;
- place on the map from the abstract;
- skim;
- read in depth.

The owner's ratings become the positive and negative examples for the next
digest's recommendations.

Open: whether the digest runs on a schedule, for example with `crontab` or
Slurm's `scrontab`.

**Mentor mode.** Given a problem, the agent:

1. restates it at three levels, from specific to general;
2. searches each level with no date or field filter;
3. finds older papers that many of the results cite: the foundations a
   cluster builds on;
4. returns each candidate with its purpose, its mechanism, what it assumes,
   and what would block it or need changing in the owner's domain.

This follows Kang et al. (ACM TOCHI 2022, doi:10.1145/3530013). In their
study, researchers gained most from papers that matched their problem at a
middle level (the same goal, reached a different way), and they gained by
adapting the idea rather than copying it. We've only read an excerpt of that
paper.

**Translation watch.** Planned, as part of the digest. It covers the nearby
fields in `watch.md`. Candidates get the same domain note as in mentor mode.

**Check the library.** Planned. A monthly pass looks for map claims that don't
trace to a paper note, contradictions, orphan pages and missing links. It also
writes a short "what changed in the field this month" into that month's
digest.

## Sync and storage

A library syncs between machines through git, with PDFs in Git LFS
(Anna, 2026-10-29).

- `init` sets `*.pdf` to go through LFS. Plain git would keep every PDF in
  history forever, and a single PDF can be large: one test paper is 39 MB.
  GitHub refuses files over 100 MB in plain git.
- Notes, text and the map are plain git.
- Every machine that clones the library needs `git-lfs`.

## Data sources

`priors lookup` uses free scholarly databases.

| Source | Used for | State |
|---|---|---|
| OpenAlex | metadata, references, citing papers, citation checks, search |
used now |
| arXiv | metadata for papers not yet in OpenAlex | used now |
| PubMed | biomedical papers, citation checks | not used yet |
| medRxiv/bioRxiv | biomedical preprints | not used yet |
| Semantic Scholar | recommendations from positive and negative examples, citing sentences | not used yet; needs a free API key |

OpenAlex often has no reference list for very new arXiv papers, so mentor
mode's "foundations" step skips them.

Open: adding Semantic Scholar, which needs each owner to get a free API key.

## How we judge it

The test is whether the owner reads more and finds what they need.

- `log.md` records papers triaged and read each week, and each mentor-mode
  result the owner flags as something they didn't know.
- A new feature gets built when a real session needed it ("I wanted to ask X
  and couldn't").

## Not in scope

- Systematic reviews of one narrow question. Deep-research tools do those
  well. The library stores and connects them.
- Reference managers such as Zotero, and note apps such as Obsidian
  (Anna, 2026-10-29).
- A visual citation graph as a standing feature. A figure can be made when
  needed.
- BibTeX management, beyond exporting entries for a paper.

## Status

Built (2026-11-03): the `priors` command (`init`, `index`, `lookup`, `where`),
the template, and the procedures in the table above. One library uses it.

Planned: the weekly digest, the monthly check, Semantic Scholar.

The engine is MIT-licensed and public (Anna, 2026-11-03).

Open: whether to also publish a Claude Code or Codex skill, so agents in the
owner's other repos know to ask the library.
