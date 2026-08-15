import asyncio
import logging
from datetime import datetime
from typing import Set, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from winrt.windows.ui.notifications.management import UserNotificationListener, UserNotificationListenerAccessStatus
from winrt.windows.ui.notifications import NotificationKinds

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NotiSync")

# WebSocket connections storage
active_connections: Set[WebSocket] = set()
# Memory storage of active notifications: {id: notification_dict}
active_notifications: Dict[int, dict] = {}
# Listener instance
listener = UserNotificationListener.current

def parse_notification(n) -> dict:
    """Parses a WinRT UserNotification object into a dictionary."""
    nid = n.id
    try:
        app_name = n.app_info.display_info.display_name
    except Exception:
        app_name = "Unknown App"
    
    title = ""
    body = ""
    try:
        visual = n.notification.visual
        binding = visual.get_binding("ToastGeneric")
        if binding:
            texts = [t.text for t in binding.get_text_elements()]
            if len(texts) > 0:
                title = texts[0]
            if len(texts) > 1:
                body = " ".join(texts[1:])
    except Exception as e:
        body = f"Error reading content: {e}"
        
    return {
        "id": nid,
        "app_name": app_name,
        "title": title or app_name,
        "body": body,
        "timestamp": datetime.now().strftime("%I:%M %p")
    }

async def broadcast(message: dict):
    """Sends a JSON message to all connected WebSocket clients."""
    if not active_connections:
        return
    disconnected = set()
    for websocket in active_connections:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send to client: {e}")
            disconnected.add(websocket)
    
    active_connections.difference_update(disconnected)

async def poll_notifications():
    """Background task that polls active Windows notifications."""
    global active_notifications
    logger.info("Initializing Notification Listener...")
    
    # Request access
    access_status = await listener.request_access_async()
    if access_status != UserNotificationListenerAccessStatus.ALLOWED:
        logger.error("Access to notifications was DENIED. Enable it in Windows Settings.")
        return
        
    logger.info("Notification Access Allowed. Starting polling loop...")
    
    # Initial load
    try:
        initial_list = await listener.get_notifications_async(NotificationKinds.TOAST)
        for n in initial_list:
            active_notifications[n.id] = parse_notification(n)
        logger.info(f"Loaded {len(active_notifications)} existing notifications.")
    except Exception as e:
        logger.error(f"Error loading initial notifications: {e}")
        
    while True:
        try:
            await asyncio.sleep(1) # Check every 1 second
            
            current_list = await listener.get_notifications_async(NotificationKinds.TOAST)
            current_ids = set()
            
            # Check for additions
            for n in current_list:
                nid = n.id
                current_ids.add(nid)
                if nid not in active_notifications:
                    parsed = parse_notification(n)
                    active_notifications[nid] = parsed
                    logger.info(f"New Notification: {parsed['app_name']} - {parsed['title']}")
                    # Broadcast to clients
                    await broadcast({
                        "type": "added",
                        "notification": parsed
                    })
            
            # Check for removals
            dismissed_ids = []
            for nid in list(active_notifications.keys()):
                if nid not in current_ids:
                    logger.info(f"Dismissed Notification ID: {nid}")
                    dismissed_ids.append(nid)
                    await broadcast({
                        "type": "removed",
                        "id": nid
                    })
            
            for nid in dismissed_ids:
                if nid in active_notifications:
                    del active_notifications[nid]
                    
        except asyncio.CancelledError:
            logger.info("Polling task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            await asyncio.sleep(5) # Backoff on error

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background notifications poll task
    polling_task = asyncio.create_task(poll_notifications())
    yield
    # Cleanup: cancel task
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="NotiSync Server", lifespan=lifespan)

# Mount static files folder
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    """Serves the main web dashboard."""
    return FileResponse("templates/index.html")

@app.get("/active_list")
async def get_active_list():
    """Returns the current list of active notifications."""
    return list(active_notifications.values())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for real-time sync and receiving dismiss instructions."""
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"Connected client: {websocket.client}")
    
    # Send existing notifications immediately
    try:
        await websocket.send_json({
            "type": "sync",
            "notifications": list(active_notifications.values())
        })
    except Exception as e:
        logger.error(f"Error syncing initial list to client: {e}")
        active_connections.discard(websocket)
        return

    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "dismiss":
                nid = data.get("id")
                if nid is not None:
                    logger.info(f"Request from client to dismiss notification ID: {nid}")
                    try:
                        # Remove from Windows Action Center
                        listener.remove_notification(nid)
                        # Remove from local dict
                        if nid in active_notifications:
                            del active_notifications[nid]
                        # Broadcast removal to other clients
                        await broadcast({
                            "type": "removed",
                            "id": nid
                        })
                    except Exception as e:
                        logger.error(f"Failed to dismiss notification {nid}: {e}")
    except WebSocketDisconnect:
        logger.info(f"Disconnected client: {websocket.client}")
    finally:
        active_connections.discard(websocket)
