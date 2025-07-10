import sys
from enum import Enum
from typing import Optional

from helpers import CustomBaseModel, get_env
from logger import logger


class StorageProviderType(str, Enum):
    FILESYSTEM = "filesystem"
    S3 = "s3"


class GlobalConfig:
    def __init__(self) -> None:
        logger.debug("Loading global config...")
        self.auth_type: AuthType = self._load_auth_type()
        self.quick_access_hide: bool = self._quick_access_hide()
        self.quick_access_title: str = self._quick_access_title()
        self.quick_access_term: str = self._quick_access_term()
        self.quick_access_sort: str = self._quick_access_sort()
        self.quick_access_limit: int = self._quick_access_limit()
        self.path_prefix: str = self._load_path_prefix()

        # --- Attachment Configuration ---
        self.attachment_storage_provider: StorageProviderType = (
            self._load_attachment_storage_provider()
        )
        # S3 Config (for public buckets only)
        self.s3_endpoint_url: Optional[str] = get_env(
            "FLATNOTES_S3_ENDPOINT_URL", mandatory=False
        )
        self.s3_access_key_id: Optional[str] = get_env(
            "FLATNOTES_S3_ACCESS_KEY_ID", mandatory=False
        )
        self.s3_secret_access_key: Optional[str] = get_env(
            "FLATNOTES_S3_SECRET_ACCESS_KEY", mandatory=False
        )
        self.s3_bucket_name: Optional[str] = get_env(
            "FLATNOTES_S3_BUCKET_NAME", mandatory=False
        )
        self.s3_region: Optional[str] = get_env("FLATNOTES_S3_REGION", mandatory=False)
        self.s3_path_prefix: str = get_env(
            "FLATNOTES_S3_PATH_PREFIX", mandatory=False, default=""
        )
        self.s3_public_url: Optional[str] = get_env(
            "FLATNOTES_S3_PUBLIC_URL", mandatory=False
        )

        # Frontend Image Processing Config
        self.frontend_image_compression_enabled: bool = get_env(
            "FLATNOTES_FRONTEND_IMAGE_COMPRESSION_ENABLED",
            mandatory=False,
            default=True,
            cast_bool=True,
        )
        self.frontend_image_compression_quality: float = self._load_float_env(
            "FLATNOTES_FRONTEND_IMAGE_COMPRESSION_QUALITY", 0.8, 0.1, 1.0
        )
        self.frontend_image_max_width: int = get_env(
            "FLATNOTES_FRONTEND_IMAGE_MAX_WIDTH",
            mandatory=False,
            default=1920,
            cast_int=True,
        )

    def load_auth(self):
        if self.auth_type in (AuthType.NONE, AuthType.READ_ONLY):
            return None
        elif self.auth_type in (AuthType.PASSWORD, AuthType.TOTP):
            from auth.local import LocalAuth

            return LocalAuth()

    def load_note_storage(self):
        from notes.file_system import FileSystemNotes

        return FileSystemNotes()

    def load_attachment_storage(self):
        """
        Loads the primary attachment storage based on configuration.
        Note: The filesystem storage is always available for fallback and local file serving.
        """
        if (
            self.attachment_storage_provider == StorageProviderType.S3
            and self.is_s3_configured()
        ):
            try:
                from attachments.s3 import S3Attachments

                logger.info("Primary attachment provider: S3 (Public Bucket Mode)")
                return S3Attachments(self)
            except (ValueError, ImportError) as e:
                logger.error(
                    f"Failed to initialize S3 provider: {e}. "
                    "Falling back to filesystem as primary provider."
                )

        logger.info("Primary attachment provider: Filesystem")
        from attachments.file_system import FileSystemAttachments

        return FileSystemAttachments()

    def is_s3_configured(self) -> bool:
        """Check if all necessary S3 variables are set for S3 mode."""
        required_vars = [
            self.s3_access_key_id,
            self.s3_secret_access_key,
            self.s3_bucket_name,
            self.s3_public_url,
        ]
        if not all(required_vars):
            logger.warning(
                "S3 provider is selected, but one or more required environment variables "
                "are missing. Required: FLATNOTES_S3_{ACCESS_KEY_ID, SECRET_ACCESS_KEY, "
                "BUCKET_NAME, PUBLIC_URL}."
            )
            return False

        if not self.s3_endpoint_url and not self.s3_region:
            logger.warning(
                "When S3 provider is used, either FLATNOTES_S3_ENDPOINT_URL or "
                "FLATNOTES_S3_REGION must be set."
            )
            return False

        return True

    def _load_attachment_storage_provider(self) -> StorageProviderType:
        key = "FLATNOTES_ATTACHMENT_STORAGE_PROVIDER"
        value = get_env(key, mandatory=False, default="filesystem").lower()
        try:
            return StorageProviderType(value)
        except ValueError:
            logger.error(
                f"Invalid value '{value}' for {key}. Must be one of: "
                + ", ".join([p.value for p in StorageProviderType])
                + ". Defaulting to filesystem."
            )
            return StorageProviderType.FILESYSTEM

    def _load_auth_type(self):
        key = "FLATNOTES_AUTH_TYPE"
        auth_type = get_env(
            key, mandatory=False, default=AuthType.PASSWORD.value
        )
        try:
            auth_type = AuthType(auth_type.lower())
        except ValueError:
            logger.error(
                f"Invalid value '{auth_type}' for {key}. "
                + "Must be one of: "
                + ", ".join([auth_type.value for auth_type in AuthType])
                + "."
            )
            sys.exit(1)
        return auth_type

    def _quick_access_hide(self):
        key = "FLATNOTES_QUICK_ACCESS_HIDE"
        value = get_env(key, mandatory=False, default=False, cast_bool=True)
        if value is False:
            depricated_key = "FLATNOTES_HIDE_RECENTLY_MODIFIED"
            value = get_env(
                depricated_key, mandatory=False, default=False, cast_bool=True
            )
            if value is True:
                logger.warning(
                    f"{depricated_key} is depricated. Please use {key} instead."
                )
        return value

    def _quick_access_title(self):
        key = "FLATNOTES_QUICK_ACCESS_TITLE"
        return get_env(key, mandatory=False, default="RECENTLY MODIFIED")

    def _quick_access_term(self):
        key = "FLATNOTES_QUICK_ACCESS_TERM"
        return get_env(key, mandatory=False, default="*")

    def _quick_access_sort(self):
        key = "FLATNOTES_QUICK_ACCESS_SORT"
        value = get_env(key, mandatory=False, default="lastModified")
        valid_values = ["score", "title", "lastModified"]
        if value not in valid_values:
            logger.error(
                f"Invalid value '{value}' for {key}. "
                + "Must be one of: "
                + ", ".join(valid_values)
            )
            sys.exit(1)
        return value

    def _quick_access_limit(self):
        key = "FLATNOTES_QUICK_ACCESS_LIMIT"
        return get_env(key, mandatory=False, default=4, cast_int=True)

    def _load_path_prefix(self):
        key = "FLATNOTES_PATH_PREFIX"
        value = get_env(key, mandatory=False, default="")
        if value and (not value.startswith("/") or value.endswith("/")):
            logger.error(
                f"Invalid value '{value}' for {key}. "
                + "Must start with '/' and not end with '/'."
            )
            sys.exit(1)
        return value

    def _load_float_env(
        self, key: str, default: float, min_val: float, max_val: float
    ) -> float:
        value_str = get_env(key, mandatory=False, default=str(default))
        try:
            value = float(value_str)
            if not (min_val <= value <= max_val):
                logger.warning(
                    f"Value for {key} ({value}) is outside the valid range [{min_val}, {max_val}]. Using default value: {default}"
                )
                return default
            return value
        except (ValueError, TypeError):
            logger.warning(f"Invalid value for {key}. Using default value: {default}")
            return default


class AuthType(str, Enum):
    NONE = "none"
    READ_ONLY = "read_only"
    PASSWORD = "password"
    TOTP = "totp"


class GlobalConfigResponseModel(CustomBaseModel):
    auth_type: AuthType
    quick_access_hide: bool
    quick_access_title: str
    quick_access_term: str
    quick_access_sort: str
    quick_access_limit: int
    frontend_image_compression_enabled: bool
    frontend_image_compression_quality: float
    frontend_image_max_width: int
