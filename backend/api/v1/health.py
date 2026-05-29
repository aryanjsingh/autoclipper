"""
Health check API routes
"""

from fastapi import APIRouter
from datetime import datetime
from typing import Dict, Any

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@router.get("/video-categories")
async def get_video_categories() -> Dict[str, Any]:
    """Get video category configuration."""
    return {
        "categories": [
            {
                "value": "knowledge",
                "name": "Knowledge & Science",
                "description": "Science, technology, history, culture and other knowledge content",
                "icon": "book",
                "color": "#1890ff"
            },
            {
                "value": "entertainment", 
                "name": "Entertainment & Leisure",
                "description": "Games, music, movies, variety shows and other entertainment content",
                "icon": "play-circle",
                "color": "#52c41a"
            },
            {
                "value": "experience",
                "name": "Life Experience",
                "description": "Life tips, food, travel, crafts and other practical content",
                "icon": "heart",
                "color": "#fa8c16"
            },
            {
                "value": "opinion",
                "name": "Opinions & Commentary",
                "description": "Current events commentary, opinion sharing, social topics, etc.",
                "icon": "message",
                "color": "#722ed1"
            },
            {
                "value": "business",
                "name": "Business & Finance",
                "description": "Business analysis, financial news, investment management, etc.",
                "icon": "dollar",
                "color": "#13c2c2"
            },
            {
                "value": "speech",
                "name": "Speeches & Interviews",
                "description": "Speeches, interviews, conversations and other spoken content",
                "icon": "sound",
                "color": "#eb2f96"
            }
        ],
        "default_category": "knowledge"
    } 