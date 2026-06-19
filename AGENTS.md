# Repository Guidelines

## Project Structure & Module Organization

flatnotes is a Vue 3/Vite frontend with a FastAPI backend. This fork owns Git integration, the note outline side panel, Mermaid rendering, S3/R2 uploads, image compression, CI, and deployment changes. Keep fork code in `client/git-integration/`, `client/note-outline/`, `client/right-tool-rail/`, `server/git_integration/`, Mermaid Toast UI files, `server/attachments/s3.py`, `tests/`, and integration points like `client/App.vue`, `client/views/Note.vue`, and `server/main.py`. Treat `server/notes/`, `server/auth/`, and generic UI as upstream vendor code. `docs/GIT_INTEGRATION_GUIDE.md` is the canonical fork guide.

## Fork Scope & Upstream Sync

Prefer modular additions over core rewrites. Keep upstream-file patches small and merge-friendly. Merge stable releases from `upstream/master`; preserve upstream behavior unless it breaks fork features. Do not reformat upstream code for style alone.

## Build, Test, and Development Commands

- `pipenv sync --dev`: install Python dependencies.
- `npm install`: install frontend tooling.
- Backend dev server:
  ```bash
  FLATNOTES_PATH="$PWD/data" \
  FLATNOTES_AUTH_TYPE=none \
  FLATNOTES_GIT_ENABLED=true \
  FLATNOTES_GIT_AUTO_INIT=true \
  FLATNOTES_GIT_REMOTE_NAME=origin \
  FLATNOTES_GIT_DEFAULT_BRANCH=main \
  FLATNOTES_GIT_COMMIT_USER_NAME="flatnotes-dev" \
  FLATNOTES_GIT_COMMIT_USER_EMAIL="dev@flatnotes.local" \
  pipenv run python -m uvicorn main:app --app-dir server --host 127.0.0.1 --port 8000 --reload
  ```
- `npm run dev`: start Vite only on `127.0.0.1:8080`; backend API and WebSocket calls proxy to the separate FastAPI server.
- `npm run build`: build `client/dist/`.
- `npm run test:js`: run Vitest coverage.
- `npm run test:py`: run backend tests with Python coverage and write `coverage/py-coverage.xml`.
- `npm run test:e2e`: run Playwright e2e smoke coverage against local FastAPI/Vite using `data/`.
- `npm run git-test`: run backend, frontend, and e2e fork test suites.

## Coding Style & Naming Conventions

Use ES modules and Vue single-file components. Name Vue components in PascalCase, stores/composables in camelCase, and tests as `*.spec.js`. Python uses snake_case. Format Python with Black/isort; Prettier formats frontend, JSON, styles, and Markdown.

## Testing Guidelines

Upstream flatnotes core has no test coverage; this fork only requires tests for fork-owned behavior. Keep tests under `tests/`: Vitest specs in `tests/client/`, backend pytest coverage in `tests/server/`, and Playwright smoke coverage in `tests/e2e/`. Do not test unrelated upstream core code.

Choose verification by touched surface. Backend Git/S3 changes need focused pytest coverage or `npm run test:py`. Frontend Git/Mermaid/image-compression changes need focused Vitest coverage or `npm run test:js`. Cross-boundary config, API shape, or UI integration changes should run `npm run git-test` and `npm run build` when feasible. Document any skipped check and why.

Codex sandbox caveat: backend Git tests can fail or hang in the sandbox because the environment can block `asyncio.to_thread`, local thread lock waiting, or localhost access used by pytest/e2e. If `npm run test:py`, `pipenv run pytest tests/server -vv`, or `npm run test:e2e` fails with a hang, timeout, or `Operation not permitted`, rerun the same command outside the sandbox before blaming the code. In this environment, use escalated execution for those checks and report both results when they differ. A non-sandbox pass means the original failure was a Codex runtime restriction, not a repository bug.

## Git Integration Design Rules

- The server is the source of truth for repository state; clients display server-pushed or server-fetched status.
- Git mutating operations must use the shared Git operation lock and refresh or broadcast status after state changes.
- Pull and sync must surface conflicts and route users to the conflict UI.
- `Pull` requires a clean worktree.
- `Commit & Sync` may stage all local changes because the user intent is archive and sync.
- Non-fast-forward `Push` failures tell users to pull first.
- Do not add diff view.
- Preserve the hybrid approach: `pygit2` for local state/writes, `subprocess` only for remote/auth flows or Git gaps.
- Never switch branches with uncommitted changes.

## Fork Feature Rules

Mermaid work belongs in Toast UI integration points and must preserve regular Markdown rendering. S3/R2 attachment changes must preserve filesystem fallback and local attachment serving. Frontend image compression must remain controlled by `FLATNOTES_FRONTEND_IMAGE_*` config and must not break non-image uploads.

New or changed `FLATNOTES_*` configuration must update config loading, frontend-visible config response models when applicable, docs, and focused tests. Validate paths, branch names, filenames, and user-supplied remote inputs at the server boundary.

## Commit & Pull Request Guidelines

Use a concise conventional subject plus a short body. Do not use only a one-line subject for non-trivial changes. Prefer types such as `feat`, `fix`, `refactor`, `test`, `docs`, `ci`, and `chore`; keep the subject imperative and under roughly 72 characters.

Example:

```text
feat: automate GitHub release creation

- reuse an existing fork release tag on reruns
- build Docker images before publishing the Git tag
- create a GitHub Release with generated notes
```

Keep commit bodies to 2-4 bullets summarizing what changed and why. Avoid implementation transcripts or exhaustive file lists. Keep commits focused. PRs should describe the change, list tests run, link issues, and include screenshots for UI changes. Mention new config, migrations, or Git/S3 behavior changes.

## Security & Configuration Tips

Do not commit note data, credentials, tokens, SSH keys, or bucket secrets. Treat `data/`, `.flatnotes`, local remotes, and local S3/R2 settings as environment-specific. Preserve Git operation locks and avoid logging secret values or full credential-bearing URLs.
