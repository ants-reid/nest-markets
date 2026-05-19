"""API key authentication middleware."""

from fastapi import HTTPException, Request, status
from app.config import get_settings


class APIKeyAuth:
    """Simple bearer token authentication using environment variable."""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.api_key
        self.enabled = bool(self.api_key)
    
    async def __call__(self, request: Request) -> str:
        """Validate API key from Authorization header.
        
        Raises HTTPException(401) if invalid or missing when enabled.
        Returns the API key for logging/audit purposes.
        """
        if not self.enabled:
            # Auth disabled in development (APP_ENV=development)
            return "development-mode"
        
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Expected 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = parts[1]
        if token != self.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return token


# Global instance for dependency injection
api_key_auth = APIKeyAuth()
