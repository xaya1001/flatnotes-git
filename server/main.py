from contextlib import asynccontextmanager
from typing import List, Literal

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import api_messages
from attachments.base import BaseAttachments
from attachments.models import AttachmentCreateResponse
from auth.base import BaseAuth
from auth.models import Login, Token
from global_config import AuthType, GlobalConfig, GlobalConfigResponseModel
from helpers import replace_base_href
from logger import logger
from notes.base import BaseNotes
from notes.models import Note, NoteCreate, NoteUpdate, SearchResult

global_config = GlobalConfig()
auth: BaseAuth = global_config.load_auth()
note_storage: BaseNotes = global_config.load_note_storage()
attachment_storage: BaseAttachments = global_config.load_attachment_storage()
auth_deps = [Depends(auth.authenticate)] if auth else []
router = APIRouter()

# --- Scoped Git Imports and Setup ---
git_integration_router = None
if global_config.flatnotes_git_enabled:
    try:
        from git_integration import git_config
        from git_integration.git_config import initialize_git_config

        initialize_git_config(global_config)
        from git_integration.git_logger import LogLevel, add_git_log
        from git_integration.git_router import get_git_manager
        from git_integration.git_router import router as git_integration_router
        from git_integration.webhook_handler import verify_github_signature
        from git_integration.websockets import connection_manager
    except ImportError as e:
        logger.error(f"FLATNOTES_GIT_ENABLED is true, but a module failed to load: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    logger.info("Application startup...")

    if git_config.GIT_ENABLED:
        logger.info("Git integration is enabled.")

        # Determine the active automatic sync method
        if git_config.GIT_WEBHOOK_SECRET:
            logger.info("Sync Mode: Real-time fetch via Webhook is active.")

        elif git_config.GIT_AUTO_FETCH_INTERVAL > 0:
            interval = git_config.GIT_AUTO_FETCH_INTERVAL
            logger.info(
                f"Sync Mode: Scheduled fetch is active with an interval of {interval} minutes."
            )

            scheduler = BackgroundScheduler(daemon=True)

            async def scheduled_fetch_job():
                """A lightweight job that only performs a git fetch."""
                if git_config.is_auto_sync_paused():
                    return

                logger.debug("Executing scheduled git fetch...")
                try:
                    manager = get_git_manager()
                    manager.fetch_only()
                    await connection_manager.broadcast_status_update()
                except Exception as e:
                    logger.error(f"Scheduled git fetch failed: {e}")
                    add_git_log(
                        LogLevel.ERROR,
                        "Scheduled fetch failed",
                        details=str(e),
                        persist=True,
                    )

            scheduler.add_job(scheduled_fetch_job, "interval", minutes=interval)
            scheduler.start()
            app.state.scheduler = scheduler
            logger.info("Scheduler for auto-fetch started.")

        else:
            logger.info("Sync Mode: Manual sync only. No automatic fetch configured.")

    yield

    # --- Shutdown logic ---
    logger.info("Application shutdown...")
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        logger.info("Shutting down scheduler.")
        app.state.scheduler.shutdown()


app = FastAPI(
    docs_url=global_config.path_prefix + "/docs",
    openapi_url=global_config.path_prefix + "/openapi.json",
    lifespan=lifespan,
)


# --- Webhook Endpoint ---
if git_integration_router:

    @app.post(
        f"{global_config.path_prefix}/api/git/webhook/github",
        # The endpoint itself has no dependencies, we check inside.
        include_in_schema=False,
    )
    async def github_webhook_receiver(
        request: Request,
        background_tasks: BackgroundTasks,
    ):
        """
        Receives webhook events from GitHub.
        If a secret is configured, it verifies the signature.
        On a valid 'push' event, it triggers a 'git fetch'.
        """
        # 1. Check if the feature is configured to be active.
        if not git_config.GIT_WEBHOOK_SECRET:
            logger.info(
                "Webhook received but ignored: FLATNOTES_GIT_WEBHOOK_SECRET is not set."
            )
            raise HTTPException(
                status_code=412,
                detail="Webhook feature is disabled: secret is not configured on the server.",
            )

        # 2. Verify the signature (now that we know a secret exists).
        await verify_github_signature(
            request, request.headers.get("x-hub-signature-256")
        )

        # 3. Process the event.
        event_type = request.headers.get("X-GitHub-Event")
        if event_type != "push":
            return {
                "status": "event_ignored",
                "reason": f"Event type '{event_type}' is not 'push'.",
            }

        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload.")

        expected_ref = f"refs/heads/{git_config.GIT_DEFAULT_BRANCH}"
        if payload.get("ref") != expected_ref:
            return {
                "status": "push_ignored",
                "reason": f"Push was not to the default branch ('{git_config.GIT_DEFAULT_BRANCH}').",
            }

        pusher_name = payload.get("pusher", {}).get("name", "unknown")
        logger.info(
            f"Webhook: Received valid push event from '{pusher_name}'. Triggering fetch."
        )
        add_git_log(
            LogLevel.INFO,
            "Webhook: Push event received",
            details={"pusher": pusher_name},
        )

        async def fetch_and_broadcast_task():
            """The actual git fetch operation, run in the background."""
            try:
                manager = get_git_manager()
                result = manager.fetch_only()  # <--- CALLING FETCH_ONLY
                add_git_log(
                    LogLevel.SUCCESS, "Webhook: Fetch successful", details=result
                )
            except Exception as e:
                logger.error(f"Webhook fetch task failed: {e}")
                add_git_log(LogLevel.ERROR, "Webhook: Fetch failed", details=str(e))
            finally:
                # Always broadcast, so the UI can update its ahead/behind status.
                await connection_manager.broadcast_status_update()

        background_tasks.add_task(fetch_and_broadcast_task)

        return {"status": "accepted", "detail": "Fetch operation scheduled."}


# Conditionally include the Git integration router
if git_integration_router:
    app.include_router(
        git_integration_router,
        prefix=f"{global_config.path_prefix}/api/git",
        tags=["git"],
    )
    logger.info("Git integration API routes included.")
else:
    logger.info(
        "Git integration is disabled or failed to load. API routes NOT included."
    )

replace_base_href("client/dist/index.html", global_config.path_prefix)


# region UI
@router.get("/", include_in_schema=False)
@router.get("/login", include_in_schema=False)
@router.get("/search", include_in_schema=False)
@router.get("/new", include_in_schema=False)
@router.get("/note/{title}", include_in_schema=False)
def root(title: str = ""):
    with open("client/dist/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)


# endregion


# region Login
if global_config.auth_type not in [AuthType.NONE, AuthType.READ_ONLY]:

    @router.post("/api/token", response_model=Token)
    def token(data: Login):
        try:
            return auth.login(data)
        except ValueError:
            raise HTTPException(status_code=401, detail=api_messages.login_failed)


# endregion


# region Notes
# Get Note
@router.get(
    "/api/notes/{title}",
    dependencies=auth_deps,
    response_model=Note,
)
def get_note(title: str):
    """Get a specific note."""
    try:
        return note_storage.get(title)
    except ValueError:
        raise HTTPException(status_code=400, detail=api_messages.invalid_note_title)
    except FileNotFoundError:
        raise HTTPException(404, api_messages.note_not_found)


if global_config.auth_type != AuthType.READ_ONLY:

    # Create Note
    @router.post(
        "/api/notes",
        dependencies=auth_deps,
        response_model=Note,
    )
    def post_note(note: NoteCreate):
        """Create a new note."""
        try:
            return note_storage.create(note)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileExistsError:
            raise HTTPException(status_code=409, detail=api_messages.note_exists)

    # Update Note
    @router.patch(
        "/api/notes/{title}",
        dependencies=auth_deps,
        response_model=Note,
    )
    def patch_note(title: str, data: NoteUpdate):
        try:
            return note_storage.update(title, data)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileExistsError:
            raise HTTPException(status_code=409, detail=api_messages.note_exists)
        except FileNotFoundError:
            raise HTTPException(404, api_messages.note_not_found)

    # Delete Note
    @router.delete(
        "/api/notes/{title}",
        dependencies=auth_deps,
        response_model=None,
    )
    def delete_note(title: str):
        try:
            note_storage.delete(title)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileNotFoundError:
            raise HTTPException(404, api_messages.note_not_found)


# endregion


# region Search
@router.get(
    "/api/search",
    dependencies=auth_deps,
    response_model=List[SearchResult],
)
def search(
    term: str,
    sort: Literal["score", "title", "lastModified"] = "score",
    order: Literal["asc", "desc"] = "desc",
    limit: int = None,
):
    """Perform a full text search on all notes."""
    if sort == "lastModified":
        sort = "last_modified"
    return note_storage.search(term, sort=sort, order=order, limit=limit)


@router.get(
    "/api/tags",
    dependencies=auth_deps,
    response_model=List[str],
)
def get_tags():
    """Get a list of all indexed tags."""
    return note_storage.get_tags()


# endregion


# region Config
@router.get("/api/config", response_model=GlobalConfigResponseModel)
def get_config():
    """Retrieve server-side config required for the UI."""
    return GlobalConfigResponseModel(
        auth_type=global_config.auth_type,
        quick_access_hide=global_config.quick_access_hide,
        quick_access_title=global_config.quick_access_title,
        quick_access_term=global_config.quick_access_term,
        quick_access_sort=global_config.quick_access_sort,
        quick_access_limit=global_config.quick_access_limit,
        flatnotes_git_enabled=global_config.flatnotes_git_enabled,
        flatnotes_GIT_AUTO_FETCH_INTERVAL=global_config.flatnotes_GIT_AUTO_FETCH_INTERVAL,
        flatnotes_git_webhook_configured=global_config.flatnotes_git_webhook_configured,
        frontend_image_compression_enabled=global_config.frontend_image_compression_enabled,
        frontend_image_compression_quality=global_config.frontend_image_compression_quality,
        frontend_image_max_width=global_config.frontend_image_max_width,
    )


# endregion


# region Attachments
# Get Attachment
@router.get(
    "/api/attachments/{filename}",
    dependencies=auth_deps,
)
# Include a secondary route used to create relative URLs that can be used
# outside the context of flatnotes (e.g. "/attachments/image.jpg").
@router.get(
    "/attachments/{filename}",
    dependencies=auth_deps,
    include_in_schema=False,
)
def get_attachment(filename: str):
    """Download an attachment."""
    try:
        return attachment_storage.get(filename)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=api_messages.invalid_attachment_filename,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=api_messages.attachment_not_found)


if global_config.auth_type != AuthType.READ_ONLY:

    # Create Attachment
    @router.post(
        "/api/attachments",
        dependencies=auth_deps,
        response_model=AttachmentCreateResponse,
    )
    def post_attachment(file: UploadFile):
        """Upload an attachment."""
        try:
            return attachment_storage.create(file)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_attachment_filename,
            )
        except FileExistsError:
            raise HTTPException(409, api_messages.attachment_exists)
        except IOError as e:
            raise HTTPException(status_code=500, detail=str(e))


# endregion


# region Healthcheck
@router.get("/health")
def healthcheck() -> str:
    """A lightweight endpoint that simply returns 'OK' to indicate the server
    is running."""
    return "OK"


# endregion

app.include_router(router, prefix=global_config.path_prefix)
app.mount(
    global_config.path_prefix,
    StaticFiles(directory="client/dist"),
    name="dist",
)
