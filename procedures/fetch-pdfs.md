# Get PDFs

Download open-access papers (arXiv, PubMed Central, or `open_access_pdf` from
`priors lookup get`) directly into `papers/<id>/paper.pdf`.

For the rest, first give each paper a stub note from the engine's
`template/requested.md` (status `requested`, with its DOI or arXiv ID and a
parent topic), then run `priors index`. Its "Requested PDFs" section in
`index.md` lists everything outstanding and where each PDF goes. Ask for
supplements the same way, as `papers/<id>/supplement.pdf`, when a paper's
methods or results are in one.

Then run `priors fetch-prompt` (every requested paper) or
`priors fetch-prompt <page>` (every paper under a page that lacks
`paper.pdf`, including abstract-only and PubMed Central text notes; no stub
needed). It prints a self-contained prompt for an agent on a machine with
library access, with save paths and a follow-up step from `fetch_prompt` in
`priors.yaml`. Show it to the owner as printed, and follow `fetch` in
`priors.yaml` for anything else about how this owner gets paywalled PDFs
(another folder to check first, say).

When the PDFs arrive, `priors index` warns about each stub whose `paper.pdf`
has arrived. Ingest each one. Check that every PDF is a real PDF whose title
matches, not a login or error page saved under the right name.
