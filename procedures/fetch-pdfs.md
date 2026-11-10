# Get PDFs

Download open-access papers (arXiv, PubMed Central, or `open_access_pdf` from
`priors lookup get`) directly into `papers/<id>/paper.pdf`.

For the rest, first give each paper a stub note from the engine's
`template/requested.md` (status `requested`, with its DOI or arXiv ID and a
parent topic), then run `priors index`. Its "Requested PDFs" section in
`index.md` lists everything outstanding and where each PDF goes. Ask for
supplements the same way, as `papers/<id>/supplement.pdf`, when a paper's
methods or results are in one.

Then follow `fetch` in `priors.yaml`, which says how this owner gets
paywalled PDFs. Usually that means writing a request and showing it to the
owner. If `fetch` says to write a prompt for another agent, keep it short and
self-contained, because that agent has none of this context:

```
In the git repo <library repo> (clone or pull it first), download these
papers and save each one at the path shown. Don't rename or edit anything
else.

- 10.xxxx/yyyy -> papers/<id>/paper.pdf
- ...

Then git add the PDFs (they go through Git LFS), commit with the message
"Add PDFs: <ids>", and push. Say which you couldn't get and why.
```

When the PDFs arrive, `priors index` warns about each stub whose `paper.pdf`
has arrived. Ingest each one. Check that every PDF is a real PDF whose title
matches, not a login or error page saved under the right name.
