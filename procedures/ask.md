# Answer a question about the literature

1. **Search first.** Grep the page headers and text across every level for
   the question's terms, naming the files by pattern instead of searching
   recursively: `grep -i -E '<terms>' papers/*/note.md topics/*.md map/*.md`
   (add `papers/*/paper.txt` to search full texts). Libraries often live on
   shared filesystems where recursive walks are restricted. Search in
   several phrasings: the owner's words, the field's usual term, and the
   term a neighbouring field would use. Open the matching topic pages, then
   their notes. Read all of `index.md` only for survey questions ("what does
   the library cover on X?").
2. **Load one topic at a time.** Read at most one topic's notes in a pass
   (about 40,000 tokens). For a question across the whole library, give each
   relevant topic to a sub-agent that reads its notes and returns a digest of
   at most about 2,000 tokens, with links to the notes it used.
3. **Answer** with links to the notes you used, and quote the paper where it
   matters. Keep what papers show apart from what they speculate and from
   your own inference.
4. Say plainly when the library doesn't cover the question, and offer to
   search outside (`priors lookup`) or run mentor mode.
5. If the owner wants the answer kept, save it as a topic page and rebuild the
   index. Log the question.

From another repo, set `PRIORS_LIBRARY` to the library's path so commands
can locate it. Running `priors where` inside the library prints the path.
