import io
from typing import TYPE_CHECKING
from uuid import uuid4

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import UploadFile, HTTPException

if TYPE_CHECKING:
    from server.global_config import GlobalConfig

from helpers import is_valid_filename
from logger import logger

from .base import BaseAttachments
from .models import AttachmentCreateResponse


class S3Attachments(BaseAttachments):
    def __init__(self, config: "GlobalConfig"):
        self.bucket_name = config.s3_bucket_name
        self.path_prefix = config.s3_path_prefix.strip("/")
        self.public_url = config.s3_public_url.rstrip("/")

        # The existence of necessary config is checked in GlobalConfig,
        # but we do a final check for the client.
        try:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=config.s3_endpoint_url,
                aws_access_key_id=config.s3_access_key_id,
                aws_secret_access_key=config.s3_secret_access_key,
                region_name=config.s3_region,
                config=Config(signature_version="s3v4"),
            )
            # Verify bucket exists and we have access
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except (NoCredentialsError, ClientError) as e:
            # Raise ValueError to be caught by GlobalConfig constructor
            raise ValueError(f"S3 client initialization failed: {e}")

    def _get_object_key(self, filename: str) -> str:
        """Constructs the full S3 object key including the optional path prefix."""
        return f"{self.path_prefix}/{filename}" if self.path_prefix else filename

    def create(self, file: UploadFile) -> AttachmentCreateResponse:
        """Create a new attachment by uploading to a public S3 bucket."""
        is_valid_filename(file.filename)

        # Generate a unique key to prevent overwrites and improve obscurity.
        unique_filename = f"{uuid4().hex}-{file.filename}"
        object_key = self._get_object_key(unique_filename)

        try:
            file_content = file.file.read()
            self.s3_client.upload_fileobj(
                io.BytesIO(file_content),
                self.bucket_name,
                object_key,
                ExtraArgs={"ContentType": file.content_type, "ACL": "public-read"},
            )
            logger.info(
                f"Successfully uploaded '{file.filename}' to S3 bucket '{self.bucket_name}' as '{object_key}'"
            )
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            # Raise IOError to be caught by the post_attachment endpoint for fallback.
            raise IOError(f"Failed to upload file to S3 storage: {e}")

        # Construct the final, publicly accessible URL.
        final_url = f"{self.public_url}/{object_key}"

        return AttachmentCreateResponse(filename=unique_filename, url=final_url)

    def get(self, filename: str):
        """
        This method is required by the base class but should not be called
        in public S3 mode. It acts as a safeguard.
        """
        logger.warning(
            f"Attempted to access S3 object '{filename}' via the server proxy. "
            "This is not supported in public S3 mode."
        )
        raise FileNotFoundError(
            f"'{filename}' is not a local file and cannot be served by the server."
        )
