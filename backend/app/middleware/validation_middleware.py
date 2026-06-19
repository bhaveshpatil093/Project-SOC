import re
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import json

class InputSanitizer:
    MAX_STRING_LENGTH = 10000
    MAX_MESSAGE_LENGTH = 2000      # SLM chat messages
    FORBIDDEN_PATTERNS = [
        r"<script.*?>.*?</script>", # XSS
        r"javascript:",
        r"\.\./",                   # Path traversal
        r"__import__",              # Python injection
    ]

    @classmethod
    def sanitize_string(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
            
        value = value.strip()
        if len(value) > cls.MAX_STRING_LENGTH:
            value = value[:cls.MAX_STRING_LENGTH]
            
        for pattern in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise HTTPException(status_code=400, detail="Forbidden input pattern detected.")
                
        return value

    @classmethod
    def sanitize_chat_message(cls, message: str) -> str:
        if not isinstance(message, str):
            return message
            
        # Remove any content between <|system|> tags (prompt injection)
        message = re.sub(r"<\|system\|>.*?</\|system\|>", "", message, flags=re.IGNORECASE | re.DOTALL)
        message = message.replace("<|system|>", "").replace("</|system|>", "")
        
        message = message.strip()
        if len(message) > cls.MAX_MESSAGE_LENGTH:
            message = message[:cls.MAX_MESSAGE_LENGTH]
            
        return cls.sanitize_string(message)

class RequestSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int = 1048576): # 1MB default
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                if int(content_length) > self.max_upload_size:
                    raise HTTPException(status_code=413, detail="Request entity too large. Limit is 1MB.")
            except ValueError:
                pass
        
        response = await call_next(request)
        return response
