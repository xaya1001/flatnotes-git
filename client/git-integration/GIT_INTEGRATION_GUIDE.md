# Flatnotes-Git: User Guide

This guide explains the Git integration features added to Flatnotes, why you might want to use them, and how to set them up correctly.

## Why Git for a Web-Based Notes App?

While Flatnotes provides a great web interface, integrating Git offers powerful advantages, especially for users who also manage their notes locally (e.g., with Obsidian).

1.  **Version History & Peace of Mind:** Every commit is a snapshot of your notes. Accidentally delete a paragraph or a whole file? You can easily restore it from your Git history.
2.  **Powerful Syncing:** If you already use `obsidian-git` to sync your Obsidian vault with a remote repository (like on GitHub), this integration allows you to commit and sync changes directly from the web, without needing shell access.
3.  **Centralized Control:** Manage your entire note-taking workflow—editing, versioning, and syncing—from a single, self-hosted web UI.
4.  **Offline & Online Harmony:** Work on your notes offline in Obsidian, push the changes, and then `pull` them into Flatnotes from anywhere. Or, write a quick note in the web UI and `sync` it back to your local vault.

> **Important Note on Folder Structure:**
> This integration is designed for a **flat note structure**. It does not support directories within your notes folder. To organize your notes, leverage Flatnotes' powerful tagging (`#my-tag`) and full-text search features instead of folders.

## Features Overview

The Git integration adds a dedicated panel to the Flatnotes UI with three main tabs:

- **Workspace:** View and manage your current changes. Stage, unstage, commit, and discard changes to files. This is where you'll find the main `Commit & Sync` button.
- **History:** Browse your repository's commit history. See who changed what and when. You can also view the files in each commit and restore a file to a previous version.
- **Log:** A real-time log of all Git operations performed by the application, useful for troubleshooting.

## Setup Instructions

Getting the Git integration to work requires a one-time setup to securely give Flatnotes access to your remote repository.

### Why is the SSH Setup "Complicated"?

For security. We need to provide the application with an SSH key to authenticate with your Git provider (e.g., GitHub). Instead of just mounting your entire `.ssh` directory, which can be risky, we use a safer method: you mount a _specific_ key and your `known_hosts` file, and the application copies them into the container with strict, secure permissions. This prevents accidental exposure of your other keys and ensures the file permissions are correct inside the Docker container.

---

### Step 1: Add Your Git Host to `known_hosts`

On your **host machine's terminal** (not inside the container), run this command. It securely saves your Git provider's fingerprint to prevent man-in-the-middle attacks.

For GitHub:

```bash
ssh-keyscan github.com >> ~/.ssh/known_hosts
```

_(Replace `github.com` if you use GitLab, Bitbucket, etc.)_

### Step 2: Update Your `docker-compose.yml`

You need to mount two files into the container: the specific SSH private key you use for Git and the `known_hosts` file you just updated.

- Edit your `docker-compose.yml`.
- In the `volumes` section for the `flatnotes` service, add the two new lines as shown below.
- **Replace `your_git_key`** with the actual filename of your private key (e.g., `id_ed25519` or `id_rsa`).

```yaml
services:
  flatnotes:
    # ... other configurations like image, container_name, environment ...
    volumes:
      - "./data:/data" # Your existing notes volume

      # --- Add these two lines for Git integration ---
      - "${HOME}/.ssh/your_git_key:/git_ssh_key_source:ro"
      - "${HOME}/.ssh/known_hosts:/known_hosts_source:ro"

    # environment:
    # PUID: 1000
    # PGID: 1000
    # ... other configurations like ports, restart policy ...
```

- The `:ro` flag makes the mounts read-only, which is a security best practice.

### Step 3: Configure Environment Variables

Set the following environment variables in your `docker-compose.yml` or `.env` file to enable and configure the feature.

If your host machine's user ID (UID) or group ID (GID) is different from `1000`, you **must** set the `PUID` and `PGID` environment variables in your `docker run` command or `docker-compose.yml` file to match your host user's IDs.

You can find your PUID and PGID by running `id -u` and `id -g` respectively on your host machine's terminal.

```yaml
environment:
  # --- Core Flatnotes variables ---
  PUID: 1000
  PGID: 1000
  # ... other FLATNOTES_* variables ...

  # --- Git Integration Variables ---
  FLATNOTES_GIT_ENABLED: "true" # Required to enable the feature

  # (Optional) The remote to push/pull from. Defaults to 'origin'.
  FLATNOTES_GIT_REMOTE_NAME: "origin"

  # (Optional) The branch to use. Defaults to 'main'.
  # Set this to 'master' if that's your default branch.
  FLATNOTES_GIT_DEFAULT_BRANCH: "main"

  # (Optional) The name and email for commits made by the app.
  # If not set, it uses Git's system-wide config.
  FLATNOTES_GIT_COMMIT_USER_NAME: "flatnotes-bot"
  FLATNOTES_GIT_COMMIT_USER_EMAIL: "bot@flatnotes.local"

  # (Optional) Auto-sync interval in minutes. 0 to disable.
  # A value of 1-4 is not recommended for performance reasons.
  FLATNOTES_GIT_AUTO_SYNC_INTERVAL: 15

  # (Optional) If true, automatically runs `git init` if the notes
  # directory is not a Git repository. Defaults to `false`.
  FLATNOTES_GIT_AUTO_INIT: "false"
```

### Step 4: Restart the Container

After saving your changes, restart the Flatnotes container for the new settings and volumes to take effect.

```bash
docker compose down
docker compose up -d
```

That's it! When you log into Flatnotes, you should now see the Git status indicator on the right side of the screen. Your setup is complete.
