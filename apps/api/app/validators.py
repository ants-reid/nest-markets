"""Input validation utilities for security."""

from pydantic import BaseModel
import re


class SecureStringField(str):
    """String that rejects common SQL/XSS injection patterns."""
    
    # Pattern to detect obvious SQL keywords in suspicious contexts
    SQL_PATTERN = re.compile(
        r"(?i)(DROP|DELETE|INSERT|UPDATE|UNION|EXEC|SCRIPT|JAVASCRIPT|ONCLICK|ONERROR)"
    )
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("Must be string")
        if len(v) > 500:
            raise ValueError("String too long (max 500 chars)")
        # Basic check for obvious injection attempts
        if cls.SQL_PATTERN.search(v) and ("--" in v or ";" in v):
            raise ValueError("Input contains suspicious SQL-like patterns")
        return v


class ValidatedInput(BaseModel):
    """Base model with validation enabled."""
    
    class Config:
        validate_assignment = True
        str_strip_whitespace = True
