# Notes API Backend

A secure FastAPI backend for a note-taking application with Firebase integration. This API provides full CRUD operations for notes with user authentication and authorization.

## Features

- **Secure Authentication**: Firebase ID token verification
- **CRUD Operations**: Create, read, update, delete notes
- **User Isolation**: Users can only access their own notes
- **Input Validation**: Pydantic models for request validation
- **Error Handling**: Comprehensive error responses
- **Logging**: Detailed application logging
- **Health Checks**: Built-in health monitoring endpoints
- **CORS Support**: Configurable cross-origin resource sharing

## Prerequisites

- Python 3.11 or higher
- Firebase project with Firestore enabled
- Firebase service account key
- Git

## Installation & Setup

### 1. Clone the Repository

```bash
git clone ...
cd notes-api-backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing one
3. Enable Firestore Database
4. Go to Project Settings > Service Accounts
5. Generate new private key (downloads JSON file)
6. Save the JSON file as `firebase-service-account-key.json` in your project root

### 5. Environment Configuration

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

```bash
GOOGLE_APPLICATION_CREDENTIALS=firebase-service-account-key.json
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=development
FIREBASE_PROJECT_ID=your-firebase-project-id
```

### 6. Run the Application

#### Development Mode

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

or

```bash
python -m uvicorn main:app --reload
```

#### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Using Docker

```bash
docker-compose up --build
```

## API Documentation

Once the server is running, you can access:

- **Interactive API Documentation**: <http://localhost:8000/docs>
- **ReDoc Documentation**: <http://localhost:8000/redoc>
- **OpenAPI JSON**: <http://localhost:8000/openapi.json>

## API Endpoints

### Authentication

All protected endpoints require a Firebase ID token in the Authorization header:

`Authorization: Bearer <firebase-id-token>`

### Health Check Endpoints

#### GET `/`

Basic health check endpoint.

**Response:**

```json
{
  "message": "Notes API is running",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

#### GET `/health`

Detailed health check with service status.

**Response:**

```json
{
  "status": "healthy",
  "services": {
    "firestore": "connected",
    "firebase_auth": "configured"
  },
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### Notes Endpoints

#### GET `/notes`

Retrieve all notes for the authenticated user.

**Headers:**

- `Authorization: Bearer <firebase-id-token>`

**Response:**

```json
[
  {
    "id": "note123",
    "title": "My Note",
    "content": "Note content here",
    "created_at": "2024-01-01T00:00:00.000Z",
    "updated_at": "2024-01-01T00:00:00.000Z",
    "user_id": "user123"
  }
]
```

#### POST `/notes`

Create a new note.

**Headers:**

- `Authorization: Bearer <firebase-id-token>`
- `Content-Type: application/json`

**Request Body:**

```json
{
  "title": "My New Note",
  "content": "This is the content of my new note"
}
```

**Response:** `201 Created`

```json
{
  "id": "note456",
  "title": "My New Note",
  "content": "This is the content of my new note",
  "created_at": "2024-01-01T00:00:00.000Z",
  "updated_at": "2024-01-01T00:00:00.000Z",
  "user_id": "user123"
}
```

#### GET `/notes/{note_id}`

Retrieve a specific note by ID.

**Headers:**

- `Authorization: Bearer <firebase-id-token>`

**Response:**

```json
{
  "id": "note123",
  "title": "My Note",
  "content": "Note content here",
  "created_at": "2024-01-01T00:00:00.000Z",
  "updated_at": "2024-01-01T00:00:00.000Z",
  "user_id": "user123"
}
```

#### PUT `/notes/{note_id}`

Update a specific note.

**Headers:**

- `Authorization: Bearer <firebase-id-token>`
- `Content-Type: application/json`

**Request Body:**

```json
{
  "title": "Updated Title",
  "content": "Updated content"
}
```

**Response:**

```json
{
  "id": "note123",
  "title": "Updated Title",
  "content": "Updated content",
  "created_at": "2024-01-01T00:00:00.000Z",
  "updated_at": "2024-01-01T12:00:00.000Z",
  "user_id": "user123"
}
```

#### DELETE `/notes/{note_id}`

Delete a specific note.

**Headers:**

- `Authorization: Bearer <firebase-id-token>`

**Response:** `204 No Content`

## Security Features

### Authentication Feature

- Firebase ID token verification
- Automatic token expiration handling
- Invalid token rejection

### Authorization Feature

- User isolation: Users can only access their own notes
- Resource ownership validation
- Proper HTTP status codes for unauthorized access

### Data Validation Feature

- Input validation using Pydantic models
- Title length constraints (1-255 characters)
- Required field validation

## Testing Feature

### Install Test Dependencies

```bash
pip install pytest pytest-asyncio httpx
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=main

# Run specific test file
pytest test_main.py

# Run with verbose output
pytest -v
```

### Test Coverage

The test suite includes:

- Authentication tests
- CRUD operation tests
- Error handling tests
- Security validation tests
- Edge case scenarios

## Deployment

### Docker Deployment

1 - **Build the image:**

```bash
docker build -t notes-api .
```

2 - **Run the container:**

```bash
docker run -p 8000:8000 --env-file .env notes-api
```

3 - **Using docker-compose:**

```bash
docker-compose up -d
```

### Cloud Deployment (Google Cloud Run)

1 - **Build and push to Google Container Registry:**

```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Build and tag
docker build -t gcr.io/YOUR-PROJECT-ID/notes-api .

# Push to registry
docker push gcr.io/YOUR-PROJECT-ID/notes-api
```

2 - **Deploy to Cloud Run:**

```bash
gcloud run deploy notes-api \
  --image gcr.io/PROJECT-ID/notes-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production
```

### Environment Variables for Production

```bash
# Required
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
FIREBASE_PROJECT_ID=your-production-project-id

# Optional
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=production
```

## Monitoring & Logging

### Built-in Logging

The application includes comprehensive logging:

- Request/response logging
- Error tracking
- Authentication events
- Database operations

### Health Monitoring

- Health check endpoints for load balancers
- Service dependency verification
- Firestore connection testing

### Metrics

Monitor these key metrics:

- Response times
- Error rates
- Authentication failures
- Database query performance

## Configuration

### CORS Configuration

Update CORS settings in `main.py` for production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://flutter-app.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Firestore Security Rules

Recommended Firestore rules for additional security:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /notes/{noteId} {
      allow read, write: if request.auth != null && request.auth.uid == resource.data.user_id;
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Firebase service account key path
   - Check token format (should include "Bearer ")
   - Ensure Firebase project ID is correct

2. **Firestore Connection Issues**
   - Verify service account has Firestore permissions
   - Check network connectivity
   - Ensure Firestore is enabled in Firebase project

3. **CORS Errors**
   - Update CORS configuration for your Flutter app domain
   - Check request headers and methods

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
uvicorn main:app --log-level debug
```

## Development Notes

### Code Structure

├── main.py             # Main FastAPI application
├── requirements.txt    # Python dependencies
├── .env                # Environment variables template
├── Dockerfile          # Container configuration
├── docker-compose.yml  # Local development setup
├── test_main.py        # Test suite
└── README.md           # This file

### Adding New Features

1. Add endpoint to `main.py`
2. Add corresponding tests in `test_main.py`
3. Update API documentation
4. Update this README if needed

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For questions or issues:

1. Check the troubleshooting section
2. Review the API documentation
3. Create an issue in the repository

## Version History

- **v1.0.0**: Initial release with CRUD operations and Firebase integration
