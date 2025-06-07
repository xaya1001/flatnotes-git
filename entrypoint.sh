#!/bin/sh

[ "$EXEC_TOOL" ] || EXEC_TOOL=gosu
[ "$FLATNOTES_HOST" ] || FLATNOTES_HOST=0.0.0.0
[ "$FLATNOTES_PORT" ] || FLATNOTES_PORT=8080

set -e

if [ -n "$FLATNOTES_GIT_SSH_COMMAND" ] && echo "$FLATNOTES_GIT_SSH_COMMAND" | grep -q -- "-i "; then
    SSH_KEY_PATH=$(echo "$FLATNOTES_GIT_SSH_COMMAND" | sed -n 's/.*-i \([^ ]*\).*/\1/p')
    USER_HOME="/home/appuser"

    echo "Setting up Git and SSH..."
    mkdir -p "$USER_HOME/.ssh"
    
    if [ -f "$SSH_KEY_PATH" ]; then
        cp "$SSH_KEY_PATH" "$USER_HOME/.ssh/id_git"
        chown -R ${PUID}:${PGID} "$USER_HOME"
        chmod 700 "$USER_HOME/.ssh"
        chmod 600 "$USER_HOME/.ssh/id_git"
        
        ${EXEC_TOOL} ${PUID}:${PGID} git config --global core.sshCommand "ssh -i $USER_HOME/.ssh/id_git -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
        ${EXEC_TOOL} ${PUID}:${PGID} git config --global --add safe.directory ${FLATNOTES_PATH}
        ${EXEC_TOOL} ${PUID}:${PGID} git config --global pull.rebase false

        echo "Git and SSH setup complete."
    else
        echo "Warning: SSH key specified in FLATNOTES_GIT_SSH_COMMAND not found at '$SSH_KEY_PATH'."
    fi
fi

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
    chown -R ${PUID}:${PGID} ${FLATNOTES_PATH}

    echo Starting flatnotes as user ${PUID}...
    exec ${EXEC_TOOL} ${PUID}:${PGID} ${flatnotes_command}

else
    echo "A user was set by docker, skipping file permission changes."
    echo Starting flatnotes as user $(id -u)...
    exec ${flatnotes_command}
fi
