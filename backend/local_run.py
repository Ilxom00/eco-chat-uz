"""
eco-chat.uz — Local Run Entry Point (Docker'siz)
SQLite + in-memory cache
"""
import local_config  # Override env vars BEFORE any other imports

# Now import the app (it will read the overridden env vars)
from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "local_run:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
