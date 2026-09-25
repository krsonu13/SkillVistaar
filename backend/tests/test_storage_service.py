import pytest
import tempfile
from pathlib import Path

from app.services.storage_service import (
    LocalStorageService,
    StorageError,
    get_storage_service,
)


@pytest.mark.asyncio
async def test_local_storage_lifecycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = LocalStorageService(root_dir=tmp_dir)
        assert storage.is_cloud is False

        key = "test_docs/user1/sample.txt"
        content = b"SkillVistaar Document Content"

        # 1. Store
        stored_path = await storage.store_file(key, content, mime_type="text/plain")
        assert Path(stored_path).exists()
        assert Path(stored_path).read_bytes() == content

        # 2. Read
        read_bytes = await storage.read_file(key)
        assert read_bytes == content

        # 3. Download URL (None for local)
        url = await storage.get_download_url(key)
        assert url is None

        # 4. Delete
        deleted = await storage.delete_file(key)
        assert deleted is True
        assert not Path(stored_path).exists()


@pytest.mark.asyncio
async def test_local_storage_path_traversal_prevention():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = LocalStorageService(root_dir=tmp_dir)
        with pytest.raises(StorageError, match="Path traversal detected"):
            await storage.store_file("../../escape.txt", b"malicious")


@pytest.mark.asyncio
async def test_get_storage_service_default():
    storage = get_storage_service()
    assert storage is not None
