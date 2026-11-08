"""Storage abstraction.

The rest of the app only calls upload/download/delete on a storage service, so
a local filesystem implementation can be swapped for S3/R2/GCS later without
touching business logic.
"""

import os

from flask import current_app


class StorageService:
    def upload(self, storage_key, file_storage):
        """Persist the uploaded file. Returns (stored_key, size_in_bytes)."""
        raise NotImplementedError

    def download(self, storage_key):
        """Return an absolute filesystem path for the given key."""
        raise NotImplementedError

    def delete(self, storage_key):
        raise NotImplementedError


class LocalStorageService(StorageService):
    """Stores files under instance/uploads/resumes/<key>."""

    def _path_for(self, storage_key):
        root = current_app.config["UPLOAD_FOLDER"]
        # Guard against path traversal in storage keys
        safe_key = os.path.normpath(storage_key).replace("..", "")
        return os.path.join(root, safe_key)

    def upload(self, storage_key, file_storage):
        path = self._path_for(storage_key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        file_storage.save(path)
        return storage_key, os.path.getsize(path)

    def download(self, storage_key):
        path = self._path_for(storage_key)
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        return path

    def delete(self, storage_key):
        try:
            os.remove(self._path_for(storage_key))
        except FileNotFoundError:
            pass


class S3StorageService(StorageService):
    """Stores files in a private S3-compatible bucket.

    Reads the standard AWS_* variables from the environment — endpoint, region,
    key and secret — so nothing else has to be configured. The bucket is
    addressed path-style, which is what a dotted bucket name requires.

    `download` returns a BytesIO rather than a path: the bucket is remote, so
    there is no file on disk to hand to send_file.
    """

    def __init__(self):
        import boto3
        from botocore.config import Config as BotoConfig

        self.bucket = (
            os.environ.get("BUCKET_NAME")
            or os.environ.get("S3_BUCKET")
            or os.environ.get("AWS_S3_BUCKET")
        )
        if not self.bucket:
            raise RuntimeError("STORAGE_MODE=s3 but no bucket name (BUCKET_NAME) is set.")
        self.client = boto3.client(
            "s3",
            endpoint_url=os.environ.get("AWS_ENDPOINT_URL_S3") or os.environ.get("S3_ENDPOINT"),
            region_name=os.environ.get("AWS_REGION") or os.environ.get("S3_REGION"),
            config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def upload(self, storage_key, file_storage):
        body = file_storage.read()
        file_storage.seek(0)
        self.client.put_object(Bucket=self.bucket, Key=storage_key, Body=body)
        return storage_key, len(body)

    def download(self, storage_key):
        import io

        from botocore.exceptions import ClientError

        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=storage_key)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise FileNotFoundError(storage_key) from exc
            raise
        return io.BytesIO(obj["Body"].read())

    def delete(self, storage_key):
        self.client.delete_object(Bucket=self.bucket, Key=storage_key)


def get_storage_service():
    mode = current_app.config["STORAGE_MODE"]
    if mode == "local":
        return LocalStorageService()
    if mode == "s3":
        return S3StorageService()
    raise RuntimeError(f"Unknown STORAGE_MODE: {mode}")
