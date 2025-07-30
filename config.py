import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from datetime import timedelta

# Define the path to the .env file.
# This ensures that pydantic-settings looks for the .env file in the correct location.
# In a real application, you might adjust this based on your deployment strategy.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE_PATH = os.path.join(BASE_DIR, '.env')

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.
    """
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, extra='ignore')

    # MongoDB Settings
    # This is the connection string for your MongoDB database.
    # It will be loaded from the MONGODB_URI environment variable in your .env file.
    MONGODB_URI: str = "mongodb://localhost:27017/eduauth_lms" # Default for local development

    # JWT (JSON Web Token) Settings
    # These are crucial for securing your API endpoints.
    # JWT_SECRET_KEY: A strong, random key used to sign your JWTs. Keep this absolutely secret!
    JWT_SECRET_KEY: str = "your_super_secret_jwt_key_please_change_this_in_production"
    # JWT_ALGORITHM: The cryptographic algorithm used for signing (e.g., HS256).
    JWT_ALGORITHM: str = "HS256"
    # ACCESS_TOKEN_EXPIRE_MINUTES: How long the access token is valid (e.g., 30 minutes).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # REFRESH_TOKEN_EXPIRE_MINUTES: How long the refresh token is valid (e.g., 7 days).
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080 # 7 days * 24 hours * 60 minutes

    # Email Service (SMTP) Settings
    # These are used for sending verification and password reset emails.
    # SMTP_SERVER: The SMTP server address (e.g., smtp.gmail.com).
    SMTP_SERVER: str = "smtp.mailtrap.io" # Example for development/testing
    # SMTP_PORT: The port for the SMTP server (e.g., 587 for TLS, 465 for SSL).
    SMTP_PORT: int = 2525 # Example for Mailtrap
    # SMTP_USER: The username for your SMTP account.
    SMTP_USER: str = "your_smtp_username"
    # SMTP_PASSWORD: The password for your SMTP account.
    SMTP_PASSWORD: str = "your_smtp_password"
    # EMAIL_FROM_NAME: The name that appears as the sender of the email.
    EMAIL_FROM_NAME: str = "EduAuth Support"
    # EMAIL_FROM_ADDRESS: The email address from which emails are sent.
    EMAIL_FROM_ADDRESS: str = "no-reply@eduauth.com"

    # Password Reset Token Expiry
    # How long the password reset token is valid (e.g., 1 hour).
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60 # 1 hour

    # Email Verification Token Expiry
    # How long the email verification token is valid (e.g., 24 hours).
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 hours

# Create a settings instance to be imported and used throughout the application.
settings = Settings()

# You can print the loaded settings (excluding sensitive ones) for debugging
# print(f"MongoDB URI: {settings.MONGODB_URI}")
# print(f"JWT Algorithm: {settings.JWT_ALGORITHM}")
# print(f"Email From Address: {settings.EMAIL_FROM_ADDRESS}")

