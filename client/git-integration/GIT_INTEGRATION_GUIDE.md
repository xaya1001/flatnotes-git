# Flatnotes-Git: User and Deployment Guide

This guide explains the Git integration features added to Flatnotes, how to build the project, and how to set it up correctly for both basic and advanced deployments.

## Why Git for a Web-Based Notes App?

While Flatnotes provides a great web interface, integrating Git offers powerful advantages, especially for users who also manage their notes across different devices or with local editors like Obsidian.

1. **Version History & Peace of Mind:** Every commit is a snapshot of your notes. Accidentally delete a paragraph or a whole file? You can easily restore it from your Git history.
2. **Powerful Syncing:** If you already use Git to sync your notes with a remote repository (like on GitHub), this integration allows you to commit and sync changes directly from the web, without needing shell access.
3. **Centralized Control:** Manage your entire note-taking workflow—editing, versioning, and syncing—from a single, self-hosted web UI.
4. **Offline & Online Harmony:** Work on your notes offline in a local editor, push the changes, and then `pull` them into Flatnotes from anywhere. Or, write a quick note in the web UI and `sync` it back to your local setup.

## Features Overview

The Git integration adds a dedicated panel to the Flatnotes UI with three main tabs:

- **Workspace:** View and manage your current changes. Stage, unstage, commit, and discard changes to files. This is where you'll find the main `Commit & Sync` button.
- **History:** Browse your repository's commit history. See who changed what and when. You can also view the files in each commit.
- **Log:** A real-time log of all Git operations performed by the application, useful for troubleshooting.

---

## Deployment Instructions

You can deploy `flatnotes-git` using a simple Docker command or by integrating it with a reverse proxy like Traefik for a more robust setup.

#### Option 1: Quick Start with `docker run`

For those who prefer not to use Docker Compose, you can start the container with a single `docker run` command.

**Before you run:**

1. Create a directory for your notes: `mkdir my-notes`
2. Replace `your_git_key` in the command below with your actual SSH private key filename (e.g., `id_ed25519`).
3. **IMPORTANT:** Change the default `FLATNOTES_PASSWORD` and `FLATNOTES_SECRET_KEY` to secure, random values.

```bash
docker run -d \
  --name flatnotes-git \
  -p 8080:8080 \
  -v ./my-notes:/data \
  -v ${HOME}/.ssh/your_git_key:/git_ssh_key_source:ro \
  -v ${HOME}/.ssh/known_hosts:/known_hosts_source:ro \
  -e "PUID=1000" \
  -e "PGID=1000" \
  -e "FLATNOTES_AUTH_TYPE=password" \
  -e "FLATNOTES_USERNAME=user" \
  -e "FLATNOTES_PASSWORD=YourStrongPasswordHere" \
  -e "FLATNOTES_SECRET_KEY=YourVeryLongRandomSecretString" \
  -e "FLATNOTES_GIT_ENABLED=true" \
  -e "FLATNOTES_GIT_AUTO_INIT=true" \
  -e "FLATNOTES_GIT_COMMIT_USER_NAME=flatnotes-bot" \
  -e "FLATNOTES_GIT_COMMIT_USER_EMAIL=bot@flatnotes.local" \
  unleash1371/flatnotes-git:latest
```

After running this command, your instance will be available at `http://<your-server-ip>:8080`.

### Option 2: Basic Docker Compose Deployment

This is the simplest way to get started. It exposes Flatnotes directly on a port of your host machine.

#### Step 1: Prepare your `.env` file

Create an `.env` file to store your configuration secrets.

```env
# .env file

# Set the user and group ID to match your host user to avoid permission issues.
# Run `id -u` and `id -g` on your host to get these values.
PUID=1000
PGID=1000

# --- Authentication (choose one) ---
# Option 1: No authentication (easiest to start)
FLATNOTES_AUTH_TYPE="none"

# Option 2: Password-based (recommended)
# FLATNOTES_AUTH_TYPE="password"
# FLATNOTES_USERNAME="user"
# FLATNOTES_PASSWORD="changeMe!" # IMPORTANT: Change this!
# FLATNOTES_SECRET_KEY="aLongRandomSeriesOfCharacters" # IMPORTANT: Change this!

# --- Enable Git Integration ---
FLATNOTES_GIT_ENABLED="true"
FLATNOTES_GIT_AUTO_INIT="true" # Recommended for first-time setup
FLATNOTES_GIT_REMOTE_NAME="origin"
FLATNOTES_GIT_DEFAULT_BRANCH="main"
FLATNOTES_GIT_PULL_STRATEGY="rebase"

# --- Optional: Real-time Fetch with Webhooks (see guide below) ---
# FLATNOTES_GIT_WEBHOOK_SECRET="your-long-random-secret-string-here"
```

#### Step 2: Create `docker-compose.yml`

Create a `docker-compose.yml` file in the same directory.

