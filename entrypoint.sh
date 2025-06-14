#!/bin/sh

[ "$EXEC_TOOL" ] || EXEC_TOOL=gosu
[ "$FLATNOTES_HOST" ] || FLATNOTES_HOST=0.0.0.0
[ "$FLATNOTES_PORT" ] || FLATNOTES_PORT=8080

set -e

USER_HOME="/home/appuser"
SOURCE_SSH_DIR="/ssh_source"
FINAL_SSH_DIR="$USER_HOME/.ssh"

echo "Configuring user with UID=${PUID} and GID=${PGID}..."
if ! getent group "${PGID}" > /dev/null; then
    addgroup --system --gid "${PGID}" appgroup
fi
if ! getent passwd "${PUID}" > /dev/null; then
    adduser --system --shell /bin/sh --uid "${PUID}" --gid "${PGID}" appuser
fi

mkdir -p "$USER_HOME"
chown "${PUID}:${PGID}" "$USER_HOME"

if [ -d "$SOURCE_SSH_DIR" ]; then
    mkdir -p "$FINAL_SSH_DIR"

    cp -rL "$SOURCE_SSH_DIR"/. "$FINAL_SSH_DIR"

    chown -R "${PUID}:${PGID}" "$FINAL_SSH_DIR"
    chmod 700 "$FINAL_SSH_DIR"
    find "$FINAL_SSH_DIR" -type f -exec chmod 644 {} \;
    find "$FINAL_SSH_DIR" -type f -name 'id_*' ! -name '*.pub' -exec chmod 600 {} \;
else
    echo "Warning: No source SSH directory found. Git operations may fail."
fi

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
    chown -R ${PUID}:${PGID} ${FLATNOTES_PATH}

    echo Starting flatnotes as user ${PUID}...
    exec ${EXEC_TOOL} ${PUID}:${PGID} ${flatnotes_command}

else
    echo "A user was set by docker, skipping file permission changes."
    echo Starting flatnotes as user $(id -u)...
    exec ${flatnotes_command}
fi
