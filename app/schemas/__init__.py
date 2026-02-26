from typing import List, Optional, Any, Union
from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
import json

# --- User Schemas ---
class UserBase(BaseModel):
    username: str
    role: Optional[str] = "user"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- Persona Schemas ---
class PersonaBase(BaseModel):
    name: str
    title: Optional[str] = None
    bio: Optional[str] = None
    theories: Optional[List[str]] = [] 
    stance: Optional[str] = None
    system_prompt: Optional[str] = None
    is_public: bool = False

class PersonaCreate(PersonaBase):
    pass

class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    theories: Optional[List[str]] = None
    stance: Optional[str] = None
    system_prompt: Optional[str] = None
    is_public: Optional[bool] = None

class PersonaResponse(PersonaBase):
    id: int
    owner_id: int
    created_at: datetime
    theories: Optional[Union[List[str], str]] = []

    model_config = ConfigDict(from_attributes=True)

    @field_validator('theories', mode='before')
    @classmethod
    def parse_theories(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        elif v is None:
            return []
        return v

# --- Forum Schemas ---
class ForumBase(BaseModel):
    topic: str

class ForumCreate(ForumBase):
    participant_ids: List[int]

class ForumResponse(ForumBase):
    id: int
    creator_id: int
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# --- Message Schemas ---
class MessageBase(BaseModel):
    speaker_name: str
    content: str
    turn_count: int = 0

class MessageCreate(MessageBase):
    forum_id: int
    persona_id: Optional[int] = None

class MessageResponse(MessageBase):
    id: int
    forum_id: int
    persona_id: Optional[int]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
