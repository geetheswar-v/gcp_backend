from pydantic import BaseModel, EmailStr
from fastapi.security import OAuth2PasswordRequestForm as FastAPIForm
from datetime import datetime
import enum

# Define an Enum for user roles to match the database model
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"

# --- User Schemas ---

class UserBase(BaseModel):
    """Base schema for a user, containing common attributes."""
    email: EmailStr
    full_name: str | None = None

class UserCreate(UserBase):
    """Schema used for creating a new user. Inherits from UserBase and adds a password."""
    full_name: str
    password: str

class User(UserBase):
    """
    Schema used for returning user data from the API.
    It includes the ID, active status, and role, but crucially,
    it does NOT include the password, ensuring hashed passwords are never exposed.
    """
    id: int
    is_active: bool
    role: UserRole

    class Config:
        # This setting allows Pydantic to read data directly from ORM models.
        from_attributes = True

# --- Token Schemas ---

class Token(BaseModel):
    """Schema for the response when a user successfully logs in."""
    access_token: str
    token_type: str
    user_name: str | None = None

class TokenData(BaseModel):
    """Schema for the data contained within a JWT token."""
    email: str | None = None
    user_id: int | None = None
    role: str | None = None
    name: str | None = None

# --- Exam Submission Schemas ---

class GeneratedExamResponse(BaseModel):
    """Response for a generated exam that hasn't been attempted yet."""
    id: int
    exam_type: str
    exam_name: str
    stream: str | None
    year: int | None
    generated_at: datetime
    exam_data: dict
    is_attempted: bool

    class Config:
        from_attributes = True

class ExamSubmissionRequest(BaseModel):
    generated_exam_id: int | None = None
    exam_type: str
    exam_name: str
    stream: str | None = None
    year: int | None = None
    score: int | None = None
    total_questions: int
    correct_answers: int
    wrong_answers: int
    unanswered: int
    percentage: float | None = None
    time_taken: int | None = None
    exam_data: dict

class ExamAttemptResponse(BaseModel):
    id: int
    exam_type: str
    exam_name: str
    stream: str | None
    year: int | None
    score: int | None
    total_questions: int
    correct_answers: int
    wrong_answers: int
    unanswered: int
    percentage: int | None
    time_taken: int | None
    submitted_at: datetime | None
    exam_data: dict

    class Config:
        from_attributes = True

# --- Exam Generation Schemas ---
class ExamGenerationRequest(BaseModel):
    """
    Schema for the request to generate a new exam, allowing for customization.
    Supports both CAT and GATE exams.
    For GATE exams, stream is required and must be one of the 30 valid streams.
    """
    exam_type: str  # CAT or GATE (the type of exam)
    exam_name: str  # Custom name like "cs_exam_2024" or "my_cat_practice"
    stream: str | None = None  # Required for GATE exams (CS, EE, ME, etc.)
    year: int | None = None
    
    class Config:
        schema_extra = {
            "example": {
                "exam_name": "GATE",
                "stream": "CS",
                "year": 2024
            }
        }


# --- OAuth2 Password Request Form ---
class OAuth2PasswordRequestForm(FastAPIForm):
    pass

