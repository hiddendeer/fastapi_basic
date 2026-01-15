import uuid
from sqlmodel import SQLModel, Field

class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(SQLModel):
    sub: uuid.UUID | None = None

class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

class Message(SQLModel):
    message: str
