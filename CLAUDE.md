# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

A lightweight shopping list web app (add / edit / delete / check items) built with Streamlit, to be deployed to Streamlit Community Cloud.

- `PRD.md` — source of truth for requirements (Korean). Feature IDs (FR-1…FR-6), user stories (US-1…US-8, P0/P1/P2), data model, UI wireframe, acceptance criteria (§10) are referenced throughout.
- `PROMPTS.md` — the staged build plan the user follows: 1) skeleton, 2) core features, 3) UI design, 4) Playwright review against the PRD, then deployment prep. Each stage limits its scope (e.g. no styling in stage 2, no logic changes in stage 3, review-only in stage 4 — report bugs, don't fix them unless asked).
- Stages 1–4 are done and the review's bugs #1–#3 are fixed. Next: deployment prep (last prompt in `PROMPTS.md`). Not a git repo yet.
- `review/screenshots/` holds Playwright review output; it's not source and should be gitignored.

## Commands

```bash
pip install -r requirements.txt          # streamlit>=1.45 (container key=, tertiary buttons, button icon=)
streamlit run app.py
streamlit run app.py --server.headless true --server.port 8501   # for Playwright
```

There is no test suite or linter in the repo. Verification is done two ways:

- **Logic:** `streamlit.testing.v1.AppTest.from_file("app.py").run()`, then drive widgets by key (`at.checkbox(key=f"chk_{id}")`, `at.button(key=f"del_{id}")`, `at.text_input(key="new_item_name")`). Read state with `at.session_state["items"]`. On Windows set `PYTHONIOENCODING=utf-8` or printing emoji crashes on cp949.
- **UI / browser:** Playwright against the running server (screenshots must be saved under the project dir, e.g. `review/screenshots/`).

Testing gotchas:
- AppTest does not apply `clear_on_submit` (the input clearing happens in the frontend), so "input cleared after add" can only be checked in a browser.
- Playwright `fill()` bypasses the input's `maxlength`; use `pressSequentially()` to test the 50-char limit realistically.
- Each keyed button container (`[class*="st-key-del_"]` etc.) contains a hidden duplicate `<button>`; select with `button:visible` or `getByRole('button', { name: '삭제' })`.
- Wait for Streamlit reruns after each action before asserting.

## Architecture (`app.py`, single file)

- **State** lives in `st.session_state` (MVP; lost on refresh by design). Always use `st.session_state["items"]` — `st.session_state.items` resolves to the mapping's `items()` method. Keys: `items: list[dict]` (`id` uuid4 str, `name`, `checked`, `created_at` ISO 8601), `editing_id` (at most one item in edit mode), `add_warning` / `edit_warning` (flash messages set by callbacks, shown on the next render).
- **Mutations** (`add_item`, `update_item`, `delete_item`, `toggle_item`, `clear_checked`) run only from widget `on_click`/`on_change` callbacks; `render_*` functions only read state. Deleting or clearing the item being edited must also reset `editing_id` (`stop_edit()`).
- **Widget keys derive from the item `id`** (`chk_`, `edit_`, `edit_btn_`, `del_`, `save_`, `cancel_` + id), never the list index, so deletions don't shift other rows' widget state. CSS and tests select on these prefixes, so keep them stable.
- **Validation** is centralized in `validate_name()` (used by add and edit): strips whitespace *and* zero-width chars (ZWSP/ZWNJ/ZWJ/WJ/BOM) at the edges only — `str.strip()` misses them, and inner ZWJs are part of emoji sequences. Max 50 chars, also enforced in the widgets via `max_chars`.
- **Rendering user text safely:** names are shown with `st.text` (no markdown/HTML parsing). Per-item styling (strikethrough when checked) comes from wrapping the name in `st.container(key=f"done-{id}")` / `todo-{id}` and targeting the generated `st-key-…` class in `inject_css()`. Never put user input into `unsafe_allow_html` markup.
- **Edit mode row:** the name input + 💾/✖️ sit in an `st.form` so Enter triggers the first submit button (save). Form widgets can't have `on_change`, so the checkbox stays outside the form; the row's columns switch from `[0.1, 0.7, 0.1, 0.1]` to `[0.1, 0.9]` with nested `[0.7, 0.1, 0.1]` inside the form to keep alignment. There's no 🗑️ in edit mode.
- **Icon buttons** have a text label (`"수정"`, `"삭제"`, `"저장"`, `"취소"`) plus `icon=`; `inject_css()` visually hides the label so screen readers get a real name.
- **`inject_css()`** also forces `stHorizontalBlock` to `nowrap` with `min-width: 0` columns so rows stay on one line at mobile width (Streamlit otherwise stacks columns below ~640px).
- Optional "완료 항목 아래로" toggle (`done_last`) sorts checked items last with a stable sort, at render time only.
- Persistent storage is out of MVP scope; Streamlit Cloud's filesystem is ephemeral, so persistence would need an external store (Google Sheets, Supabase).

## Conventions

- The user communicates in Korean; UI strings, docs, and reports are Korean.
