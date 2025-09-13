# Mistral Local API Server

A well-structured FastAPI-based REST API server that exposes your local Mistral 7B model with PostgreSQL database integration for conversation logging and usage analytics.

## Project Structure

```
API/
├── app/                    # Main application code
│   ├── __init__.py
│   ├── main.py            # FastAPI application and startup logic
│   ├── models.py          # Pydantic models for requests/responses
│   ├── utils.py           # Utility functions
│   ├── database.py        # PostgreSQL database manager
│   ├── model_server.py    # Mistral model server manager
│   └── routes/            # API route handlers
│       ├── __init__.py
│       ├── health.py      # Health check endpoints
│       ├── chat.py        # Chat completion endpoints
│       ├── completions.py # Simple completion endpoints
│       ├── conversations.py # Conversation history endpoints
│       └── stats.py       # Usage statistics endpoints
├── config/                # Configuration files
│   ├── __init__.py
│   └── settings.py        # Application settings
├── scripts/               # Utility scripts
│   └── run_api.py         # API server runner script
├── tests/                 # Test files
│   └── test_api.py        # API endpoint tests
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
└── README.md             # This file
```

## Features

- 🚀 **Local Model Serving**: Exposes your local Mistral 7B model via REST API
- 🐘 **PostgreSQL Integration**: Logs all conversations and API usage to your Render database
- 🔄 **OpenAI-Compatible**: Compatible with OpenAI API format for easy integration
- 📊 **Analytics**: Built-in usage statistics and conversation history
- ⚡ **GPU Acceleration**: Uses your RTX 3050 for fast inference
- 🔒 **Session Management**: Track conversations across multiple requests
- 🏗️ **Clean Architecture**: Well-organized modular structure
- 🧪 **Comprehensive Testing**: Built-in test suite for all endpoints

## Quick Start

### 1. Install Dependencies

```bash
cd API
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the environment template:
```bash
cp .env.example .env
```

Edit `.env` with your Render PostgreSQL connection string:
```env
DATABASE_URL=postgresql://username:password@hostname:port/database_name
```

### 3. Run the API Server

```bash
cd scripts
python run_api.py
```

The server will start on `http://localhost:9000`

### 4. Test the API

```bash
cd tests
python test_api.py
```

## API Endpoints

### Health Check
```http
GET /health
```

### Chat Completions (OpenAI Compatible)
```http
POST /v1/chat/completions
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "model": "mistral-7b-instruct",
  "temperature": 0.7,
  "max_tokens": 300,
  "session_id": "optional-session-id"
}
```

### Simple Completions
```http
POST /v1/completions
Content-Type: application/json

{
  "prompt": "The capital of France is",
  "model": "mistral-7b-instruct",
  "temperature": 0.7,
  "max_tokens": 100
}
```

### Conversation History
```http
GET /v1/conversations/{session_id}?limit=10
```

### Usage Statistics
```http
GET /v1/stats?hours=24
```

## Architecture

### Application Flow

```
External Request → FastAPI Router → Route Handler → Model Server → Response + Logging
                                         ↓
                                 PostgreSQL Database
```

### Key Components

1. **`app/main.py`**: FastAPI application factory and lifecycle management
2. **`app/routes/`**: Modular route handlers for different API endpoints
3. **`app/database.py`**: PostgreSQL connection and data models
4. **`app/model_server.py`**: Mistral model server orchestration
5. **`config/settings.py`**: Centralized configuration management

### Server State Management

The API uses a global `ServerState` class to manage the model server instance across all route handlers, avoiding circular imports and ensuring clean startup/shutdown.

## Configuration

All configuration is handled through environment variables defined in `.env`:

```env
# Database
DATABASE_URL=postgresql://username:password@hostname:port/database_name

# API Server
API_HOST=0.0.0.0
API_PORT=9000

# Model Server
MODEL_SERVER_HOST=127.0.0.1
MODEL_SERVER_PORT=8081

# GPU Settings (RTX 3050)
GPU_LAYERS=20
CONTEXT_SIZE=32768
BATCH_SIZE=2048
THREADS=8
```

## Development

### Running in Development Mode

```bash
cd scripts
python run_api.py
```

### Running Tests

```bash
cd tests
python test_api.py
```

### Adding New Endpoints

1. Create a new route file in `app/routes/`
2. Define your route handlers
3. Import and register in `app/main.py`
4. Add tests in `tests/test_api.py`

### Database Migrations

The database schema is automatically created on startup. Tables include:
- `conversations`: Chat history and metadata
- `api_usage`: Request logging and analytics

## Production Deployment

### Security Considerations

- Add API key authentication
- Configure CORS origins properly
- Use HTTPS with SSL certificates
- Implement rate limiting
- Monitor logs for suspicious activity

### Performance Optimization

- Adjust GPU layers based on your RTX 3050 VRAM
- Monitor response times via `/v1/stats`
- Use connection pooling for database (already implemented)
- Consider caching for repeated queries

### Monitoring

- Health checks at `/health`
- Usage statistics at `/v1/stats`
- Database query monitoring
- GPU utilization tracking

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running scripts from the correct directory
2. **Database Connection**: Verify DATABASE_URL is correctly configured
3. **Model Server**: Check if the model file exists and ports are available
4. **GPU Issues**: Adjust GPU_LAYERS if you encounter VRAM errors

### Debug Mode

Set `LOG_LEVEL=DEBUG` in `.env` for verbose logging.

### Logs

Check console output for detailed error messages and performance metrics.

## Example Usage

### Python Client

```python
import requests

response = requests.post("http://localhost:9000/v1/chat/completions", json={
    "messages": [
        {"role": "user", "content": "Explain quantum computing"}
    ],
    "temperature": 0.7,
    "max_tokens": 500,
    "session_id": "my-session"
})

result = response.json()
print(result["choices"][0]["message"]["content"])
```

### cURL

```bash
curl -X POST "http://localhost:9000/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -d '{
       "messages": [{"role": "user", "content": "Hello"}],
       "temperature": 0.7,
       "max_tokens": 100
     }'
```

## Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation as needed
4. Ensure all tests pass before submitting changes

## License

This project is part of your local AI infrastructure setup.