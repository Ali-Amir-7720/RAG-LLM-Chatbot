from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=256)
    profile_picture: str | None = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("username is required")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("email must contain @")
        return value


class UserRead(BaseModel):
    id: UUID
    username: str
    email: str
    profile_picture: str | None
    created_at: datetime
    updated_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthSignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("username is required")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("email must contain @")
        return value


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)
    device: str | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("email must contain @")
        return value


class AuthRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=4096)


class AuthLogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=4096)


class AuthResponse(BaseModel):
    user: UserRead
    tokens: TokenPair


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("email must contain @")
        return value


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=256)



class ConversationCreateRequest(BaseModel):
    model_name: str = Field(min_length=1, max_length=100)
    title: str | None = Field(default=None, max_length=255)
    system_prompt: str | None = None
    generation_config: dict = Field(default_factory=dict)


class ConversationRead(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    model_name: str
    system_prompt: str | None
    generation_config: dict
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)
    parent_message_id: UUID | None = None


class MessageRead(BaseModel):
    id: UUID
    conversation_id: UUID
    parent_message_id: UUID | None
    role: str
    content: str
    model_name: str | None
    token_count: int | None
    generation_time: float | None
    is_helpful: bool | None
    feedback_text: str | None
    created_at: datetime


class SearchResult(BaseModel):
    message_id: UUID
    conversation_id: UUID
    snippet: str
    rank: float


class MessageRegenerateRequest(BaseModel):
    content: str | None = None


class MessageFeedbackRequest(BaseModel):
    is_helpful: bool
    feedback_text: str | None = None


class DocumentRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    storage_path: str
    content_hash: str
    mime_type: str
    file_size: int
    status: str
    uploaded_at: datetime



