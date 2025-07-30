import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from eduauth.config import settings
from eduauth.email_utils import send_email
from eduauth.db_models import UserModel # Import UserModel for database operations

# Placeholder for password hashing utility. This will be implemented in auth.py.
# For now, we'll use a simple placeholder function.
# In auth.py, you'll use passlib.context.CryptContext for bcrypt hashing.
def hash_password_placeholder(password: str) -> str:
    """
    Placeholder for the actual password hashing function.
    This will be replaced by a proper hashing mechanism (e.g., bcrypt) in auth.py.
    """
    # In a real scenario, this would be bcrypt.hash(password)
    return f"hashed_{password}"

async def generate_reset_password_token() -> str:
    """
    Generates a secure, URL-safe random token for password reset.
    """
    return secrets.token_urlsafe(32) # Generates a 32-byte random string

async def send_password_reset_email(user_email: str, reset_token: str, db_users_collection: Any) -> bool:
    """
    Sends a password reset link to the user.

    Args:
        user_email (str): The email address of the user requesting reset.
        reset_token (str): The unique token generated for password reset.
        db_users_collection (Any): The MongoDB collection object for 'users'.

    Returns:
        bool: True if the email was successfully queued/sent, False otherwise.
    """
    # In a real application, you'd construct a full URL to your frontend
    # where the user can enter their new password using this token.
    # Example: reset_link = f"https://yourlms.com/reset-password?token={reset_token}"
    reset_link = f"Please use this token to reset your password: {reset_token}"

    subject = "EduAuth Password Reset Request"
    body = f"""
    <html>
    <body>
        <p>Hello,</p>
        <p>You have requested to reset your password for your EduAuth account.</p>
        <p>To reset your password, please click the link below or use the token provided:</p>
        <p><a href="{reset_link}">Reset My Password</a></p>
        <p>If the link doesn't work, you can use this token: <strong>{reset_token}</strong></p>
        <p>This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
        <p>If you did not request a password reset, please ignore this email.</p>
        <p>Best regards,</p>
        <p>{settings.EMAIL_FROM_NAME}</p>
    </body>
    </html>
    """
    email_sent_result = await send_email(user_email, subject, body, is_html=True)
    return email_sent_result.get("status") == "success"

async def store_reset_password_token(user_id: str, token: str, db_users_collection: Any) -> bool:
    """
    Stores the password reset token and its expiry in the user's database record.

    Args:
        user_id (str): The ID of the user.
        token (str): The reset password token to store.
        db_users_collection (Any): The MongoDB collection object for 'users'.

    Returns:
        bool: True if the token was successfully stored, False otherwise.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    try:
        # Find the user by ID and update their reset token fields
        result = await db_users_collection.update_one(
            {"_id": UserModel.Config.json_encoders[ObjectId](user_id)}, # Convert str user_id to ObjectId for query
            {"$set": {
                "reset_password_token": token,
                "reset_password_token_expires_at": expires_at,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error storing reset password token for user {user_id}: {e}")
        return False

async def reset_user_password(reset_token: str, new_password: str, db_users_collection: Any) -> Optional[UserModel]:
    """
    Validates the reset token and updates the user's password.

    Args:
        reset_token (str): The token received from the user.
        new_password (str): The new password provided by the user.
        db_users_collection (Any): The MongoDB collection object for 'users'.

    Returns:
        Optional[UserModel]: The updated UserModel if password reset is successful, None otherwise.
    """
    user = await db_users_collection.find_one({
        "reset_password_token": reset_token,
        "reset_password_token_expires_at": {"$gt": datetime.now(timezone.utc)} # Token must not be expired
    })

    if not user:
        return None # Token not found or expired

    # Hash the new password before storing it
    hashed_new_password = hash_password_placeholder(new_password) # This will be replaced by actual bcrypt hashing

    # Update the user's password and clear token fields
    try:
        await db_users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "hashed_password": hashed_new_password,
                "reset_password_token": None, # Clear the token
                "reset_password_token_expires_at": None, # Clear expiry
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        # Fetch the updated user document
        updated_user = await db_users_collection.find_one({"_id": user["_id"]})
        return UserModel(**updated_user) # Return as Pydantic model
    except Exception as e:
        print(f"Error resetting password for token {reset_token}: {e}")
        return None

