# Evaluate the library

Test whether agents can answer the owner's questions from the library, so a
change to the template, the procedures or the tree can be judged by its effect.
The questions live in the library's `eval/questions.md` (format in the engine's
`template/library/eval/questions.md`); results go in `eval/runs/<date>.md`.

1. **Check the gold answers** against the notes before a run whenever a
   question or its notes changed. A gold note is one that must be cited for a
   complete answer.
2. **Run each question in a fresh context** (a new session or sub-agent that
   has seen no other question), in the library directory, following
   `ask.md`. Use more than one model when you can, so a result isn't one
   model's quirk. Record the notes opened, the notes cited, the tool calls
   and the answer.
3. **Score each answer:**
   - retrieval: 2 if every gold note is cited, 1 if some, 0 if none;
   - correctness: 2 right and complete, 1 right but missing a part, 0 wrong
     or unsupported, graded against the notes;
   - separation: shown, speculated and inferred kept apart (yes/no);
   - abstention: says when the library doesn't cover it (yes/no);
   - every quote in the answer appears in the cited note's paper text, and
     every link resolves.
   The agent scores; the owner checks a sample of the correctness grades.
4. **Report** totals by question type and every answer that scored 0 on
   retrieval or correctness, with the notes it opened. Compare with the
   previous run.

Run the full set after any change to the note template, `ask.md` or the
tree's structure, and a short subset monthly. Add a question whenever a real
session fails to locate something.
