# server/attachments/s3.py

import os
import uuid
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
from fastapi.responses import FileResponse

from server.logger import logger
from server.global_config import GlobalConfig

from .base import BaseAttachments
from .models import AttachmentCreateResponse


class S3Attachments(BaseAttachments):
    """
    Manages attachments by uploading them to an S3-compatible storage service.
    """

    def __init__(self):
        config = GlobalConfig()
        self.bucket_name = config.s3_bucket_name
        self.endpoint_url = config.s3_endpoint_url
        self.region = config.s3_region
        self.access_key = config.s3_access_key_id
        self.secret_key = config.s3_secret_access_key
        self.path_prefix = (
            config.s3_path_prefix.strip("/") + "/" if config.s3_path_prefix else ""
        )
        self.public_url_base = (
            config.s3_public_url_base.strip("/") if config.s3_public_url_base else None
        )

        # Basic configuration validation
        if not all([self.access_key, self.secret_key, self.bucket_name]):
            raise ValueError(
                "S3 provider is missing required configuration (ACCESS_KEY, SECRET_KEY, BUCKET_NAME)."
            )

        logger.info(f"Initializing S3Attachments for bucket '{self.bucket_name}'")
        try:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise

    def create(self, file: UploadFile) -> AttachmentCreateResponse:
        """Uploads a file to S3 and returns its public URL."""
        # Sanitize filename for safety, although UUID makes it less critical
        safe_filename = os.path.basename(file.filename)
        # Generate a unique key to prevent any possible overwrites
        s3_key = f"{self.path_prefix}{uuid.uuid4()}-{safe_filename}"

        logger.info(f"Uploading '{safe_filename}' to S3 with key '{s3_key}'")

        try:
            self.s3_client.upload_fileobj(
                file.file,
                self.bucket_name,
                s3_key,
                ExtraArgs={"ContentType": file.content_type},
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            logger.error(f"S3 Upload Failed. Code: {error_code}. Details: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"S3 Upload Failed: {error_code or 'Unknown error'}",
            )
        except Exception as e:
            logger.error(f"An unexpected error occurred during S3 upload: {e}")
            raise HTTPException(
                status_code=500, detail="An unexpected error occurred during upload."
            )

        public_url = self._get_public_url(s3_key)
        logger.info(f"Upload successful. Public URL: {public_url}")

        return AttachmentCreateResponse(filename=safe_filename, url=public_url)

    def get(self, filename: str) -> FileResponse:
        """Direct download from server is not supported for S3. Files are accessed via public URL."""
        logger.warning(
            f"Attempted to call get() on S3 attachment '{filename}'. This is not supported."
        )
        raise NotImplementedError(
            "Direct download for S3 attachments is not supported. Use the public URL provided on creation."
        )

    def _get_public_url(self, key: str) -> str:
        """Constructs the public URL for a given S3 key."""
        # Custom domain/R2 public URL base has highest priority
        if self.public_url_base:
            return f"{self.public_url_base}/{key}"

        # URL for S3-compatible services with a custom endpoint (like R2, MinIO)
        if self.endpoint_url:
            # Assumes virtual-hosted-style is not the default for custom endpoints,
            # builds path-style URL which is common for R2 public access.
            return f"{self.endpoint_url}/{self.bucket_name}/{key}"

        # Standard AWS S3 virtual-hosted-style URL
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
