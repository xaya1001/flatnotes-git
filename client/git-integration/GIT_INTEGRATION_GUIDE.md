# Flatnotes-Git: User Guide

This guide explains the Git integration features added to Flatnotes, how to build the project, and how to set it up correctly.

## Why Git for a Web-Based Notes App?

While Flatnotes provides a great web interface, integrating Git offers powerful advantages, especially for users who also manage their notes across different devices or with local editors like Obsidian.

1.  **Version History & Peace of Mind:** Every commit is a snapshot of your notes. Accidentally delete a paragraph or a whole file? You can easily restore it from your Git history.
2.  **Powerful Syncing:** If you already use Git to sync your notes with a remote repository (like on GitHub), this integration allows you to commit and sync changes directly from the web, without needing shell access.
3.  **Centralized Control:** Manage your entire note-taking workflow—editing, versioning, and syncing—from a single, self-hosted web UI.
4.  **Offline & Online Harmony:** Work on your notes offline in a local editor, push the changes, and then `pull` them into Flatnotes from anywhere. Or, write a quick note in the web UI and `sync` it back to your local setup.

## Features Overview

The Git integration adds a dedicated panel to the Flatnotes UI with three main tabs:

- **Workspace:** View and manage your current changes. Stage, unstage, commit, and discard changes to files. This is where you'll find the main `Commit & Sync` button.
- **History:** Browse your repository's commit history. See who changed what and when. You can also view the files in each commit and restore a file to a previous version.
- **Log:** A real-time log of all Git operations performed by the application, useful for troubleshooting.

## Getting Started: Build & Run with Docker

This project is best run as a Docker container. The following instructions assume you have cloned this repository from GitHub and will build the Docker image locally.

### Step 1: Prepare Your `docker-compose.yml`

Create a `docker-compose.yml` file in the root of the cloned project directory. Here is a recommended template to start with:

```yaml
version: "3.8"

services:
  flatnotes:
    # Use 'build: .'' to build the image from the Dockerfile in the current directory.
    build: .
    container_name: flatnotes
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      # Mount your notes directory here.
      # IMPORTANT: Replace './my-notes' with the actual path to your notes folder.
      - "./my-notes:/data"

      # --- Optional: For Git SSH access (see Git Setup section below) ---
      # - "${HOME}/.ssh/your_git_key:/git_ssh_key_source:ro"
      # - "${HOME}/.ssh/known_hosts:/known_hosts_source:ro"
    environment:
      # Set the user and group ID to match your host user to avoid permission issues.
      # Run `id -u` and `id -g` on your host to get these values.
      PUID: 1000
      PGID: 1000

      # --- Authentication (choose one) ---
      # Option 1: No authentication (easiest to start)
      FLATNOTES_AUTH_TYPE: "none"

      # Option 2: Password-based (recommended)
      # FLATNOTES_AUTH_TYPE: "password"
      # FLATNOTES_USERNAME: "user"
      # FLATNOTES_PASSWORD: "changeMe!"
      # FLATNOTES_SECRET_KEY: "aLongRandomSeriesOfCharacters" # IMPORTANT: Change this!

      # --- Enable Git Integration ---
      FLATNOTES_GIT_ENABLED: "true"
      # You will configure more Git variables in the setup steps below.
```

### Step 2: Build and Start the Container

From the root of the project directory (where your `docker-compose.yml` is), run:

```bash
docker compose up -d --build
```

