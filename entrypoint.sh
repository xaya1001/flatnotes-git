#!/bin/sh

[ "$EXEC_TOOL" ] || EXEC_TOOL=gosu
[ "$FLATNOTES_HOST" ] || FLATNOTES_HOST=0.0.0.0
[ "$FLATNOTES_PORT" ] || FLATNOTES_PORT=8080

set -e

USER_HOME="/home/appuser"
SSH_DIR="$USER_HOME/.ssh"
# The file name where the user is expected to mount their key (read-only)
SOURCE_KEY_FILE="$SSH_DIR/id_key_source"
# The file name of the internal copy that the application will use
INTERNAL_KEY_FILE="$SSH_DIR/id_key"

# 1. Prepare the user's .ssh directory
mkdir -p "$SSH_DIR"
chown "${PUID}:${PGID}" "$USER_HOME"
chown "${PUID}:${PGID}" "$SSH_DIR"
chmod 700 "$SSH_DIR"

# 2. If a source key is mounted, copy it and set permissions
if [ -f "$SOURCE_KEY_FILE" ]; then
    echo "Source SSH key found. Setting it up for internal use."
    cp "$SOURCE_KEY_FILE" "$INTERNAL_KEY_FILE"
    chown "${PUID}:${PGID}" "$INTERNAL_KEY_FILE"
    chmod 600 "$INTERNAL_KEY_FILE"

    # 3. Configure Git to use the prepared key
    SSH_COMMAND="ssh -i $INTERNAL_KEY_FILE -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
    ${EXEC_TOOL} "${PUID}:${PGID}" git config --global core.sshCommand "$SSH_COMMAND"
    echo "Git SSH command configured."
else
    echo "No source SSH key found at $SOURCE_KEY_FILE. Skipping SSH key-specific configuration."
fi

# 4. Set other general Git configurations as the target user
${EXEC_TOOL} "${PUID}:${PGID}" git config --global --add safe.directory "${FLATNOTES_PATH}"
${EXEC_TOOL} "${PUID}:${PGID}" git config --global pull.rebase false

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
    chown -R "${PUID}:${PGID}" "${APP_PATH}" "${FLATNOTES_PATH}"

    echo Starting flatnotes as user ${PUID}...
    exec ${EXEC_TOOL} ${PUID}:${PGID} ${flatnotes_command}

else
    echo "A user was set by docker, skipping file permission changes."
    echo Starting flatnotes as user $(id -u)...
    exec ${flatnotes_command}
fi