```yaml
# docker-compose.yml
services:
  flatnotes:
    # Use the pre-built image from Docker Hub
    image: unleash1371/flatnotes-git:latest
    container_name: flatnotes-git
    restart: unless-stopped
    ports:
      # Expose the container's port 8080 to the host's port 8080
      - "8080:8080"
    volumes:
      # Mount your notes directory here.
      # IMPORTANT: Replace './my-notes' with the actual path to your notes folder.
      - "./my-notes:/data"

      # --- Mount your Git SSH key for remote access (see Git Setup section) ---
      # Replace 'your_git_key' with your actual key filename (e.g., id_ed25519)
      - "${HOME}/.ssh/your_git_key:/git_ssh_key_source:ro"
      - "${HOME}/.ssh/known_hosts:/known_hosts_source:ro"
    env_file:
      - ./.env # Load configuration from the .env file
```

#### Step 3: Start the Container

From the directory containing your `.env` and `docker-compose.yml` files, run:

```bash
docker compose up -d
```

Your Flatnotes instance should now be running and accessible at `http://<your-server-ip>:8080`.

---

### Option 3: Advanced Deployment with Traefik & Authelia

This setup uses [Traefik](https://traefik.io/traefik/) as a reverse proxy for automatic HTTPS and [Authelia](https://www.authelia.com/) for single sign-on (SSO) and 2FA. This is a production-ready configuration.

> **Prerequisite:** This guide assumes you have a working Traefik and Authelia setup.

#### Step 1: Prepare your `.env` file

Use the same `.env` file as in the basic setup. You can set `FLATNOTES_AUTH_TYPE` to `none`, as Authelia will handle the access control.

#### Step 2: Create `docker-compose.yml`

This version does not expose any ports directly. Instead, it uses Traefik labels to manage routing.

```yaml
# docker-compose.yml
services:
  flatnotes:
    # Use the pre-built image from Docker Hub
    image: unleash1371/flatnotes-git:latest
    container_name: flatnotes-git
    restart: unless-stopped
    env_file:
      - ./.env # Load configuration from the .env file
    volumes:
      # Mount your notes directory
      - "./my-notes:/data"
      # Mount your Git SSH key
      - "${HOME}/.ssh/your_git_key:/git_ssh_key_source:ro"
      - "${HOME}/.ssh/known_hosts:/known_hosts_source:ro"
    networks:
      # Connect the container to your existing Traefik network
      - traefik_default

    labels:
      # --- Traefik Main Configuration ---
      - "traefik.enable=true"
      # Define a single service that all routers will use
      - "traefik.http.services.flatnotes-git.loadbalancer.server.port=8080"

      # --- Router 1: WebSockets (High Priority, NO Authelia) ---
      # This rule must be very specific to bypass Authelia ONLY for the WebSocket.
      - "traefik.http.routers.flatnotes-git-ws.rule=Host(`notes.yourdomain.com`) && Path(`/api/git/ws/status`)"
      - "traefik.http.routers.flatnotes-git-ws.entrypoints=websecure"
      - "traefik.http.routers.flatnotes-git-ws.service=flatnotes-git"
      - "traefik.http.routers.flatnotes-git-ws.priority=100" # High priority to match first

      # --- Router 2: GitHub Webhook (High Priority, NO Authelia) ---
      # This rule allows GitHub to send webhook notifications without being blocked by Authelia.
      - "traefik.http.routers.flatnotes-git-webhook.rule=Host(`notes.yourdomain.com`) && Path(`/api/git/webhook/github`)"
      - "traefik.http.routers.flatnotes-git-webhook.entrypoints=websecure"
      - "traefik.http.routers.flatnotes-git-webhook.service=flatnotes-git"
      - "traefik.http.routers.flatnotes-git-webhook.priority=100" # High priority

      # --- Router 3: Main Application (Default Priority, WITH Authelia) ---
      # This is the catch-all rule for all other traffic, protected by Authelia.
      - "traefik.http.routers.flatnotes-git-app.rule=Host(`notes.yourdomain.com`)"
      - "traefik.http.routers.flatnotes-git-app.entrypoints=websecure"
      - "traefik.http.routers.flatnotes-git-app.service=flatnotes-git"
      # Apply your Authelia middleware here
      - "traefik.http.routers.flatnotes-git-app.middlewares=authelia@file"
      - "traefik.http.routers.flatnotes-git-app.priority=1" # Low priority

networks:
  # Reference your external Traefik network
  traefik_default:
    external: true
```

**Key points of the Traefik configuration:**

- **Priorities are crucial:** The specific, unprotected routes for WebSockets and webhooks have a _high priority_ (`100`) so Traefik matches them first. The main application route has a _low priority_ (`1`) to act as a fallback for all other requests.
- **Authelia Middleware:** The `authelia@file` middleware is only applied to the main application router, securing your notes while leaving the necessary API endpoints open.

#### Step 3: Start the Container

```bash
docker compose up -d
```

Your instance will now be accessible via `https://notes.yourdomain.com`, protected by Traefik and Authelia.

---

## Git Setup Instructions

These instructions are required for **both** deployment options to enable communication with your remote Git repository (e.g., GitHub).

> **A Critical Note on Directory Structure:**
> This integration is designed for a **flat note structure**. It does not recognize or manage notes located in sub-directories within your main notes folder.
> **Recommendation:** Use tags (`#my-tag`, `#projects/alpha`) for organization instead of folders.

### Scenario 1: New User / Untracked Notes Folder

1. **Prepare Notes Directory:** On your server, create a directory for your notes (e.g., `mkdir my-notes`) and ensure it's the one mounted in your `docker-compose.yml`.
2. **Enable Auto-Init:** In your `.env` file, ensure `FLATNOTES_GIT_AUTO_INIT=true` is set.
3. **Restart Flatnotes:** Run `docker compose restart`. The application will initialize a Git repository in your notes directory.
4. **Next Steps:** Your notes are now version-controlled locally. To sync with a remote provider, proceed to Scenario 2.

### Scenario 2: Syncing an Existing Local Git Repo with a Remote

This is for users who have completed Scenario 1 or already have a Git-enabled notes folder.

#### Step 1: Create a Remote Repository

If you haven't already, create a new, empty repository on your Git provider (e.g., GitHub, GitLab).

#### Step 2: Connect Your Local Repository to the Remote

You will need to access your server's command line for this one-time setup.

```bash
# Navigate to your notes directory on the server
cd /path/to/your/notes

# Add the remote repository URL
# Replace the URL with your own repository's SSH URL
git remote add origin git@github.com:YourUsername/YourNotesRepo.git

# Push your existing commits to the remote
# The -u flag sets the upstream branch for future pulls/pushes
git push -u origin main
```

#### Step 3: Configure SSH Access for the Docker Container

Give the Flatnotes container secure, automated access to this remote repository.

1. **Add Your Git Host to `known_hosts`:** On your **host machine's terminal**, run:

   ```bash
   # For GitHub:
   ssh-keyscan github.com >> ~/.ssh/known_hosts
   ```

   _(Replace `github.com` if you use GitLab, Bitbucket, etc.)_

2. **Verify `docker-compose.yml`:** Ensure the volume mounts for your SSH key and `known_hosts` file are correctly configured as shown in the examples above.

#### Step 4: Restart and Verify

Restart the container with `docker compose down && docker compose up -d`. Flatnotes should now be able to communicate with your remote repository.

---

## Optional: Real-time Fetch with Webhooks

To make Flatnotes aware of remote changes instantly (e.g., when you `push` from a local editor), you can set up a webhook. This enables Flatnotes to automatically `git fetch` in the background.

### Step 1: Set a Webhook Secret

Add this to your `.env` file with a long, random string:

```env
FLATNOTES_GIT_WEBHOOK_SECRET="your-long-random-secret-string-here"
```

### Step 2: Create the Webhook in Your Git Provider (GitHub Example)

1. Navigate to your repository on GitHub -> **Settings** -> **Webhooks** -> **Add webhook**.
2. **Payload URL**: `https://notes.yourdomain.com/api/git/webhook/github`
3. **Content type**: `application/json`
4. **Secret**: Paste the exact secret from your `.env` file.
5. **Events**: Select **"Let me select individual events."** and check **only "Pushes"**.
6. Click **Add webhook**.

### Step 3: Restart and Test

Restart your container (`docker compose restart`). Push a change from a local clone and check the Flatnotes UI. The status indicator should automatically update to show that there are incoming changes to pull.

---

## Bonus: Decoupling Attachments with S3/R2 Storage

For advanced users, storing attachments in S3-compatible object storage keeps your Git repository lean and fast.

### How to Configure

Add the following variables to your `.env` file, customized for your provider.

| Variable                                | Description                                                                                                                                          |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `FLATNOTES_ATTACHMENT_STORAGE_PROVIDER` | Set to `"s3"`.                                                                                                                                       |
| `FLATNOTES_S3_ENDPOINT_URL`             | **(Required for R2/MinIO)** The full endpoint URL. For Cloudflare R2: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`. For AWS S3, leave this blank. |
| `FLATNOTES_S3_ACCESS_KEY_ID`            | **(Required)** Your S3 Access Key ID.                                                                                                                |
| `FLATNOTES_S3_SECRET_ACCESS_KEY`        | **(Required)** Your S3 Secret Access Key.                                                                                                            |
| `FLATNOTES_S3_BUCKET_NAME`              | **(Required)** The name of the S3 bucket where files will be stored.                                                                                 |
| `FLATNOTES_S3_REGION`                   | **(Required)** The AWS region of your bucket (e.g., `us-east-1`). For Cloudflare R2, set this to `auto`.                                             |
| `FLATNOTES_S3_PUBLIC_URL_BASE`          | (Optional but recommended for R2) A custom public URL base for your files. Example: `https://pub-xxxxxxxx.r2.dev`.                                   |

After adding these variables, restart your container. New attachments will now be uploaded to your S3-compatible provider.
