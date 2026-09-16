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


def get_storage_service():
    if current_app.config["STORAGE_MODE"] == "local":
        return LocalStorageService()
    raise RuntimeError(f"Unknown STORAGE_MODE: {current_app.config['STORAGE_MODE']}")
