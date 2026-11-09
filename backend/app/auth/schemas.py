from pydantic import BaseModel, Field, SecretStr


class LoginRequest(BaseModel):
    username: str = Field(max_length=191)
    password: SecretStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
