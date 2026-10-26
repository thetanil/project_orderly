# Issue tracker: Local Markdown

Issues and specs for this repo live as markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The spec is `.scratch/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`, never a single combined tickets file
- Triage state is recorded as a `Status:` line near the top of each issue file (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `.scratch/<effort>/map.md` (the Notes / Decisions-so-far / Fog body).
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.

## Closing an implementation issue

Acceptance criteria are checked by automated tests, not by hand. When an agent finishes an issue:

- Every criterion gets a test that runs in CI: Api-level tests for behaviour (`tests/`), browser tests for UI behaviour (`tests/ui/`, headless Chromium against the real Api), and CI/packaging checks as tests too (`tests/test_frontend_gates.py`, `tests/test_wheel.py`). A criterion that sounds like "check it looks right in the window" is rewritten into something a browser test can assert, or raised with the owner; it is not left as a manual step.
- Tick `- [x]` only a criterion whose test exists and passes.
- Set `Status: done` when every box is ticked, and list the tests in `## Comments`.
- If a criterion genuinely cannot be automated, set `Status: ready-for-human`, leave that box open and say why in `## Comments`.
- Never leave `ready-for-agent` on an issue that has been worked.
