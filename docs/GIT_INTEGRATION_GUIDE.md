# Flatnotes-Git Guide

This fork adds Git workflows, Mermaid rendering, S3/R2 attachment storage, frontend image compression, and deployment changes on top of upstream `dullage/flatnotes`.

## Feature Summary

- **Workspace:** view staged/unstaged files, stage or unstage changes, commit, discard, pull, push, and run `Commit & Sync`.
- **History:** browse commits and changed files.
- **Log:** inspect Git operation output for troubleshooting.
- **Conflict UI:** guide users through continue/abort flows when pull or sync conflicts.

The Git integration assumes a flat notes directory. Notes in subdirectories are not managed as Flatnotes notes; use tags such as `#project/alpha` instead.

## Local Development

`npm run dev` starts only the Vite frontend on `127.0.0.1:8080`. API and WebSocket calls are proxied to the backend at `127.0.0.1:8000`, so run both processes.

### One-Time Setup

```bash
pipenv sync --dev
npm install
mkdir -p data
git -C data init -b main
git -C data config user.name "Flatnotes Dev"
git -C data config user.email "dev@flatnotes.local"
touch data/.gitignore
git -C data add .gitignore
git -C data commit -m "Initial notes repo"
```

### Backend

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

### Frontend

```bash
npm run dev
```

Open `http://127.0.0.1:8080`.

## Manual Smoke Test

1. Create or edit a note in the web UI.
2. Open the Git panel and confirm the file appears in Workspace.
3. Run `Commit & Sync` with a message.
4. Confirm the commit with `git -C data log --oneline --decorate -5`.
5. Edit a file directly under `data/`, refresh the UI, and confirm status updates.

For remote testing, use a disposable repository:

```bash
git -C data remote add origin git@github.com:USER/NOTES_TEST_REPO.git
ssh -T git@github.com
```

Use disposable remotes for conflict, reset, discard, and branch-switch testing.

## Automated Checks

This fork only requires tests for fork-owned behavior. Upstream Flatnotes core has little or no coverage, so do not add broad tests for unrelated core code.

```bash
npm run test:js
npm run test:py
npm run build
```

## Docker Deployment

### Minimal `docker run`

```bash
docker run -d \
  --name flatnotes-git \
  -p 8080:8080 \
  -v ./my-notes:/data \
  -v ${HOME}/.ssh/your_git_key:/git_ssh_key_source:ro \
  -v ${HOME}/.ssh/known_hosts:/known_hosts_source:ro \
  -e PUID=1000 \
  -e PGID=1000 \
  -e FLATNOTES_AUTH_TYPE=password \
  -e FLATNOTES_USERNAME=user \
  -e FLATNOTES_PASSWORD=changeMe \
  -e FLATNOTES_SECRET_KEY=aLongRandomSecret \
  -e FLATNOTES_GIT_ENABLED=true \
  -e FLATNOTES_GIT_AUTO_INIT=true \
  -e FLATNOTES_GIT_COMMIT_USER_NAME=flatnotes-bot \
  -e FLATNOTES_GIT_COMMIT_USER_EMAIL=bot@flatnotes.local \
  unleash1371/flatnotes-git:latest
```

### Docker Compose

```yaml
services:
  flatnotes:
    image: unleash1371/flatnotes-git:latest
    container_name: flatnotes-git
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - "./my-notes:/data"
      - "${HOME}/.ssh/your_git_key:/git_ssh_key_source:ro"
      - "${HOME}/.ssh/known_hosts:/known_hosts_source:ro"
    env_file:
      - ./.env
```

Recommended `.env`:

```env
PUID=1000
PGID=1000
FLATNOTES_AUTH_TYPE="password"
FLATNOTES_USERNAME="user"
FLATNOTES_PASSWORD="changeMe"
FLATNOTES_SECRET_KEY="aLongRandomSecret"

FLATNOTES_GIT_ENABLED="true"
FLATNOTES_GIT_AUTO_INIT="true"
FLATNOTES_GIT_REMOTE_NAME="origin"
FLATNOTES_GIT_DEFAULT_BRANCH="main"
FLATNOTES_GIT_PULL_STRATEGY="rebase"
```

Start with:

```bash
docker compose up -d
```

## Remote Git Setup

