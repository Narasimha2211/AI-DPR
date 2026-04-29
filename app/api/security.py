# ============================================
# Security Utilities
# Path validation, input sanitization
# ============================================

import re
from pathlib import Path
from fastapi import HTTPException
from config.settings import settings


def validate_file_path(file_path: str) -> Path:
    """
    Validate that a file_path is within the allowed uploads directory.
    Prevents path traversal attacks (e.g., ../../etc/passwd).
    """
    try:
        resolved = Path(file_path).resolve()
        upload_dir = settings.UPLOAD_DIR.resolve()
        
        # Must be within the uploads directory
        if not str(resolved).startswith(str(upload_dir)):
            raise HTTPException(
                status_code=403,
                detail="Access denied: file path outside allowed directory"
            )
        
        if not resolved.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return resolved
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file path")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path injection and special characters.
    Only allows alphanumeric, hyphens, underscores, dots, and spaces.
    """
    if not filename:
        return "unnamed_file"
    
    # Remove any directory separators
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # Remove null bytes and other control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    
    # Only keep safe characters
    name, ext = Path(filename).stem, Path(filename).suffix
    name = re.sub(r'[^a-zA-Z0-9_\-\s\.]', '_', name)
    
    # Ensure extension is valid
    if ext.lower() not in settings.SUPPORTED_FORMATS:
        ext = ""
    
    sanitized = f"{name}{ext}"
    
    # Limit length
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    return sanitized or "unnamed_file"