This command will build the Docker image from the source code and then start the container in the background. Your Flatnotes instance should now be running and accessible at `http://localhost:8080` (or your server's IP).

## Git Setup Instructions

Now that the application is running, let's configure the Git integration.

> **A Critical Note on Directory Structure:**
> This integration is designed for a **flat note structure**. It does not recognize or manage notes located in sub-directories within your main notes folder. If your existing notes (e.g., from an Obsidian vault) are organized into folders, they will not be visible or manageable through the Git UI.
>
> **Recommendation:** Before proceeding, consider flattening your note structure and using tags (`#my-tag`, `#projects/alpha`) for organization instead of folders.

---

### **Scenario 1: You are a new user or have an existing, untracked notes folder.**

This is the path for users who want to start using Git with their notes for the first time.

1.  **Prepare Your Notes Directory:** On your server, create a directory for your notes (e.g., `mkdir my-notes`) and make sure it's the one mounted in your `docker-compose.yml`.

2.  **Configure `docker-compose.yml` for Auto-Initialization:** For a seamless start, add the following to the `environment` section of your `docker-compose.yml`:

    ```yaml
    environment:
      # ... other variables ...
      FLATNOTES_GIT_ENABLED: "true"
      # This will automatically run `git init` inside your notes folder if it's not already a repository.
      FLATNOTES_GIT_AUTO_INIT: "true"
      # It's good practice to set a default author for commits made by the app.
      FLATNOTES_GIT_COMMIT_USER_NAME: "flatnotes-bot"
      FLATNOTES_GIT_COMMIT_USER_EMAIL: "bot@flatnotes.local"
    ```

3.  **Restart Flatnotes:** Run `docker compose restart`. The application will start, initialize a Git repository in your notes directory, and create a `.gitignore` file.

4.  **Next Steps:** Your notes are now version-controlled locally. To sync with a remote provider like GitHub, proceed to **Scenario 2**.

---

### **Scenario 2: You have a local Git repository and want to sync it with a remote (e.g., GitHub).**

This is the path for users who have completed Scenario 1 or already have a Git-enabled notes folder.

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

#### Step 3: Configure SSH Access for Flatnotes

Now, you need to give the Flatnotes container secure, automated access to this remote repository.

1.  **Add Your Git Host to `known_hosts`:** On your **host machine's terminal**, run:

    ```bash
    # For GitHub:
    ssh-keyscan github.com >> ~/.ssh/known_hosts
    ```

    _(Replace `github.com` if you use GitLab, Bitbucket, etc.)_

2.  **Update `docker-compose.yml`:** Uncomment or add the volume mounts for the SSH key and `known_hosts` file. **Replace `your_git_key`** with your key's filename (e.g., `id_ed25519`).
    ```yaml
    services:
      flatnotes:
        # ...
        volumes:
          - "./my-notes:/data"
          # --- Uncomment and configure these two lines for Git SSH access ---
          - "${HOME}/.ssh/your_git_key:/git_ssh_key_source:ro"
          - "${HOME}/.ssh/known_hosts:/known_hosts_source:ro"
        # ...
    ```
    - The `:ro` flag makes the mounts read-only, which is a security best practice.

#### Step 4: Configure Final Environment Variables

Ensure the following environment variables are set in your `docker-compose.yml` or `.env` file:

```yaml
environment:
  # ... other variables like PUID/PGID ...
  FLATNOTES_GIT_ENABLED: "true"
  FLATNOTES_GIT_REMOTE_NAME: "origin"
  FLATNOTES_GIT_DEFAULT_BRANCH: "main"
  FLATNOTES_GIT_PULL_STRATEGY: "rebase" # 'rebase' (default) or 'merge'
```

#### Step 5: Restart and Verify

Restart the container with `docker compose down && docker compose up -d`. Flatnotes should now be able to communicate with your remote repository.

---

## Optional: Real-time Sync with Webhooks

By default, Flatnotes only knows about remote changes when you click "Pull" or when the auto-sync timer runs. To make Flatnotes aware of remote changes instantly (e.g., when you `push` from a local editor), you can set up a webhook.

This feature enables Flatnotes to automatically `git fetch` in the background. This is a **safe, read-only operation** that will not modify your notes. Instead, it will update the UI to show that new changes are available to be pulled.

### Step 1: Set a Webhook Secret

For security, the webhook endpoint is **only active if you set a secret key**.

- Choose a long, random string for your secret (e.g., with `openssl rand -hex 32`).
- Add it to your `environment` section in `docker-compose.yml`:

```yaml
environment:
  # ... all your other variables ...
  FLATNOTES_GIT_WEBHOOK_SECRET: "your-long-random-secret-string-here"
```

### Step 2: Create the Webhook in Your Git Provider

Here are instructions for GitHub. The process is similar for GitLab or other providers.

1.  Navigate to your notes repository on GitHub.
2.  Go to **Settings** > **Webhooks**.
3.  Click **Add webhook**.
4.  Fill out the form:
    - **Payload URL**: Enter the full, publicly accessible URL to your Flatnotes instance, followed by the specific webhook path. For example:
      `https://notes.your-domain.com/api/git/webhook/github`
    - **Content type**: Select `application/json`.
    - **Secret**: Paste the exact same secret string you set for `FLATNOTES_GIT_WEBHOOK_SECRET`.
    - **Which events would you like to trigger this webhook?**: Select **"Let me select individual events."**, then uncheck everything except **"Pushes"**. This is important for efficiency and security.
5.  Ensure **Active** is checked, and click **Add webhook**.

### Step 3: Restart and Test

1.  Restart your Flatnotes container to apply the new secret:
    ```bash
    docker compose restart
    ```
2.  To test, make a change in a local clone of your notes repository and run `git push`.
3.  Check the **Recent Deliveries** tab in your GitHub webhook settings. You should see a recent delivery with a green checkmark and a `202 Accepted` response code.
4.  Open the Flatnotes web UI. The Git status indicator should automatically update to show that there are incoming changes to pull.

You now have a fully real-time, bi-directional Git sync setup for your notes!
