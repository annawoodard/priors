# priors

A literature library that coding agents (Claude Code, Codex) keep for you, in
plain markdown and git, so you can ask any model you like about your papers.

- **Ingest** papers, and literature reviews you paste in from a
  deep-research tool (such as ChatGPT or Gemini Deep Research), into notes
  where every claim quotes the paper and every citation is checked against
  OpenAlex, an open catalog of scholarly papers.
- **Browse** a tree of pages (areas, topics, papers, full text). Agents find
  their way through it from one generated index, with no database.
- **Mentor mode**: describe a problem, get approaches from any field and
  decade, with what it would take to use each in your domain.

`DESIGN.md` says how it works and what's still open.

## Set up

Needs Python 3.9+, `pyyaml`, `git-lfs`, and `pdftotext` from poppler.

```bash
git clone https://github.com/annawoodard/priors ~/priors
pip install -e ~/priors
priors init ~/my-library --owner Sam --domain "prostate MRI"
cd ~/my-library && git init -b main && git lfs install --local
```

Then edit `priors.yaml`: who you are, your domain, how agents should run
`priors` on this machine, and how paywalled PDFs, which agents can't download,
get into the library. Keep the library repo private if it will hold publisher
PDFs.

## Use

Open an agent in the library folder. It reads `AGENTS.md`, which points it at
`priors.yaml` and the procedures in this repo. Then ask, for example:

- "Ingest papers/2401.18059-raptor." (after saving the PDF as
  `papers/<id>/paper.pdf`)
- "Ingest the inbox." (after pasting a review into `inbox/<name>.md`)
- "Mentor mode: I need to register contrast-enhanced frames despite motion."
- "What does the library say about label noise?"

The command line does the mechanical parts:

```
priors index [--check]     rebuild index.md and check the tree
priors lookup get <doi>    metadata from OpenAlex; see `priors lookup -h`
priors where               print the library and engine paths
```

From another repo, set `PRIORS_LIBRARY=/path/to/library` and agents there can
query the library too.

## License

MIT. See `LICENSE`.
