from fastapi import FastAPI, Request, Response, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware # For CORS configuration

from eduauth.config import settings # Import our application settings
from eduauth.routes import router as auth_router # Import the authentication router

# --- Database Connection Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application lifespan events.
    Handles database connection on startup and disconnection on shutdown.
    """
    print("Starting up application...")
    # Connect to MongoDB
    try:
        app.mongodb_client = AsyncIOMotorClient(settings.MONGODB_URI)
        app.mongodb = app.mongodb_client.get_database("assignmentAppDB") # Use your actual database name
        print("Connected to MongoDB!")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        # Optionally, raise an exception or exit if DB connection is critical
        raise

    yield # Application runs here

    # Disconnect from MongoDB on shutdown
    print("Shutting down application...")
    app.mongodb_client.close()
    print("Disconnected from MongoDB.")

# Initialize FastAPI application with lifespan context manager
app = FastAPI(
    title="EduAuth Authentication Module API",
    description="A pluggable authentication module for custom LMS using FastAPI and MongoDB.",
    version="1.0.0",
    lifespan=lifespan # Assign the lifespan context manager
)

# --- CORS Configuration (Enhancement) ---
# This is crucial for allowing your frontend application to communicate with this API.
# Adjust `allow_origins` to your frontend's URL(s) in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development. Change this to specific domains in production, e.g., ["http://localhost:3000", "https://yourlmsfrontend.com"]
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

# --- Dependency for Database Access ---
# This function will be used by FastAPI's Depends() to inject the MongoDB database object
async def get_database():
    """
    FastAPI dependency that yields the MongoDB database object.
    """
    if not hasattr(app, "mongodb"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized. Application is not ready."
        )
    return app.mongodb

# Override the get_database dependency in auth.py and routes.py
# This tells FastAPI to use our actual database connection.
# We modify the original functions to use the app's mongodb attribute.
import eduauth.auth
import eduauth.routes

eduauth.auth.get_database = get_database
eduauth.routes.get_database = get_database

# Include the authentication router
app.include_router(auth_router)

# --- Root Endpoint (Optional) ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to EduAuth API! Visit /docs for API documentation."}

