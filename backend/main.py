"""FastAPI application entry point"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import configuration management
from .core.config import settings, get_logging_config, get_api_key

# Configure logging
logging_config = get_logging_config()
logging.basicConfig(
    level=getattr(logging, logging_config["level"]),
    format=logging_config["format"],
    handlers=[
        logging.StreamHandler(),  # Output to console
        logging.FileHandler(logging_config["file"])  # Output to file
    ]
)

logger = logging.getLogger(__name__)

# Use unified API route registration
from .api.v1 import api_router
from .core.database import engine
from .models.base import Base

# Create FastAPI app
app = FastAPI(
    title="AutoClip API",
    description="AI video clip processing API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Create database tables
@app.on_event("startup")
async def startup_event():
    logger.info("Starting AutoClip API service...")
    # Import all models to ensure tables are created
    from .models.bilibili import BilibiliAccount, UploadRecord
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Load API key into environment variables
    api_key = get_api_key()
    if api_key:
        import os
        os.environ["DASHSCOPE_API_KEY"] = api_key
        logger.info("API key loaded into environment variables")
    else:
        logger.warning("API key configuration not found")
    
    # WebSocket gateway service disabled - using new simplified progress system
    # from .services.websocket_gateway_service import websocket_gateway_service
    # await websocket_gateway_service.start()
    # logger.info("WebSocket gateway service started")
    logger.info("WebSocket gateway service disabled; using new simplified progress system")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down AutoClip API service...")
    # WebSocket gateway service disabled
    # from .services.websocket_gateway_service import websocket_gateway_service
    # await websocket_gateway_service.stop()
    # logger.info("WebSocket gateway service stopped")
    logger.info("WebSocket gateway service disabled")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include unified API routes
app.include_router(api_router, prefix="/api/v1")

# Standalone video-categories endpoint
@app.get("/api/v1/video-categories")
async def get_video_categories():
    """Get video category configuration."""
    return {
        "categories": [
            {
                "value": "default",
                "name": "Default",
                "description": "General video content processing",
                "icon": "🎬",
                "color": "#4facfe"
            },
            {
                "value": "knowledge",
                "name": "Knowledge & Education",
                "description": "Science, technology, history, culture, and other educational content",
                "icon": "📚",
                "color": "#52c41a"
            },
            {
                "value": "entertainment",
                "name": "Entertainment",
                "description": "Games, music, movies, and other entertainment content",
                "icon": "🎮",
                "color": "#722ed1"
            },
            {
                "value": "business",
                "name": "Business",
                "description": "Business, entrepreneurship, investment, and related content",
                "icon": "💼",
                "color": "#fa8c16"
            },
            {
                "value": "experience",
                "name": "Experience Sharing",
                "description": "Personal experiences, life insights, and similar content",
                "icon": "🌟",
                "color": "#eb2f96"
            },
            {
                "value": "opinion",
                "name": "Opinion & Commentary",
                "description": "Current events commentary, opinion analysis, and related content",
                "icon": "💭",
                "color": "#13c2c2"
            },
            {
                "value": "speech",
                "name": "Speech",
                "description": "Public speeches, lectures, and similar content",
                "icon": "🎤",
                "color": "#f5222d"
            }
        ]
    }

# Import unified error handling middleware
from .core.error_middleware import global_exception_handler

# Register global exception handler
app.add_exception_handler(Exception, global_exception_handler)

if __name__ == "__main__":
    import uvicorn
    import sys
    
    # Default port
    port = 8000
    
    # Check command-line arguments
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    logger.error(f"Invalid port number: {sys.argv[i + 1]}")
                    port = 8000
    
    logger.info(f"Starting server on port: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