The notes directory mounted as `/data` must be a Git repository. For a new folder, enable `FLATNOTES_GIT_AUTO_INIT=true` and restart the container. To connect it to a remote:

```bash
cd /path/to/my-notes
git remote add origin git@github.com:USER/NOTES_REPO.git
git push -u origin main
```

The container entrypoint copies the mounted SSH key to the app user and sets `GIT_SSH_COMMAND`. Before starting the container, make sure the host has a known host entry:

```bash
ssh-keyscan github.com >> ~/.ssh/known_hosts
```

## Webhooks

Set a secret with at least 16 characters:

```env
FLATNOTES_GIT_WEBHOOK_SECRET="your-long-random-secret"
```

For GitHub, create a webhook:

- Payload URL: `https://notes.example.com/api/git/webhook/github`
- Content type: `application/json`
- Events: only `Pushes`

If using Traefik/Authelia, leave `/api/git/webhook/github` and `/api/git/ws/status` outside Authelia. Give those routes higher priority than the main app route.

## S3/R2 Attachments

Set the filesystem provider to S3-compatible public bucket mode:

| Variable                                | Description                                                 |
| --------------------------------------- | ----------------------------------------------------------- |
| `FLATNOTES_ATTACHMENT_STORAGE_PROVIDER` | Set to `s3`.                                                |
| `FLATNOTES_S3_ENDPOINT_URL`             | Required for R2/MinIO. For AWS S3, region can be enough.    |
| `FLATNOTES_S3_ACCESS_KEY_ID`            | Access key ID.                                              |
| `FLATNOTES_S3_SECRET_ACCESS_KEY`        | Secret access key.                                          |
| `FLATNOTES_S3_BUCKET_NAME`              | Bucket name.                                                |
| `FLATNOTES_S3_REGION`                   | AWS region, or `auto` for Cloudflare R2.                    |
| `FLATNOTES_S3_PUBLIC_URL`               | Public URL base, for example `https://pub-xxxxxxxx.r2.dev`. |
| `FLATNOTES_S3_PATH_PREFIX`              | Optional object key prefix, for example `flatnotes/`.       |

Frontend image compression is enabled by default:

| Variable                                       | Description                                           |
| ---------------------------------------------- | ----------------------------------------------------- |
| `FLATNOTES_FRONTEND_IMAGE_COMPRESSION_ENABLED` | Set to `false` to disable browser-side compression.   |
| `FLATNOTES_FRONTEND_IMAGE_COMPRESSION_QUALITY` | JPEG/WebP quality from `0.1` to `1.0`; default `0.8`. |
| `FLATNOTES_FRONTEND_IMAGE_MAX_WIDTH`           | Maximum image width before upload; default `1920`.    |

## Git Design Rules

- The server is the source of truth for repository state; clients display server-pushed status.
- `Pull` requires a clean worktree.
- `Commit & Sync` may stage all local changes because the user intent is archive and sync.
- Non-fast-forward `Push` failures should tell users to pull first.
- Conflicts must be visible and route users to the conflict UI.
- Do not add a diff view.
- Do not switch branches with uncommitted changes.
- Preserve the hybrid implementation: `pygit2` for local state/writes, `subprocess` only for remote/auth flows or Git gaps.

## Fork Maintenance

Fork-owned paths:

- `client/git-integration/`
- `server/git_integration/`
- Mermaid integration in `client/components/toastui/`
- S3/R2 attachment handling in `server/attachments/s3.py`
- Small integration points in `client/App.vue`, `client/views/Note.vue`, and `server/main.py`

When syncing upstream, prefer stable releases from `upstream/master`. Preserve upstream core behavior unless it breaks a fork-owned feature. Do not refactor or reformat upstream code for style alone.

## Troubleshooting

- Git panel missing: confirm `FLATNOTES_GIT_ENABLED=true` and restart.
- Repository not initialized: check `FLATNOTES_PATH`; initialize manually or set `FLATNOTES_GIT_AUTO_INIT=true`.
- Vite API failures: backend must run on `127.0.0.1:8000`.
- Fetch/push failures: verify remote URL, upstream branch, SSH key, and `known_hosts`.
- Webhook failures: check secret length, reverse proxy rules, and GitHub delivery logs.
