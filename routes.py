from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorClient # For MongoDB client
from typing import Any, Optional
from datetime import datetime, timezone
from bson import ObjectId

from eduauth.config import settings
from eduauth.models import (
    UserCreate, UserLogin, UserResponse, Token, TokenData,
    PasswordResetRequest, PasswordResetConfirm, EmailVerificationRequest,
    UserRole, UserStatus
)
from eduauth.db_models import UserModel
from eduauth.auth import (
    hash_password, verify_password, get_database,
    get_current_user, get_current_admin_user,
    get_current_teacher_or_admin_user, get_current_student_user,
    get_current_active_user # Import all necessary auth dependencies
)
from eduauth.jwt_handler import create_access_token
from eduauth.verify_email import generate_verification_token, send_verification_email, store_verification_token, verify_user_email
from eduauth.reset_password import generate_reset_password_token, send_password_reset_email, store_reset_password_token, reset_user_password
from eduauth.decorators import admin_required, teacher_or_admin_required, student_required, active_user_required # Import decorators

# Initialize FastAPI Router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# --- Helper function to get MongoDB users collection ---
async def get_users_collection(db: AsyncIOMotorClient = Depends(get_database)):
    """Dependency that provides the MongoDB 'users' collection."""
    # Ensure the database name matches what's in your MONGODB_URI or explicitly set it
    return db.get_database("assignmentAppDB").users # Replace "assignmentAppDB" with your actual database name if different

# --- User Registration ---
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_create: UserCreate,
    background_tasks: BackgroundTasks,
    users_collection: Any = Depends(get_users_collection)
):
    """
    Registers a new user.
    - Hashes the password.
    - Creates a user document in MongoDB.
    - Sends an email verification link.
    """
    # Check if a user with the given email already exists
    existing_user = await users_collection.find_one({"email": user_create.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered."
        )

    # Hash the user's password
    hashed_password = hash_password(user_create.password)

    # Generate verification token
    verification_token = await generate_verification_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES)

    # Create a new UserModel instance
    new_user_data = UserModel(
        email=user_create.email,
        hashed_password=hashed_password,
        full_name=user_create.full_name,
        role=user_create.role,
        status=UserStatus.PENDING_VERIFICATION, # New users are pending verification
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires_at=expires_at
    )

    # Insert the new user into the database
    insert_result = await users_collection.insert_one(new_user_data.model_dump(by_alias=True, exclude_none=True))
    new_user_data.id = insert_result.inserted_id # Set the ID from the database

    # Send verification email as a background task
    background_tasks.add_task(send_verification_email,
                              new_user_data.email,
                              verification_token,
                              users_collection) # Pass the collection for the task

    return UserResponse(**new_user_data.model_dump(by_alias=True)) # Return the created user data

# --- Email Verification ---
@router.get("/verify-email", response_model=UserResponse)
async def verify_email_endpoint(
    token: str,
    users_collection: Any = Depends(get_users_collection)
):
    """
    Verifies a user's email using the provided token.
    """
    verified_user = await verify_user_email(token, users_collection)
    if not verified_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token."
        )
    return verified_user

@router.post("/resend-verification-email", status_code=status.HTTP_200_OK)
async def resend_verification_email_endpoint(
    request: EmailVerificationRequest,
    background_tasks: BackgroundTasks,
    users_collection: Any = Depends(get_users_collection)
):
    """
    Resends an email verification link to the user if their account is not verified.
    """
    user_doc = await users_collection.find_one({"email": request.email})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    user = UserModel(**user_doc)

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified."
        )

    # Generate a new token and update the user record
    new_verification_token = await generate_verification_token()
    updated = await store_verification_token(user.id, new_verification_token, users_collection)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update verification token."
        )

    # Send new verification email
    background_tasks.add_task(send_verification_email,
                              user.email,
                              new_verification_token,
                              users_collection)
    return {"message": "Verification email resent successfully."}


# --- User Login ---
@router.post("/login", response_model=Token)
async def login_for_access_token(
    user_login: UserLogin,
    users_collection: Any = Depends(get_users_collection)
):
    """
    Authenticates a user and returns an access token upon successful login.
    """
    user_doc = await users_collection.find_one({"email": user_login.email})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = UserModel(**user_doc)

    # Verify password
    if not verify_password(user_login.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is active and verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not verified. Please verify your email.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token (and potentially a refresh token)
    access_token = create_access_token(
        data={"email": user.email, "role": user.role.value, "id": str(user.id)}
    )
    # You might also create a refresh token here if implementing refresh token flow
    return {"access_token": access_token, "token_type": "bearer"}

# --- Password Reset Request ---
@router.post("/reset-password-request", status_code=status.HTTP_200_OK)
async def request_password_reset(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    users_collection: Any = Depends(get_users_collection)
):
    """
    Initiates the password reset process by sending a reset link to the user's email.
    """
    user_doc = await users_collection.find_one({"email": request.email})
    if not user_doc:
        # For security, always return a generic success message even if email not found
        # to prevent enumeration of existing users.
        return {"message": "If your email is registered, a password reset link has been sent."}

    user = UserModel(**user_doc)

    # Generate and store reset token
    reset_token = await generate_reset_password_token()
    updated = await store_reset_password_token(user.id, reset_token, users_collection)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate password reset token."
        )

    # Send password reset email as a background task
    background_tasks.add_task(send_password_reset_email,
                              user.email,
                              reset_token,
                              users_collection)
    return {"message": "If your email is registered, a password reset link has been sent."}

# --- Password Reset Confirmation ---
@router.post("/reset-password-confirm", response_model=UserResponse)
async def confirm_password_reset(
    request: PasswordResetConfirm,
    users_collection: Any = Depends(get_users_collection)
):
    """
    Confirms the password reset using the token and sets the new password.
    """
    updated_user = await reset_user_password(request.token, request.new_password, users_collection)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token."
        )
    return updated_user

# --- Protected Routes (Examples using RBAC Decorators) ---

@router.get("/protected/student", response_model=UserResponse)
@student_required() # Apply the student_required decorator
async def protected_student_route(current_user: UserModel = Depends(get_current_student_user)):
    """
    Example protected route for students.
    Only users with 'student' role can access this.
    """
    return current_user # Returns the student's own user data

@router.get("/protected/teacher", response_model=UserResponse)
@teacher_or_admin_required() # Apply the teacher_or_admin_required decorator
async def protected_teacher_route(current_user: UserModel = Depends(get_current_teacher_or_admin_user)):
    """
    Example protected route for teachers and admins.
    Only users with 'teacher' or 'admin' role can access this.
    """
    return current_user # Returns the teacher's/admin's own user data

@router.get("/protected/admin", response_model=UserResponse)
@admin_required() # Apply the admin_required decorator
async def protected_admin_route(current_user: UserModel = Depends(get_current_admin_user)):
    """
    Example protected route for administrators.
    Only users with 'admin' role can access this.
    """
    return current_user # Returns the admin's own user data

@router.get("/protected/any-active", response_model=UserResponse)
@active_user_required() # Apply the active_user_required decorator
async def protected_any_active_route(current_user: UserModel = Depends(get_current_active_user)):
    """
    Example protected route for any active authenticated user.
    """
    return current_user # Returns the active user's own user data

