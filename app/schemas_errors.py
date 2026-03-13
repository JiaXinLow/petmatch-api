from pydantic import BaseModel
from typing import Optional, Any

class ErrorResponse(BaseModel):
    detail: Any