# Repository Guidelines

## Project Structure & Module Organization

flatnotes is a Vue 3/Vite frontend with a FastAPI backend. This fork owns Git integration, Mermaid rendering, S3/R2 uploads, image compression, CI, and deployment changes. Keep fork code in `client/git-integration/`, `server/git_integration/`, Mermaid Toast UI files, `server/attachments/s3.py`, and integration points like `client/App.vue`, `client/views/Note.vue`, and `server/main.py`. Treat `server/notes/`, `server/auth/`, and generic UI as upstream vendor code.

## Fork Scope & Upstream Sync

Prefer modular additions over core rewrites. Keep upstream-file patches small and merge-friendly. Merge stable releases from `upstream/master`; preserve upstream behavior unless it breaks fork features. Do not reformat upstream code for style alone.

## Build, Test, and Development Commands

- `pipenv sync --dev`: install Python dependencies.
- `npm install`: install frontend tooling.
- `npm run dev`: start Vite.
- `npm run build`: build `client/dist/`.
- `npm run test:js`: run Vitest coverage.
- `npm run test:py`: run backend tests.
- `npm run git-test`: run both test suites.

## Coding Style & Naming Conventions

Use ES modules and Vue single-file components. Name Vue components in PascalCase, stores/composables in camelCase, and tests as `*.spec.js`. Python uses snake_case. Format Python with Black/isort; Prettier formats frontend, JSON, styles, and Markdown.

## Testing Guidelines

Upstream flatnotes core has no test coverage; this fork only requires tests for fork-owned behavior. Add Vitest specs under `client/git-integration/tests/` for Git UI, stores, composables, Mermaid, and fork frontend integration. Add pytest coverage under `server/git_integration/test/` for Git workflows, APIs, concurrency, attachments, and S3/R2. Do not test unrelated upstream core code.

## Git Integration Design Rules

The server is the source of truth for repository state; clients display server-pushed status. Pull and sync must surface conflicts and route users to the conflict UI. `Pull` requires a clean worktree; non-fast-forward `Push` failures tell users to pull first. Do not add diff view. Preserve the hybrid approach: `pygit2` for local state/writes, `subprocess` only for remote/auth or Git gaps. Never switch branches with uncommitted changes.

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

Do not commit note data, credentials, tokens, SSH keys, or bucket secrets. Treat `data/`, `.flatnotes`, and local remotes as environment-specific. Validate paths and branch names, and preserve Git operation locks.
