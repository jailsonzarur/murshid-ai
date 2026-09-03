from io import BytesIO

import pytest

from src.features.files.services.bucket_service import (
    BucketKeyError,
    MinioBucketService,
    get_minio_endpoint_config,
    get_minio_public_endpoint,
)


class FakeMinioNotFoundError(Exception):
    code = "NoSuchKey"


class FakeMinioResponse:
    def __init__(self, content: bytes, content_type: str | None) -> None:
        self._content = BytesIO(content)
        self.headers = {"content-type": content_type} if content_type else {}
        self.closed = False
        self.released = False

    def read(self) -> bytes:
        return self._content.read()

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class FakeMinioClient:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict] = {}

    def put_object(self, bucket_name: str, object_name: str, *, data, length: int, content_type: str | None = None):
        self.objects[(bucket_name, object_name)] = {
            "Body": data.read(length),
            "ContentType": content_type,
        }

    def fget_object(self, bucket_name: str, object_name: str, file_path: str):
        if (bucket_name, object_name) not in self.objects:
            raise FakeMinioNotFoundError()

        with open(file_path, "wb") as destination:
            destination.write(self.objects[(bucket_name, object_name)]["Body"])

    def get_object(self, bucket_name: str, object_name: str):
        if (bucket_name, object_name) not in self.objects:
            raise FakeMinioNotFoundError()

        stored = self.objects[(bucket_name, object_name)]
        return FakeMinioResponse(stored["Body"], stored["ContentType"])


def test_upload_and_get_object():
    client = FakeMinioClient()
    service = MinioBucketService(
        client=client,
        bucket_name="iasmim",
        public_base_url="https://cdn.example.com/iasmim",
    )

    uploaded = service.upload(
        b"exam file",
        "exam.pdf",
        folder="exams",
        content_type="application/pdf",
        key="exams/exam.pdf",
    )
    stored = service.get(uploaded.key)

    assert uploaded.key == "exams/exam.pdf"
    assert uploaded.file_url == "https://cdn.example.com/iasmim/exams/exam.pdf"
    assert uploaded.size == 9
    assert stored.content == b"exam file"
    assert stored.content_type == "application/pdf"


def test_upload_stream_sends_the_file_without_loading_it():
    client = FakeMinioClient()
    service = MinioBucketService(client=client, bucket_name="iasmim")

    uploaded = service.upload_stream(
        BytesIO(b"audio bytes"),
        "aula.mp3",
        length=11,
        folder="lectures",
        content_type="audio/mpeg",
    )

    assert uploaded.size == 11
    assert uploaded.content_type == "audio/mpeg"
    assert service.get(uploaded.key).content == b"audio bytes"


def test_download_to_writes_straight_to_disk(tmp_path):
    client = FakeMinioClient()
    service = MinioBucketService(client=client, bucket_name="iasmim")
    uploaded = service.upload(b"audio bytes", "aula.mp3", folder="lectures")

    destination = tmp_path / "aula.mp3"
    service.download_to(uploaded.key, destination)

    assert destination.read_bytes() == b"audio bytes"


@pytest.mark.parametrize("key", ["../secret.txt", "exams/../../secret.txt", ""])
def test_rejects_invalid_keys(key: str):
    service = MinioBucketService(client=FakeMinioClient(), bucket_name="iasmim")

    with pytest.raises(BucketKeyError):
        service.get(key)


def test_get_raises_404_when_object_does_not_exist():
    service = MinioBucketService(client=FakeMinioClient(), bucket_name="iasmim")

    with pytest.raises(Exception) as error:
        service.get("missing.pdf")

    assert getattr(error.value, "status_code") == 404


def test_reads_railway_minio_public_endpoint(monkeypatch):
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT", "https://bucket.example.com:443")

    assert get_minio_public_endpoint() == "https://bucket.example.com:443"


def test_builds_endpoint_from_railway_host_and_port(monkeypatch):
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT", "")
    monkeypatch.setenv("MINIO_PUBLIC_HOST", "bucket.example.com")
    monkeypatch.setenv("MINIO_PUBLIC_PORT", "443")

    assert get_minio_public_endpoint() == "https://bucket.example.com:443"


def test_parses_minio_client_endpoint_config(monkeypatch):
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT", "https://bucket.example.com:443")

    endpoint_config = get_minio_endpoint_config()

    assert endpoint_config.endpoint == "bucket.example.com:443"
    assert endpoint_config.public_url == "https://bucket.example.com:443"
    assert endpoint_config.secure is True
