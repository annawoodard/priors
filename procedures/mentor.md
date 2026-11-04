# Mentor mode

The owner describes a problem. Find approaches from any field and any decade
that could help, the way a well-read mentor would.

1. **Restate the problem at three levels**, from specific to general. Example:
   "registering DCE phases despite motion" → "aligning an image time series
   whose contrast changes" → "estimating motion when appearance changes over
   time". Show the owner the three and wait for them to confirm or
   correct them before searching.
2. **Search the library first.** Grep the `Purpose and mechanism` sections of
   paper notes and the topic pages for the key terms of each restatement.
3. **Search outside.** `priors lookup search "<restatement>"` for each level,
   with no date filter. Try the vocabulary of other fields (statistics,
   signal processing, computer vision, neighboring applications) too.
4. **Find the foundations.** Run `priors lookup common-refs <id> <id> ...` on
   the most relevant hits to find older work many of them cite. OpenAlex often
   has no reference list for very new arXiv papers; leave those out of this
   step.
5. **Report 3-7 candidates.** For each: what problem it solves (purpose), how
   (mechanism), what it assumes, and what would block it or need changing in
   the owner's domain (check against the domain page). Say which are in the
   library and which are new. Flag candidates that match the middle restatement
   (same goal, different method). In the study this mode is based on (Kang et
   al., ACM TOCHI 2022), those helped most.
6. **Save what the owner keeps.** Candidates they want become `known` notes or
   queue entries. Log the session, including whether anything was new to them.
