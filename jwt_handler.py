import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from typing import Dict, Any

from eduauth.config import settings
from eduauth.models import TokenData, UserRole # Import TokenData and UserRole for type hinting

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a new JWT access token.

    Args:
        data (Dict[str, Any]): The payload to be encoded in the token.
                               This typically includes user ID, email, and role.
        expires_delta (Optional[timedelta]): The timedelta for the token's expiration.
                                            If None, uses the default from settings.

    Returns:
        str: The encoded JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default access token expiration from settings
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire}) # Add expiration timestamp to the payload
    # Encode the token using the secret key and algorithm from settings
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a new JWT refresh token.
    Refresh tokens typically have a longer expiration time.

    Args:
        data (Dict[str, Any]): The payload to be encoded in the token.
        expires_delta (Optional[timedelta]): The timedelta for the token's expiration.
                                            If None, uses the default from settings.

    Returns:
        str: The encoded JWT refresh token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default refresh token expiration from settings
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> TokenData:
    """
    Decodes and validates a JWT.

    Args:
        token (str): The JWT string to decode.

    Returns:
        TokenData: A Pydantic model containing the decoded token payload (email, role, id).

    Raises:
        HTTPException: If the token is invalid, expired, or has missing credentials.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the token. The options disable specific validation checks
        # if you want to handle them manually, but generally, it's good to let PyJWT do it.
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], options={"verify_exp": True})

        # Extract email, role, and id from the payload
        email: str = payload.get("email")
        role: str = payload.get("role")
        user_id: str = payload.get("id")

        if email is None or role is None or user_id is None:
            raise credentials_exception
        
        # Return the payload as a TokenData Pydantic model for type safety
        return TokenData(email=email, role=UserRole(role), id=user_id)
    except jwt.ExpiredSignatureError:
        # Handle expired token specifically
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        # Handle any other invalid token errors
        raise credentials_exception
    except Exception as e:
        # Catch any other unexpected errors during decoding
        print(f"Error decoding token: {e}")
        raise credentials_exception

