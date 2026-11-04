# Get PDFs

Download open-access papers (arXiv, PubMed Central, or `open_access_pdf` from
`priors lookup get`) directly into `papers/<id>/paper.pdf`.

For the rest, follow `fetch` in `priors.yaml`, which says how this owner gets
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

When the PDFs arrive, pull and ingest each paper.
