from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
from dotenv import load_dotenv
import logging
from starlette.responses import JSONResponse 
from starlette.requests import Request

# Load environment variables
load_dotenv()

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    try:
        # Get credentials path from environment
        cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            logger.info(f"Using Firebase credentials from: {cred_path}")
        else:
            cred = credentials.ApplicationDefault()
            logger.info("Using default Firebase credentials")
        
        firebase_admin.initialize_app(cred)
        logger.info("Firebase initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")

# Get Firestore client
db = firestore.client()

# Initialize FastAPI app
app = FastAPI(
    title="Notes API",
    description="A secure API for managing notes with Firebase integration",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# Pydantic models
class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Note title")
    content: str = Field(..., description="Note content")

class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Note title")
    content: Optional[str] = Field(None, description="Note content")

class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str
    user_id: str

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

# Authentication dependency
async def get_current_user(authorization: str = Header(None)):
    """
    Verify Firebase ID token and return user information
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )
    
    try:
        # Extract token from "Bearer <token>"
        if authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
        else:
            token = authorization
        
        # Verify the ID token
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Authentication token has expired"
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )

# Utility functions
def format_timestamp(timestamp):
    """Convert Firestore timestamp to ISO string"""
    if hasattr(timestamp, 'timestamp'):
        return datetime.fromtimestamp(timestamp.timestamp(), tz=timezone.utc).isoformat()
    return timestamp

def note_doc_to_dict(doc_id: str, doc_data: dict) -> dict:
    """Convert Firestore document to dictionary with proper formatting"""
    return {
        "id": doc_id,
        "title": doc_data.get("title", ""),
        "content": doc_data.get("content", ""),
        "created_at": format_timestamp(doc_data.get("created_at")),
        "updated_at": format_timestamp(doc_data.get("updated_at")),
        "user_id": doc_data.get("user_id", "")
    }

# API Routes

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Notes API is running", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Test Firestore connection
        test_ref = db.collection('health_check').document('test')
        test_ref.set({"timestamp": datetime.now(timezone.utc)})
        test_ref.delete()
        
        return {
            "status": "healthy",
            "services": {
                "firestore": "connected",
                "firebase_auth": "configured"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/notes", response_model=List[NoteResponse])
async def get_notes(current_user: dict = Depends(get_current_user)):
    """
    Get all notes for the authenticated user
    """
    try:
        user_id = current_user['uid']
        logger.info(f"Fetching notes for user: {user_id}")
        
        # Query notes for the current user
        notes_ref = db.collection('notes')
        query = notes_ref.where('user_id', '==', user_id).order_by('updated_at', direction=firestore.Query.DESCENDING)
        docs = query.stream()
        
        notes = []
        for doc in docs:
            note_data = note_doc_to_dict(doc.id, doc.to_dict())
            notes.append(note_data)
        
        logger.info(f"Retrieved {len(notes)} notes for user: {user_id}")
        return notes
        
    except Exception as e:
        logger.error(f"Error fetching notes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve notes"
        )

@app.post("/notes", response_model=NoteResponse, status_code=201)
async def create_note(note: NoteCreate, current_user: dict = Depends(get_current_user)):
    """
    Create a new note for the authenticated user
    """
    try:
        user_id = current_user['uid']
        logger.info(f"Creating note for user: {user_id}")
        
        # Create note document
        now = datetime.now(timezone.utc)
        note_data = {
            "title": note.title,
            "content": note.content,
            "user_id": user_id,
            "created_at": now,
            "updated_at": now
        }
        
        # Add to Firestore
        doc_ref = db.collection('notes').add(note_data)
        doc_id = doc_ref[1].id
        
        # Return created note
        created_note = note_doc_to_dict(doc_id, note_data)
        logger.info(f"Created note with ID: {doc_id} for user: {user_id}")
        
        return created_note
        
    except Exception as e:
        logger.error(f"Error creating note: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create note"
        )

@app.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get a specific note by ID (only if it belongs to the authenticated user)
    """
    try:
        user_id = current_user['uid']
        logger.info(f"Fetching note {note_id} for user: {user_id}")
        
        # Get the note document
        doc_ref = db.collection('notes').document(note_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="Note not found"
            )
        
        note_data = doc.to_dict()
        
        # Check if the note belongs to the current user
        if note_data.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied. This note doesn't belong to you."
            )
        
        return note_doc_to_dict(note_id, note_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching note: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve note"
        )

@app.put("/notes/{note_id}", response_model=NoteResponse)
async def update_note(note_id: str, note: NoteUpdate, current_user: dict = Depends(get_current_user)):
    """
    Update a specific note by ID (only if it belongs to the authenticated user)
    """
    try:
        user_id = current_user['uid']
        logger.info(f"Updating note {note_id} for user: {user_id}")
        
        # Get the note document first to verify ownership
        doc_ref = db.collection('notes').document(note_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="Note not found"
            )
        
        existing_data = doc.to_dict()
        
        # Check if the note belongs to the current user
        if existing_data.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied. This note doesn't belong to you."
            )
        
        # Prepare update data
        update_data = {"updated_at": datetime.now(timezone.utc)}
        
        if note.title is not None:
            update_data["title"] = note.title
        if note.content is not None:
            update_data["content"] = note.content
        
        # Update the document
        doc_ref.update(update_data)
        
        # Get the updated document
        updated_doc = doc_ref.get()
        updated_data = updated_doc.to_dict()
        
        logger.info(f"Updated note {note_id} for user: {user_id}")
        return note_doc_to_dict(note_id, updated_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating note: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update note"
        )

@app.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: str, current_user: dict = Depends(get_current_user)):
    """
    Delete a specific note by ID (only if it belongs to the authenticated user)
    """
    try:
        user_id = current_user['uid']
        logger.info(f"Deleting note {note_id} for user: {user_id}")
        
        # Get the note document first to verify ownership
        doc_ref = db.collection('notes').document(note_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="Note not found"
            )
        
        note_data = doc.to_dict()
        
        # Check if the note belongs to the current user
        if note_data.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied. This note doesn't belong to you."
            )
        
        # Delete the document
        doc_ref.delete()
        
        logger.info(f"Deleted note {note_id} for user: {user_id}")
        return  # 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting note: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete note"
        )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException): 
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )