"""
WebSocket API routes
"""

import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.websocket_manager import manager, WebSocketMessage
from ...services.websocket_notification_service import WebSocketNotificationService
from ...services.websocket_gateway_service import websocket_gateway_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket connection endpoint"""
    await manager.connect(websocket, user_id)
    
    try:
        # Send connection confirmation message
        welcome_message = WebSocketMessage.create_system_notification(
            "connection",
            "Connection successful",
            f"User {user_id} successfully connected to WebSocket service",
            "success"
        )
        await manager.send_personal_message(welcome_message, user_id)
        
        # Handle client messages - keep alive loop
        while True:
            try:
                # Receive client message
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                await handle_client_message(user_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"User {user_id} disconnected voluntarily")
                break
            except json.JSONDecodeError:
                logger.error(f"User {user_id} sent malformed message")
                try:
                    error_message = WebSocketMessage.create_error_notification(
                        "message_format_error",
                        "Message format error",
                        {"message": "Please send a valid JSON format message"}
                    )
                    await manager.send_personal_message(error_message, user_id)
                except:
                    # If send fails, connection is broken, exit directly
                    break
            except Exception as e:
                logger.error(f"Error processing message from user {user_id}: {e}")
                try:
                    error_message = WebSocketMessage.create_error_notification(
                        "processing_error",
                        "Message processing error",
                        {"error": str(e)}
                    )
                    await manager.send_personal_message(error_message, user_id)
                except:
                    # If send fails, connection is broken, exit directly
                    break
    
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        # Clean up in order: unsubscribe first, then disconnect
        try:
            await websocket_gateway_service.unsubscribe_user_from_all_tasks(user_id)
        except Exception as e:
            logger.error(f"Failed to clean up user subscriptions: {e}")
        
        try:
            await manager.disconnect(user_id)
        except Exception as e:
            logger.error(f"Failed to disconnect user: {e}")

async def handle_client_message(user_id: str, message: Dict[str, Any]):
    """Handle client messages"""
    message_type = message.get("type")
    
    if message_type == "sync_subscriptions":
        # New idempotent subscription method
        project_ids = message.get("project_ids", [])
        # Pass project IDs directly, let gateway service normalize internally
        channels = set(project_ids)
        
        stats = await websocket_gateway_service.sync_user_subscriptions(user_id, channels)
        
        response = WebSocketMessage.create_system_notification(
            "subscription_sync",
            "Subscription sync completed",
            f"Added {stats['added']} / Removed {stats['removed']} / Unchanged {stats['unchanged']}",
            "success"
        )
        await manager.send_personal_message(response, user_id)
        
    elif message_type == "subscribe":
        # Subscribe to topic (legacy compatible)
        topic = message.get("topic")
        if topic:
            manager.subscribe_to_topic(user_id, topic)
            response = WebSocketMessage.create_system_notification(
                "subscription",
                "Subscription successful",
                f"Successfully subscribed to topic: {topic}",
                "success"
            )
            await manager.send_personal_message(response, user_id)
    
    elif message_type == "subscribe_task":
        # Subscribe to task progress (new version)
        task_id = message.get("task_id")
        if task_id:
            success = await websocket_gateway_service.subscribe_user_to_task(user_id, task_id)
            if success:
                response = WebSocketMessage.create_system_notification(
                    "task_subscription",
                    "Task subscription successful",
                    f"Successfully subscribed to progress updates for task {task_id}",
                    "success"
                )
            else:
                response = WebSocketMessage.create_error_notification(
                    "task_subscription_failed",
                    "Task subscription failed",
                    {"task_id": task_id}
                )
            await manager.send_personal_message(response, user_id)
    
    elif message_type == "unsubscribe":
        # Unsubscribe from topic (legacy compatible)
        topic = message.get("topic")
        if topic:
            manager.unsubscribe_from_topic(user_id, topic)
            response = WebSocketMessage.create_system_notification(
                "unsubscription",
                "Unsubscription successful",
                f"Unsubscribed from topic: {topic}",
                "info"
            )
            await manager.send_personal_message(response, user_id)
    
    elif message_type == "unsubscribe_task":
        # Unsubscribe from task progress (new version)
        task_id = message.get("task_id")
        if task_id:
            success = await websocket_gateway_service.unsubscribe_user_from_task(user_id, task_id)
            if success:
                response = WebSocketMessage.create_system_notification(
                    "task_unsubscription",
                    "Task unsubscription successful",
                    f"Unsubscribed from progress updates for task {task_id}",
                    "info"
                )
            else:
                response = WebSocketMessage.create_error_notification(
                    "task_unsubscription_failed",
                    "Task unsubscription failed",
                    {"task_id": task_id}
                )
            await manager.send_personal_message(response, user_id)
    
    elif message_type == "subscribe_many":
        # Batch subscribe to tasks
        task_ids = message.get("channels", [])
        if task_ids:
            results = await websocket_gateway_service.subscribe_user_to_many_tasks(user_id, task_ids)
            response = WebSocketMessage.create_system_notification(
                "batch_subscription",
                "Batch subscription completed",
                f"New subscriptions: {len(results['added'])}, Already existed: {len(results['already_subscribed'])}",
                "success"
            )
            await manager.send_personal_message(response, user_id)
    
    elif message_type == "unsubscribe_many":
        # Batch unsubscribe from tasks
        task_ids = message.get("channels", [])
        if task_ids:
            results = await websocket_gateway_service.unsubscribe_user_from_many_tasks(user_id, task_ids)
            response = WebSocketMessage.create_system_notification(
                "batch_unsubscription",
                "Batch unsubscription completed",
                f"Removed subscriptions: {len(results['removed'])}, Not subscribed: {len(results['not_subscribed'])}",
                "success"
            )
            await manager.send_personal_message(response, user_id)
    
    elif message_type == "sync_subscriptions":
        # Sync subscription set alignment
        task_ids = message.get("channels", [])
        results = await websocket_gateway_service.sync_user_subscriptions(user_id, task_ids)
        response = WebSocketMessage.create_system_notification(
            "subscription_sync",
            "Subscription set sync completed",
            f"Added: {len(results['added'])}, Removed: {len(results['removed'])}, Unchanged: {len(results['unchanged'])}",
            "success"
        )
        await manager.send_personal_message(response, user_id)
    
    elif message_type == "ping":
        # Heartbeat check
        response = {
            "type": "pong",
            "timestamp": WebSocketMessage.create_system_notification(
                "ping", "", "", "info"
            )["timestamp"]
        }
        await manager.send_personal_message(response, user_id)
        logger.debug(f"User {user_id} heartbeat check - pong replied")
    
    elif message_type == "get_status":
        # Get connection status
        gateway_status = await websocket_gateway_service.get_subscription_status(user_id)
        status = {
            "type": "status",
            "user_id": user_id,
            "connected": user_id in manager.active_connections,
            "subscriptions": list(manager.user_subscriptions.get(user_id, set())),
            "task_subscriptions": gateway_status["subscribed_tasks"],
            "total_connections": manager.get_connection_count(),
            "timestamp": WebSocketMessage.create_system_notification(
                "status", "", "", "info"
            )["timestamp"]
        }
        await manager.send_personal_message(status, user_id)
    
    else:
        # Unknown message type
        error_message = WebSocketMessage.create_error_notification(
            "unknown_message_type",
            "Unknown message type",
            {"message_type": message_type, "supported_types": ["subscribe", "subscribe_task", "unsubscribe", "unsubscribe_task", "ping", "get_status"]}
        )
        await manager.send_personal_message(error_message, user_id)

@router.get("/ws/status")
async def get_websocket_status():
    """Get WebSocket service status"""
    return {
        "status": "running",
        "total_connections": manager.get_connection_count(),
        "topics": {
            topic: manager.get_topic_subscriber_count(topic)
            for topic in manager.topic_subscribers
        }
    }

@router.post("/ws/broadcast")
async def broadcast_message(message: Dict[str, Any]):
    """Broadcast message to all connected users"""
    try:
        await manager.broadcast(message)
        return {"status": "success", "message": "Message broadcast successful"}
    except Exception as e:
        logger.error(f"Failed to broadcast message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to broadcast message: {e}")

@router.post("/ws/broadcast/{topic}")
async def broadcast_to_topic(topic: str, message: Dict[str, Any]):
    """Broadcast message to subscribers of a specific topic"""
    try:
        await manager.broadcast_to_topic(message, topic)
        return {"status": "success", "message": f"Message broadcast to subscribers of topic {topic}"}
    except Exception as e:
        logger.error(f"Failed to broadcast message to topic {topic}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to broadcast message: {e}")

@router.post("/ws/send/{user_id}")
async def send_to_user(user_id: str, message: Dict[str, Any]):
    """Send message to a specific user"""
    try:
        await manager.send_personal_message(message, user_id)
        return {"status": "success", "message": f"Message sent to user {user_id}"}
    except Exception as e:
        logger.error(f"Failed to send message to user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {e}")
