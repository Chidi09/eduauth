from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from eduauth.models import UserRole, UserStatus, PyObjectId # Import Enums and PyObjectId from models

class UserModel(BaseModel):
    """
    Represents the structure of a user document in the MongoDB 'users' collection.
    This is the core database model for authentication.
    """
    # The MongoDB document ID. PyObjectId ensures correct handling of ObjectId.
    id: PyObjectId = Field(alias="_id", default_factory=ObjectId)
    email: EmailStr = Field(..., unique=True, index=True) # Email must be unique and indexed for fast lookups
    hashed_password: str = Field(...) # Store hashed password, not plain text
    full_name: str = Field(...)
    role: UserRole = Field(UserRole.STUDENT) # Default role is student
    status: UserStatus = Field(UserStatus.PENDING_VERIFICATION) # Default status
    is_verified: bool = Field(False) # Flag to indicate if email is verified

    # Fields for email verification
    verification_token: Optional[str] = None
    verification_token_expires_at: Optional[datetime] = None

    # Fields for password reset
    reset_password_token: Optional[str] = None
    reset_password_token_expires_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        """
        Pydantic configuration for this model.
        """
        from_attributes = True # Enable ORM mode for compatibility with MongoDB documents
        populate_by_name = True # Allow population by field name or alias (_id to id)
        json_encoders = {ObjectId: str} # Convert ObjectId to string when serializing to JSON
        # Example schema for OpenAPI documentation
        json_schema_extra = {
            "example": {
                "email": "testuser@example.com",
                "hashed_password": "somehashedpassword",
                "full_name": "Test User",
                "role": "student",
                "status": "pending_verification",
                "is_verified": False
            }
        }

class CourseModel(BaseModel):
    """
    An example LMS-specific model for courses.
    This demonstrates how other LMS models can link to users using PyObjectId.
    """
    id: PyObjectId = Field(alias="_id", default_factory=ObjectId)
    title: str = Field(...)
    description: Optional[str] = None
    instructor_id: PyObjectId = Field(...) # Links to UserModel via ObjectId
    enrolled_students: List[PyObjectId] = Field(default_factory=list) # List of student ObjectIds

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "title": "Introduction to Python",
                "description": "A beginner-friendly course on Python programming.",
                "instructor_id": "60c72b2f9b1e8e001c8e4a1b", # Example ObjectId
                "enrolled_students": []
            }
        }

class EnrollmentModel(BaseModel):
    """
    An example LMS-specific model to track student-course enrollments.
    This also links to UserModel and CourseModel using PyObjectId.
    """
    id: PyObjectId = Field(alias="_id", default_factory=ObjectId)
    student_id: PyObjectId = Field(...) # Links to UserModel via ObjectId
    course_id: PyObjectId = Field(...) # Links to CourseModel via ObjectId
    enrollment_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["enrolled", "completed", "dropped"] = Field("enrolled")

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "student_id": "60c72b2f9b1e8e001c8e4a1c", # Example ObjectId
                "course_id": "60c72b2f9b1e8e001c8e4a1d", # Example ObjectId
                "status": "enrolled"
            }
        }
