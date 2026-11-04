# Ingest a paper

Turn a PDF in `papers/<id>/` into a note, and place it in the tree. Run
`priors` the way the `run` setting in `priors.yaml` says.

1. **Name the folder** if it isn't named yet: the arXiv ID (or a short name
   built from the DOI), a hyphen, and a few words from the title:
   `2610.14136-correction-training`.
2. **Get the text.** If `paper.txt` is missing:
   `pdftotext -layout papers/<id>/paper.pdf papers/<id>/paper.txt`. Tables
   often come out jumbled; when a number you quote is unclear, render
   that PDF page (`pdftoppm -f N -l N -png`).
3. **Get metadata.** `priors lookup get arxiv:<id>` or `priors lookup get
   <doi>`. Copy title, authors, year, venue, DOI and OpenAlex ID into the
   header.
4. **Read the paper.** At least the abstract, introduction, method, main
   results and conclusion. Record what you read in `coverage:`.
5. **Write `note.md`** from the engine's `template/note.md`:
   - a one-line `summary` saying what the paper does and its main result;
   - purpose and mechanism;
   - claims, each with a section, table, figure or equation and the passage
     or number quoted;
   - speculation, then our inferences, kept apart;
   - the domain section, headed with the value of `domain.note_section`,
     checked against the domain page;
   - the owner's section, headed with the value of `take_heading`, left
     empty. Never write in it.
6. **Set `status`.** `known` unless the owner says they skimmed or read it.
   Only the owner sets `core`.
7. **Place it.** Pick one or more parent topics. Create a topic if none fits,
   with a map page as its parent. Add the paper to each parent's list with a
   one-line description, update the parent's summary if it no longer covers
   its children, and set `updated` to today's date on every page you changed.
8. **Rebuild the index.** `priors index` must report no errors.
9. **Log it** in `log.md`, and ask the owner for their take if they read it.
