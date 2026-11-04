# Ingest a pasted review

The owner pastes a literature review (from `review_source` in `priors.yaml`)
into a file in `inbox/`. Turn it into a clean review, checked citations, and
`known` paper notes. Run `priors` the way the `run` setting in `priors.yaml`
says.

1. **Move the original.** Pick `<slug>` (date plus a short name for the
   question: `2026-10-30-dce-motion-correction`) and move the file unchanged to
   `reviews/<slug>/original.md`. Never edit it afterwards.
2. **Clean it** into `reviews/<slug>/review.md`. Fix headings, lists, broken
   lines and citation markers. Don't change what it says. Give it a header:
   `type: review`, a one-line `summary` naming the question, `parents` (a map
   page or topic), `updated`. List anything you couldn't repair at the top.
3. **Check every citation** with `priors lookup match "<title>" --year <year>`
   (or `priors lookup get <doi>`). Write one line per citation in
   `reviews/<slug>/citations.md`:
   - `confirmed`: the paper exists and, from its abstract, plausibly says what
     the review claims;
   - `mismatched`: it exists but the review's claim doesn't match it;
   - `not found`.
   Never drop or silently fix a citation.
4. **Add papers.** Each confirmed paper the review cites in support of a claim
   gets a `known` note: header, purpose and mechanism from the abstract, and
   claims credited to the review ("per review <slug>") until someone checks
   them in the paper.
5. **Connect it.** Link the review from the map or topic it informs, put
   papers worth reading into `queue.md`, and write a fetch request
   (`fetch-pdfs.md`) for any that need PDFs.
6. **Rebuild the index** (`priors index` must report no errors) **and log the
   review.**
