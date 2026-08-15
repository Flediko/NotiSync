import asyncio
from winrt.windows.ui.notifications.management import UserNotificationListener, UserNotificationListenerAccessStatus
from winrt.windows.ui.notifications import NotificationKinds

async def main():
    listener = UserNotificationListener.current
    access_status = await listener.request_access_async()
    if access_status != UserNotificationListenerAccessStatus.ALLOWED:
        print("Access denied.")
        return
        
    notifications = await listener.get_notifications_async(NotificationKinds.TOAST)
    if not notifications:
        print("No active notifications to dismiss.")
        return
        
    # Pick the first notification
    target = notifications[0]
    app_name = target.app_info.display_info.display_name
    nid = target.id
    
    print(f"Attempting to dismiss notification {nid} from {app_name}...")
    try:
        listener.remove_notification(nid)
        print("Dismiss method executed! Check if notification is gone.")
    except Exception as e:
        print(f"Error dismissing notification: {e}")

if __name__ == "__main__":
    asyncio.run(main())
