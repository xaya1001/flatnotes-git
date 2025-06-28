# server/git_integration/test/test_attachments.py
import io
import os
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from attachments.file_system.file_system import FileSystemAttachments
from attachments.s3 import S3Attachments

# --- Test Data and Mocks ---


# A simple mock that mimics FastAPI's UploadFile
class MockUploadFile:
    def __init__(self, filename: str, content: bytes, content_type: str):
        self.filename = filename
        self.file = io.BytesIO(content)
        self.content_type = content_type


# --- Fixtures for Each Backend ---


@pytest.fixture
def filesystem_attachments_service(tmp_path):
    """Provides an instance of FileSystemAttachments using a temporary directory."""
    # Temporarily set the FLATNOTES_PATH env var for the service
    os.environ["FLATNOTES_PATH"] = str(tmp_path)
    service = FileSystemAttachments()
    # Clean up the env var after the test
    yield service
    del os.environ["FLATNOTES_PATH"]


@pytest.fixture
def s3_attachments_service():
    """Provides an instance of S3Attachments with a mocked S3 environment."""
    # Use moto to mock AWS services in this context
    with mock_aws():
        # 1. Setup Mock S3 Environment
        s3_client = boto3.client("s3", region_name="us-east-1")
        bucket_name = "test-bucket"
        s3_client.create_bucket(Bucket=bucket_name)

        # 2. Mock the GlobalConfig object that S3Attachments expects
        mock_config = MagicMock()
        mock_config.s3_bucket_name = bucket_name
        mock_config.s3_access_key_id = "testing"
        mock_config.s3_secret_access_key = "testing"
        mock_config.s3_region = "us-east-1"
        mock_config.s3_endpoint_url = None
        mock_config.s3_path_prefix = "test-prefix"
        mock_config.s3_public_url_base = None  # Test presigned URLs first
        mock_config.s3_presigned_url_expiration = 3600

        # 3. Create and yield the service instance
        service = S3Attachments(mock_config)
        yield service


# --- Test Class Using Parametrization ---


@pytest.mark.parametrize(
    "attachment_service_fixture",
    [
        "filesystem_attachments_service",
        "s3_attachments_service",
    ],
)
class TestAttachmentBackends:
    def test_create_attachment(self, attachment_service_fixture, request):
        """Tests successful creation of an attachment."""
        # Get the correct service instance from the fixture name
        service = request.getfixturevalue(attachment_service_fixture)

        mock_file = MockUploadFile(
            filename="test_image.png",
            content=b"some image data",
            content_type="image/png",
        )

        # Action
        result = service.create(mock_file)

        # Assertions
        assert result.filename is not None
        assert result.url is not None
        assert "test_image.png" in result.filename

        # Specific backend checks
        if isinstance(service, FileSystemAttachments):
            # For filesystem, check if the file exists on disk
            expected_path = os.path.join(service.storage_path, result.filename)
            assert os.path.exists(expected_path)
            assert result.url == f"attachments/{result.filename}"
        elif isinstance(service, S3Attachments):
            # For S3, check if the object exists in the mock bucket
            object_key = service._get_object_key(result.filename)
            response = service.s3_client.get_object(
                Bucket=service.bucket_name, Key=object_key
            )
            assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
            assert response["Body"].read() == b"some image data"
            assert "test_image.png" in object_key

    def test_get_attachment(self, attachment_service_fixture, request):
        """Tests successful retrieval of an attachment."""
        service = request.getfixturevalue(attachment_service_fixture)

        mock_file = MockUploadFile(
            filename="retrieval_test.jpg",
            content=b"jpeg data",
            content_type="image/jpeg",
        )
        create_result = service.create(mock_file)

        # Action
        get_response = service.get(create_result.filename)

        # Assertions
        assert get_response is not None

        # Specific backend checks
        if isinstance(service, FileSystemAttachments):
            assert hasattr(get_response, "path")
            assert os.path.basename(get_response.path) == create_result.filename
        elif isinstance(service, S3Attachments):
            assert hasattr(get_response, "headers")
            assert "location" in get_response.headers
            # Check that it's a valid URL containing the object key
            object_key = service._get_object_key(create_result.filename)
            assert object_key in get_response.headers["location"]

    def test_get_nonexistent_attachment_raises_error(
        self, attachment_service_fixture, request
    ):
        """Tests that getting a non-existent file raises FileNotFoundError."""
        service = request.getfixturevalue(attachment_service_fixture)

        with pytest.raises(FileNotFoundError):
            service.get("nonexistent-file-123.txt")

    def test_create_with_invalid_filename_raises_error(
        self, attachment_service_fixture, request
    ):
        """Tests that filenames with invalid characters are rejected."""
        service = request.getfixturevalue(attachment_service_fixture)

        mock_file = MockUploadFile(
            filename="invalid/path.txt", content=b"test", content_type="text/plain"
        )

        # Simply check for ValueError, don't match the specific message.
        # This makes the test less brittle.
        with pytest.raises(ValueError):
            service.create(mock_file)
