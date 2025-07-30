from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from typing import Optional, Any
from datetime import datetime, timezone
from bson import ObjectId

from eduauth.config import settings
from eduauth.models import (
    UserCreate, UserLogin, UserResponse, Token, TokenData, UserRole, UserStatus
)
from eduauth.db_models import UserModel
from eduauth.jwt_handler import create_access_token, create_refresh_token, decode_token
from eduauth.verify_email import generate_verification_token, send_verification_email, store_verification_token
from eduauth.reset_password import generate_reset_password_token, send_password_reset_email, store_reset_password_token

# Password hashing context (using bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer for handling JWTs in Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- Password Hashing and Verification Functions ---
def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

# --- Database Dependency (Placeholder for now) ---
# This will be properly initialized in main.py or app.py
# For now, assume 'get_database' provides a database object with a 'users' collection.
async def get_database():
    """
    Dependency to get the MongoDB database client.
    This will be implemented fully in the main application file (e.g., main.py).
    """
    # In main.py, you would yield the actual database client
    # from motor.motor_asyncio import AsyncIOMotorClient
    # client = AsyncIOMotorClient(settings.MONGODB_URI)
    # db = client.get_database("assignmentAppDB") # Replace with your actual DB name
    # yield db
    # client.close()
    raise NotImplementedError("Database dependency not implemented yet. Implement in main.py.")

# --- Current User Dependency ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: Any = Depends(get_database)) -> UserModel:
    """
    Dependency to get the current authenticated user from the JWT.
    Raises HTTPException if the token is invalid or user not found/verified.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    unverified_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Account not verified. Please verify your email.",
    )

    try:
        token_data: TokenData = decode_token(token) # Decode the token using our handler
    except HTTPException as e:
        raise e # Re-raise JWT handler's exceptions directly

    user_id = token_data.id
    if user_id is None:
        raise credentials_exception

    # Fetch user from database using the ID from the token
    user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    if user_doc is None:
        raise credentials_exception

    user = UserModel(**user_doc) # Convert dict to Pydantic model

    # Check if the user's email is verified, unless they are an admin
    # Admins might be created directly and not require email verification
    if not user.is_verified and user.role != UserRole.ADMIN:
        raise unverified_exception

    return user

# --- Role-based Access Control (RBAC) Dependencies ---
def get_current_active_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Ensures the user is active."""
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def get_current_admin_user(current_user: UserModel = Depends(get_current_active_user)) -> UserModel:
    """Ensures the user has an 'admin' role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    return current_user

def get_current_teacher_or_admin_user(current_user: UserModel = Depends(get_current_active_user)) -> UserModel:
    """Ensures the user has a 'teacher' or 'admin' role."""
    if current_user.role not in [UserRole.TEACHER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Teacher or Admin access required."
        )
    return current_user

def get_current_student_user(current_user: UserModel = Depends(get_current_active_user)) -> UserModel:
    """Ensures the user has a 'student' role."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Student access required."
        )
    return current_user

