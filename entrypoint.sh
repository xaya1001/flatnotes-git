#!/bin/sh

[ "$EXEC_TOOL" ] || EXEC_TOOL=gosu
[ "$FLATNOTES_HOST" ] || FLATNOTES_HOST=0.0.0.0
[ "$FLATNOTES_PORT" ] || FLATNOTES_PORT=8080

set -e

USER_HOME="/home/appuser"
USER_SSH_DIR="$USER_HOME/.ssh"

# Source paths for mounted files
SOURCE_SSH_KEY_PATH="/git_ssh_key_source"
SOURCE_KNOWN_HOSTS_PATH="/known_hosts_source"

# Path for the key inside the container
USER_SSH_KEY_PATH="$USER_SSH_DIR/user_git_ssh_key"

echo "Configuring user with UID=${PUID} and GID=${PGID}..."
if ! getent group "${PGID}" > /dev/null; then
    addgroup --system --gid "${PGID}" appgroup
fi
if ! getent passwd "${PUID}" > /dev/null; then
    adduser --system --shell /bin/sh --uid "${PUID}" --gid "${PGID}" appuser
fi

# Create user's home and .ssh directory
mkdir -p "$USER_SSH_DIR"
chown -R "${PUID}:${PGID}" "$USER_HOME"

# --- Securely copy and permission SSH files ---
if [ -f "$SOURCE_SSH_KEY_PATH" ]; then
    echo "Copying SSH private key..."
    cp "$SOURCE_SSH_KEY_PATH" "$USER_SSH_KEY_PATH"
    chown "${PUID}:${PGID}" "$USER_SSH_KEY_PATH"
    chmod 600 "$USER_SSH_KEY_PATH"

    # Configure Git to use the copied key
    export GIT_SSH_COMMAND="ssh -i ${USER_SSH_KEY_PATH} -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes"
else
    echo "Warning: No SSH key found at ${SOURCE_SSH_KEY_PATH}. Git operations requiring SSH will fail."
fi

if [ -f "$SOURCE_KNOWN_HOSTS_PATH" ]; then
    echo "Copying known_hosts file..."
    cp "$SOURCE_KNOWN_HOSTS_PATH" "$USER_SSH_DIR/known_hosts"
    chown "${PUID}:${PGID}" "$USER_SSH_DIR/known_hosts"
    chmod 644 "$USER_SSH_DIR/known_hosts"
fi

# Ensure the .ssh directory itself has the correct permissions
chmod 700 "$USER_SSH_DIR"

# Ensure git trusts the repository directory
${EXEC_TOOL} "${PUID}:${PGID}" git config --global --add safe.directory "${FLATNOTES_PATH}"

echo "\
======================================
======== Welcome to flatnotes ========
======================================

If you enjoy using flatnotes, please
consider sponsoring the project at:

https://sponsor.flatnotes.io

It would really make my day 🙏.

──────────────────────────────────────
"

flatnotes_command="python -m \
                  uvicorn \
                  main:app \
                  --app-dir server \
                  --host ${FLATNOTES_HOST} \
                  --port ${FLATNOTES_PORT} \
                  --proxy-headers \
                  --forwarded-allow-ips '*'"

if [ `id -u` -eq 0 ] && [ `id -g` -eq 0 ]; then
    echo Setting file permissions...
    chown -R ${PUID}:${PGID} ${APP_PATH} ${FLATNOTES_PATH}

    echo Starting flatnotes as user ${PUID}...
    exec ${EXEC_TOOL} ${PUID}:${PGID} ${flatnotes_command}

else
    echo "A user was set by docker, skipping file permission changes."
    echo Starting flatnotes as user $(id -u)...
    exec ${flatnotes_command}
fi
