from pydantic import BaseModel, EmailStr, Field, BeforeValidator
from typing import Optional, List, Literal, Annotated
from enum import Enum
from bson import ObjectId

# Custom type for MongoDB's ObjectId to work with Pydantic
# This ensures that Pydantic can handle ObjectId objects correctly during serialization/deserialization.
PyObjectId = Annotated[str, BeforeValidator(str)]

class UserRole(str, Enum):
    """
    Defines the possible roles a user can have within the LMS.
    This provides strong typing and limits roles to predefined values.
    """
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

class UserStatus(str, Enum):
    """
    Defines the possible statuses of a user account.
    This helps in managing account states like active, inactive, or pending verification.
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"

class UserCreate(BaseModel):
    """
    Schema for user registration (input model).
    Defines the data required when a new user signs up.
    """
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=8, example="StrongP@ssw0rd")
    full_name: str = Field(..., example="John Doe")
    # Role is optional here, as it might be set by default or by an admin
    # Literal ensures that the role must be one of the specified strings
    role: Optional[UserRole] = Field(UserRole.STUDENT, example="student")

class UserLogin(BaseModel):
    """
    Schema for user login (input model).
    Defines the data required for a user to log in.
    """
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., example="StrongP@ssw0rd")

class UserResponse(BaseModel):
    """
    Schema for user data returned by the API (output model).
    This defines what user information is exposed to the client.
    It includes the PyObjectId for MongoDB document ID.
    """
    id: PyObjectId = Field(alias="_id", default=None) # Maps MongoDB's _id to 'id'
    email: EmailStr
    full_name: str
    role: UserRole
    status: UserStatus
    is_verified: bool
    # Pydantic's Config class allows for additional model configuration.
    # from_attributes = True is used to enable compatibility with ORM/ODM models,
    # allowing Pydantic to read data directly from object attributes.
    class Config:
        from_attributes = True # Formerly orm_mode = True in older Pydantic versions
        populate_by_name = True # Allows mapping by alias (e.g., _id to id)
        json_encoders = {ObjectId: str} # Ensures ObjectId is serialized as a string

class Token(BaseModel):
    """
    Schema for JWT tokens returned upon successful login.
    """
    access_token: str
    token_type: str = "bearer" # Standard token type

class TokenData(BaseModel):
    """
    Schema for data contained within a JWT.
    This is used to extract user information from the token.
    """
    email: Optional[str] = None
    role: Optional[UserRole] = None
    id: Optional[PyObjectId] = None # User ID from the database

class PasswordResetRequest(BaseModel):
    """
    Schema for requesting a password reset.
    Requires only the user's email.
    """
    email: EmailStr = Field(..., example="user@example.com")

class PasswordResetConfirm(BaseModel):
    """
    Schema for confirming a password reset.
    Requires the reset token and the new password.
    """
    token: str = Field(..., example="a_long_reset_token_string")
    new_password: str = Field(..., min_length=8, example="NewStrongP@ssw0rd")

class EmailVerificationRequest(BaseModel):
    """
    Schema for requesting a new email verification link.
    Requires only the user's email.
    """
    email: EmailStr = Field(..., example="user@example.com")

