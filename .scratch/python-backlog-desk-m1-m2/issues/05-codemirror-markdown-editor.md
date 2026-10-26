Status: ready-for-agent
Blocked by: 01, 02, 04
Spec: ../spec.md

# 05 CodeMirror 6 editor for Markdown blocks

User stories: 24

## What to build

Replace textareas for description, acceptance criteria and local notes with a CodeMirror 6 Markdown editor, themed with the app's dark/light tokens, wired through the single mutation path with debounced updates (which also debounce autosave). R22 detection is owned by issue 02 and its quick fix by issue 09; this issue only makes sure editor edits surface R22 inline.

## Acceptance criteria

- [ ] Edits in the editor are undoable with the app-level undo and appear in the Problems list if R22 is violated.
- [ ] Editor theme follows the dark/light toggle; large descriptions stay responsive.

## Comments

Implemented on branch main (backend tests under `tests/`; frontend type-checked, built and driven in a headless browser against the real Api; not yet judged on the owner's desktop).
