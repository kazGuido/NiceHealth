from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from ..storage import get_file
import mimetypes

router = APIRouter(prefix="/files", tags=["files"])

@router.get("/{file_name}")
async def serve_file(file_name: str):
    """Serve a file from MinIO through the backend"""
    file_obj = get_file(file_name)
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Try to guess the media type
    content_type, _ = mimetypes.guess_type(file_name)
    if not content_type:
        content_type = "application/octet-stream"
    
    return StreamingResponse(
        file_obj,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=31536000"}
    )

