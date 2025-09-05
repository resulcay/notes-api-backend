import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import sys

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock environment variables before importing main
with patch.dict(os.environ, {
    'GOOGLE_APPLICATION_CREDENTIALS': 'test-credentials.json',
    'FIREBASE_PROJECT_ID': 'test-project'
}):
    # Mock Firebase before importing main
    with patch('firebase_admin.initialize_app'), \
         patch('firebase_admin._apps', []), \
         patch('firebase_admin.credentials.Certificate'), \
         patch('firebase_admin.firestore.client'):
        
        from main import app

# Create test client
client = TestClient(app)

# Mock Firebase user token
MOCK_USER_TOKEN = "mock-firebase-token"
MOCK_USER_ID = "mock-user-123"

@pytest.fixture
def mock_firebase_auth():
    """Mock Firebase authentication"""
    with patch('main.auth.verify_id_token') as mock_verify:
        mock_verify.return_value = {
            'uid': MOCK_USER_ID,
            'email': 'test@example.com'
        }
        yield mock_verify

@pytest.fixture
def mock_firestore():
    """Mock Firestore database"""
    with patch('main.db') as mock_db:
        yield mock_db

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Notes API is running" in response.json()["message"]

def test_get_notes_unauthorized():
    """Test getting notes without authentication"""
    response = client.get("/notes")
    assert response.status_code == 401

def test_get_notes_authorized(mock_firebase_auth, mock_firestore):
    """Test getting notes with authentication"""
    # Mock Firestore response
    mock_doc = MagicMock()
    mock_doc.id = "note-123"
    mock_doc.to_dict.return_value = {
        "title": "Test Note",
        "content": "Test Content",
        "user_id": MOCK_USER_ID,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
    
    mock_firestore.collection.return_value.where.return_value.order_by.return_value.stream.return_value = [mock_doc]
    
    response = client.get(
        "/notes",
        headers={"Authorization": f"Bearer {MOCK_USER_TOKEN}"}
    )
    
    assert response.status_code == 200
    notes = response.json()
    assert len(notes) == 1
    assert notes[0]["title"] == "Test Note"

def test_create_note_unauthorized():
    """Test creating note without authentication"""
    note_data = {
        "title": "New Note",
        "content": "New Content"
    }
    
    response = client.post("/notes", json=note_data)
    assert response.status_code == 401

def test_create_note_authorized(mock_firebase_auth, mock_firestore):
    """Test creating note with authentication"""
    note_data = {
        "title": "New Note",
        "content": "New Content"
    }
    
    # Mock Firestore add operation
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "new-note-123"
    mock_firestore.collection.return_value.add.return_value = (None, mock_doc_ref)
    
    response = client.post(
        "/notes",
        json=note_data,
        headers={"Authorization": f"Bearer {MOCK_USER_TOKEN}"}
    )
    
    assert response.status_code == 201
    created_note = response.json()
    assert created_note["title"] == "New Note"
    assert created_note["content"] == "New Content"
    assert created_note["user_id"] == MOCK_USER_ID

def test_create_note_invalid_data():
    """Test creating note with invalid data"""
    invalid_data = {
        "title": "",  # Empty title should fail validation
        "content": "Content"
    }
    
    response = client.post(
        "/notes",
        json=invalid_data,
        headers={"Authorization": f"Bearer {MOCK_USER_TOKEN}"}
    )
    
    assert response.status_code == 422  # Validation error

def test_update_note_authorized(mock_firebase_auth, mock_firestore):
    """Test updating note with authentication"""
    note_id = "note-123"
    update_data = {
        "title": "Updated Title",
        "content": "Updated Content"
    }
    
    # Mock existing document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "title": "Old Title",
        "content": "Old Content",
        "user_id": MOCK_USER_ID,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
    
    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_doc
    mock_firestore.collection.return_value.document.return_value = mock_doc_ref
    
    response = client.put(
        f"/notes/{note_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {MOCK_USER_TOKEN}"}
    )
    
    assert response.status_code == 200
    updated_note = response.json()
    assert updated_note["title"] == "Updated Title"

def test_update_note_not_found(mock_firebase_auth, mock_firestore):
    """Test updating non-existent note"""
    note_id = "non-existent"
    update_data = {"title": "Updated Title"}
    
    # Mock non-existent document
    mock_doc = MagicMock()
    mock_doc.exists = False
    
    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_doc
    mock_firestore.collection.return_value.document.return_value = mock_doc_ref
    
    response = client.put(
        f"/notes/{note_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {MOCK_USER_TOKEN}"}
    )
    
    assert response.status_code == 404

def test_update_note_wrong_owner(mock_firebase_auth, mock_firestore):
    """Test updating note that belongs to another user"""
    note_id = "note-123"
    update_data = {"title": "Updated Title"}
    
    # Mock document belonging to different user
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "title": "Other User's Note",
        "content": "Content",
        "user_id": "other-user-456",  # Different user
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
    
    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_doc
    mock_firestore.collection.return_value.document.return_value = mock_doc_ref
    
    response = client.put(
        f"/notes/{note_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {MOCK_USER_TOKEN}"}
    )
    
    assert response.status_code == 403

def test_delete_note_authorized(mock_firebase_auth, mock_firestore):
    """Test deleting note with authentication"""
    note_id = "note-123"
    
    # Mock existing document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "title": "Note to Delete",
        "content": "Content",
        "user_id": MOCK_USER_ID,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
    
    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_doc
    mock_firestore.collection.return_value.document.return_value = mock_doc_ref
    
    response = client.delete(
        f"/notes/{note_id}",
        headers={"Authorization": f"Bearer {MOCK_USER_TOKEN}"}
    )
    
    assert response.status_code == 204
    # Verify delete was called
    mock_doc_ref.delete.assert_called_once()

def test_delete_note_not_found(mock_firebase_auth, mock_firestore):
    """Test deleting non-existent note"""
    note_id = "non-existent"
    
    # Mock non-existent document
    mock_doc = MagicMock()
    mock_doc.exists = False
    
    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_doc
    mock_firestore.collection.return_value.document.return_value = mock_doc_ref
    
    response = client.delete(
        f"/notes/{note_id}",
        headers={"Authorization": f"Bearer {MOCK_USER_TOKEN}"}
    )
    
    assert response.status_code == 404

def test_get_single_note_authorized(mock_firebase_auth, mock_firestore):
    """Test getting single note with authentication"""
    note_id = "note-123"
    
    # Mock existing document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "title": "Single Note",
        "content": "Single Content",
        "user_id": MOCK_USER_ID,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
    
    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_doc
    mock_firestore.collection.return_value.document.return_value = mock_doc_ref
    
    response = client.get(
        f"/notes/{note_id}",
        headers={"Authorization": f"Bearer {MOCK_USER_TOKEN}"}
    )
    
    assert response.status_code == 200
    note = response.json()
    assert note["title"] == "Single Note"
    assert note["id"] == note_id

if __name__ == "__main__":
    pytest.main([__file__])