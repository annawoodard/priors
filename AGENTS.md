# priors engine

This repo is the engine: the `priors` command (`priors/`), the agent
procedures (`procedures/`), and the template for new libraries (`template/`).
No library content lives here. `DESIGN.md` is the design; keep it current
when behavior changes.

- Nothing here may be specific to one owner. Owner-specific settings belong in
  a library's `priors.yaml`; add a setting rather than a special case.
- In procedures, write "the owner" and "the domain", and name settings by
  their `priors.yaml` keys.
- Test changes against a throwaway library made with `priors init` in a
  temporary folder, not inside this repo.
- Commit or push only when asked.
