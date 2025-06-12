# attachments/s3.py

import io
from typing import TYPE_CHECKING
from uuid import uuid4

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import UploadFile
from fastapi.responses import RedirectResponse

# Use TYPE_CHECKING to avoid circular import at runtime
if TYPE_CHECKING:
    from global_config import GlobalConfig

from helpers import is_valid_filename
from logger import logger

from .base import BaseAttachments
from .models import AttachmentCreateResponse


class S3Attachments(BaseAttachments):
    def __init__(self, config: "GlobalConfig"):
        self.bucket_name = config.s3_bucket_name
        self.path_prefix = config.s3_path_prefix.strip("/")
        self.public_url_base = (
            config.s3_public_url_base.rstrip("/") if config.s3_public_url_base else None
        )
        self.presigned_url_expiration = config.s3_presigned_url_expiration

        if not all(
            [
                config.s3_access_key_id,
                config.s3_secret_access_key,
                self.bucket_name,
                config.s3_region,
            ]
        ):
            raise ValueError(
                "S3 provider is selected, but one or more required S3 environment variables are missing (e.g. key, secret, bucket, region)."
            )

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
        except NoCredentialsError as e:
            raise ValueError(f"S3 credentials not available: {e}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            raise ValueError(f"S3 client error ({error_code}): {e}")

    def _get_object_key(self, filename: str) -> str:
        """Constructs the full S3 object key."""
        return f"{self.path_prefix}/{filename}" if self.path_prefix else filename

    def create(self, file: UploadFile) -> AttachmentCreateResponse:
        is_valid_filename(file.filename)

        # Generate a unique key to prevent overwrites
        unique_filename = f"{uuid4().hex}-{file.filename}"
        object_key = self._get_object_key(unique_filename)

        try:
            # Use file.read() which is async-compatible, instead of file.file
            file_content = file.file.read()
            self.s3_client.upload_fileobj(
                io.BytesIO(file_content),
                self.bucket_name,
                object_key,
                ExtraArgs={"ContentType": file.content_type},
            )
            logger.info(
                f"Successfully uploaded '{file.filename}' to S3 bucket '{self.bucket_name}' as '{object_key}'"
            )
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            # Do not use FileExistsError. This is an I/O failure.
            raise IOError(f"Failed to upload file to S3 storage: {e}")

        # Construct the URL based on whether a public base URL is provided
        if self.public_url_base:
            url = f"{self.public_url_base}/{object_key}"
        else:
            # Fallback to the endpoint URL if no public base is set
            endpoint_url = self.s3_client.meta.endpoint_url
            url = f"{endpoint_url}/{self.bucket_name}/{object_key}"

        return AttachmentCreateResponse(filename=unique_filename, url=url)

    def get(self, filename: str):
        is_valid_filename(filename)
        object_key = self._get_object_key(filename)

        # If a public URL base is defined, we assume files are publicly accessible and redirect directly.
        if self.public_url_base:
            return RedirectResponse(url=f"{self.public_url_base}/{object_key}")

        # Otherwise, generate a secure presigned URL for temporary access.
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=self.presigned_url_expiration,
            )
            return RedirectResponse(url=url)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(
                    "The specified attachment cannot be found in S3."
                )
            else:
                logger.error(f"Error generating presigned URL from S3: {e}")
                raise IOError(f"Could not retrieve file from S3: {e}")
