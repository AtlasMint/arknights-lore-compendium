# Agent Guide




## Git

Follow `docs/COMMITS.md`. In practice `main` uses **`type(scope): description`** — `feat:`,
`fix(ingest):`, `ci:`, `docs(repo):`.

- **One aspect per code commit** (@fooruiheng). A commit carries a single feature, fix or concern —
  if you fixed two unrelated things, that is two commits. **Documentation and assets are the
  exception and may be committed in bulk.**
- **Keep documentation out of code commits.** Split them even when the docs describe the code you
  just wrote.
- **The body carries the why**, in the style already in this history: what was measured rather than
  assumed, and an explicit note of what was deliberately _not_ done and why.
- **Never rewrite published history.** Rewording or squashing commits that are already on `origin`
  rewrites other people's work and breaks every clone. Adopt conventions going forward instead.
- Commit and push only when asked.

## Consumed instruction docs

A doc written to direct one piece of work — a migration plan, a port brief, a one-off
runbook, anything handed over as "do this" — is **spent** once that work is done. Leaving it
at the repo root or loose in [`docs/`](docs/) reads as live guidance and invites a later
agent to start the job again.

So, in the same change that finishes the work:

1. **Record the outcome in the doc first.** Move its status line to done, and append a short
   note covering anything the plan left open — decisions taken in the doing, where the
   implementation departed from the brief, and what is still owed. The plan is what someone
   intended; that note is what actually happened, and it is the half worth keeping.
2. **Move it to [`docs/archive/`](docs/archive/)** — `git mv`, never delete. The reasoning
   is the record even when the instructions are stale, and deletion is the one thing that
   cannot be undone from history alone.
3. **Repoint every reference**, including prose mentions in source comments, not just
   markdown links. `grep -rn "<DOC-NAME>" --include='*.md' --include='*.tsx'` over the repo
   catches them.

`docs/` proper is for **living** documentation — [`COMMITS.md`](docs/COMMITS.md) is the
example, and on `main` it sat alongside `DEPLOY.md` and `MARKETING-PAGE-HISTORY.md` —
things a reader consults because they are still true. `docs/archive/` is for documents
that were true once. Judge by whether the doc still tells someone what to do, not by how
old it is.
