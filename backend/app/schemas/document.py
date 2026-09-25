from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_type: str
    original_filename: str
    mime_type: str
    file_size: int
    sha256_hash: str
    scan_status: str
    is_private: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime