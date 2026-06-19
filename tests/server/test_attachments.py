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
    os.environ["FLATNOTES_PATH"] = str(tmp_path)
    service = FileSystemAttachments()
    yield service
    del os.environ["FLATNOTES_PATH"]


@pytest.fixture
def s3_attachments_service():
    """Provides an instance of S3Attachments with a mocked S3 environment."""
    with mock_aws():
        s3_client = boto3.client("s3", region_name="us-east-1")
        bucket_name = "test-bucket"
        s3_client.create_bucket(Bucket=bucket_name)

        # Mock the GlobalConfig object that S3Attachments expects
        mock_config = MagicMock()
        mock_config.s3_bucket_name = bucket_name
        mock_config.s3_access_key_id = "testing"
        mock_config.s3_secret_access_key = "testing"
        mock_config.s3_region = "us-east-1"
        mock_config.s3_endpoint_url = None
        mock_config.s3_path_prefix = "test-prefix"
        mock_config.s3_public_url = f"https://{bucket_name}.s3.amazonaws.com"

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
            expected_path = os.path.join(service.storage_path, result.filename)
            assert os.path.exists(expected_path)
            assert result.url == f"attachments/{result.filename}"
        elif isinstance(service, S3Attachments):
            assert result.url.startswith(service.public_url)
            assert result.url.endswith(result.filename)
            assert service.path_prefix in result.url

            # Check if the object exists in the mock bucket
            object_key = service._get_object_key(result.filename)
            response = service.s3_client.get_object(
                Bucket=service.bucket_name, Key=object_key
            )
            assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
            assert response["Body"].read() == b"some image data"

    def test_get_attachment(self, attachment_service_fixture, request):
        """
        Tests retrieval of an attachment.
        - For filesystem, it should succeed.
        - For S3, it should raise FileNotFoundError as it's not supported.
        """
        service = request.getfixturevalue(attachment_service_fixture)

        if isinstance(service, S3Attachments):
            with pytest.raises(FileNotFoundError):
                service.get("any-s3-filename.txt")
            return

        mock_file = MockUploadFile(
            filename="retrieval_test.jpg",
            content=b"jpeg data",
            content_type="image/jpeg",
        )
        create_result = service.create(mock_file)

        # Action
        get_response = service.get(create_result.filename)

        # Assertions for filesystem
        assert get_response is not None
        assert hasattr(get_response, "path")
        assert os.path.basename(get_response.path) == create_result.filename

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

        with pytest.raises(ValueError):
            service.create(mock_file)


def test_s3_create_does_not_send_object_acl(s3_attachments_service):
    """R2-compatible uploads must not rely on unsupported x-amz-acl headers."""
    service = s3_attachments_service
    mock_file = MockUploadFile(
        filename="r2-compatible.png",
        content=b"image bytes",
        content_type="image/png",
    )

    service.s3_client.upload_fileobj = MagicMock()

    service.create(mock_file)

    extra_args = service.s3_client.upload_fileobj.call_args.kwargs["ExtraArgs"]
    assert extra_args == {"ContentType": "image/png"}
