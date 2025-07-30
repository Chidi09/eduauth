import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from eduauth.config import settings
from eduauth.email_utils import send_email
from eduauth.db_models import UserModel # Import UserModel for database operations
from eduauth.models import UserStatus # Import UserStatus Enum

# Placeholder for database connection. This will be properly initialized later.
# For now, assume 'database' is an object that can access your MongoDB collections.
# It will have a 'users' collection attribute.
# Example: from motor.motor_asyncio import AsyncIOMotorClient
# client = AsyncIOMotorClient(settings.MONGODB_URI)
# database = client.get_database("assignmentAppDB") # Replace with your actual database name

async def generate_verification_token() -> str:
    """
    Generates a secure, URL-safe random token for email verification.
    """
    return secrets.token_urlsafe(32) # Generates a 32-byte random string

async def send_verification_email(user_email: str, verification_token: str, db_users_collection: Any) -> bool:
    """
    Sends an email verification link to the user.

    Args:
        user_email (str): The email address of the user to verify.
        verification_token (str): The unique token generated for verification.
        db_users_collection (Any): The MongoDB collection object for 'users'.

    Returns:
        bool: True if the email was successfully queued/sent, False otherwise.
    """
    # In a real application, you'd construct a full URL to your frontend
    # where the user can click to verify. For now, we'll just include the token.
    # Example: verification_link = f"https://yourlms.com/verify-email?token={verification_token}"
    verification_link = f"Please use this token to verify your email: {verification_token}"

    subject = "Verify Your EduAuth Account"
    body = f"""
    <html>
    <body>
        <p>Hello,</p>
        <p>Thank you for registering with EduAuth!</p>
        <p>To complete your registration and activate your account, please verify your email address by clicking the link below or using the token provided:</p>
        <p><a href="{verification_link}">Verify My Email</a></p>
        <p>If the link doesn't work, you can use this token: <strong>{verification_token}</strong></p>
        <p>This link will expire in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES} minutes.</p>
        <p>If you did not register for an account, please ignore this email.</p>
        <p>Best regards,</p>
        <p>{settings.EMAIL_FROM_NAME}</p>
    </body>
    </html>
    """
    # Send the email using the utility function
    email_sent_result = await send_email(user_email, subject, body, is_html=True)
    return email_sent_result.get("status") == "success"

async def store_verification_token(user_id: str, token: str, db_users_collection: Any) -> bool:
    """
    Stores the verification token and its expiry in the user's database record.

    Args:
        user_id (str): The ID of the user.
        token (str): The verification token to store.
        db_users_collection (Any): The MongoDB collection object for 'users'.

    Returns:
        bool: True if the token was successfully stored, False otherwise.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES)
    try:
        # Find the user by ID and update their verification token fields
        result = await db_users_collection.update_one(
            {"_id": UserModel.Config.json_encoders[ObjectId](user_id)}, # Convert str user_id to ObjectId for query
            {"$set": {
                "verification_token": token,
                "verification_token_expires_at": expires_at,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error storing verification token for user {user_id}: {e}")
        return False

async def verify_user_email(verification_token: str, db_users_collection: Any) -> Optional[UserModel]:
    """
    Validates the verification token and marks the user's email as verified.

    Args:
        verification_token (str): The token received from the user.
        db_users_collection (Any): The MongoDB collection object for 'users'.

    Returns:
        Optional[UserModel]: The updated UserModel if verification is successful, None otherwise.
    """
    user = await db_users_collection.find_one({
        "verification_token": verification_token,
        "verification_token_expires_at": {"$gt": datetime.now(timezone.utc)} # Token must not be expired
    })

    if not user:
        return None # Token not found or expired

    # Mark user as verified and clear token fields
    try:
        await db_users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "is_verified": True,
                "status": UserStatus.ACTIVE.value, # Set status to active upon verification
                "verification_token": None, # Clear the token
                "verification_token_expires_at": None, # Clear expiry
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        # Fetch the updated user document
        updated_user = await db_users_collection.find_one({"_id": user["_id"]})
        return UserModel(**updated_user) # Return as Pydantic model
    except Exception as e:
        print(f"Error verifying user email for token {verification_token}: {e}")
        return None

