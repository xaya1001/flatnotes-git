from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Literal, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import APIRouter, Depends, FastAPI, HTTPException, UploadFile
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

# --- Scoped Git Imports and Setup ---
git_integration_router = None
if global_config.flatnotes_git_enabled:
    try:
        from git_integration import config as git_config
        from git_integration.log_handler import LogLevel, add_git_log
        from git_integration.router import (
            broadcast_updates,
            get_git_manager,
            router as git_integration_router,
        )
        from git_integration.git_manager import GitManager
    except ImportError as e:
        logger.error(f"FLATNOTES_GIT_ENABLED is true, but a module failed to load: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    logger.info("Application startup...")

    if git_integration_router:
        try:
            manager = get_git_manager()

            if global_config.flatnotes_git_auto_pull_on_start:
                logger.info("Performing auto-pull on startup...")
                add_git_log(LogLevel.INFO, "Auto-pull on startup: Initiated.")
                try:
                    stdout = manager.pull_remote_changes(rebase=True)
                    logger.info(f"Auto-pull successful. Stdout: {stdout}")
                    add_git_log(
                        LogLevel.SUCCESS,
                        "Auto-pull on startup: Successful.",
                        details=stdout,
                    )
                except Exception as e:
                    logger.error(f"Auto-pull on startup failed: {e}", exc_info=True)
                    add_git_log(
                        LogLevel.ERROR, "Auto-pull on startup: Failed.", details=str(e)
                    )

            if global_config.flatnotes_git_auto_sync_interval > 0:
                logger.info(
                    f"Initializing scheduled auto-sync for every {global_config.flatnotes_git_auto_sync_interval} minutes."
                )
                scheduler = BackgroundScheduler(daemon=True)

                def scheduled_sync_job():
                    if git_config.is_auto_sync_paused():
                        return
                    logger.info("Executing scheduled git sync...")
                    add_git_log(LogLevel.INFO, "Scheduled auto-sync: Task started.")
                    try:
                        sync_manager = get_git_manager()
                        commit_message = f"chore: automatic sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        sync_manager.sync_workspace(commit_message)
                        add_git_log(
                            LogLevel.SUCCESS, "Scheduled auto-sync: Successful."
                        )
                    except Exception as e:
                        logger.error(f"Scheduled git sync failed: {e}", exc_info=True)
                        add_git_log(
                            LogLevel.ERROR,
                            "Scheduled auto-sync: Failed.",
                            details=str(e),
                        )

                scheduler.add_job(
                    scheduled_sync_job,
                    "interval",
                    minutes=global_config.flatnotes_git_auto_sync_interval,
                )
                scheduler.start()
                app.state.scheduler = scheduler
                logger.info("Scheduler for auto-sync started.")

        except Exception as e:
            logger.error(
                f"Failed to initialize GitManager during application startup: {e}"
            )

    yield

    # --- Shutdown logic ---
    logger.info("Application shutdown...")
    if hasattr(app.state, "scheduler"):
        logger.info("Shutting down scheduler.")
        app.state.scheduler.shutdown()


app = FastAPI(
    docs_url=global_config.path_prefix + "/docs",
    openapi_url=global_config.path_prefix + "/openapi.json",
    lifespan=lifespan,
)

router = APIRouter()


app.include_router(router, prefix=global_config.path_prefix)

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
            raise HTTPException(
                status_code=401, detail=api_messages.login_failed
            )


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
        raise HTTPException(
            status_code=400, detail=api_messages.invalid_note_title
        )
    except FileNotFoundError:
        raise HTTPException(404, api_messages.note_not_found)


if global_config.auth_type != AuthType.READ_ONLY:

    # Create Note
    @router.post(
        "/api/notes",
        dependencies=auth_deps,
        response_model=Note,
    )
    async def post_note(
        note: NoteCreate,
        manager: Optional[GitManager] = (
            Depends(get_git_manager) if global_config.flatnotes_git_enabled else None
        ),
    ):
        """Create a new note."""
        try:
            new_note = note_storage.create(note)
            if global_config.flatnotes_git_enabled:
                await broadcast_updates(manager)
            return new_note
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileExistsError:
            raise HTTPException(
                status_code=409, detail=api_messages.note_exists
            )

    # Update Note
    @router.patch(
        "/api/notes/{title}",
        dependencies=auth_deps,
        response_model=Note,
    )
    async def patch_note(
        title: str,
        data: NoteUpdate,
        manager: Optional[GitManager] = (
            Depends(get_git_manager) if global_config.flatnotes_git_enabled else None
        ),
    ):
        try:
            updated_note = note_storage.update(title, data)
            if global_config.flatnotes_git_enabled:
                await broadcast_updates(manager)
            return updated_note
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileExistsError:
            raise HTTPException(
                status_code=409, detail=api_messages.note_exists
            )
        except FileNotFoundError:
            raise HTTPException(404, api_messages.note_not_found)

    # Delete Note
    @router.delete(
        "/api/notes/{title}",
        dependencies=auth_deps,
        response_model=None,
    )
    async def delete_note(
        title: str,
        manager: Optional[GitManager] = (
            Depends(get_git_manager) if global_config.flatnotes_git_enabled else None
        ),
    ):
        try:
            note_storage.delete(title)
            if global_config.flatnotes_git_enabled:
                await broadcast_updates(manager)
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
        flatnotes_git_auto_sync_interval=global_config.flatnotes_git_auto_sync_interval,
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
        raise HTTPException(
            status_code=404, detail=api_messages.attachment_not_found
        )


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
