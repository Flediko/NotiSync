import asyncio
import sys
from winrt.windows.ui.notifications.management import UserNotificationListener, UserNotificationListenerAccessStatus
from winrt.windows.ui.notifications import NotificationKinds

# Configure stdout to support UTF-8 characters (like emojis) without crashing
sys.stdout.reconfigure(encoding='utf-8')

async def main():
    listener = UserNotificationListener.current
    access_status = await listener.request_access_async()
    print(f"Access status: {access_status}")
    
    if access_status != UserNotificationListenerAccessStatus.ALLOWED:
        print("Access denied.")
        return
        
    print("Starting notification polling loop...")
    known_notifications = {}
    
    # Initialize with current active notifications
    initial_notifications = await listener.get_notifications_async(NotificationKinds.TOAST)
    for n in initial_notifications:
        try:
            app_name = n.app_info.display_info.display_name
            known_notifications[n.id] = app_name
        except Exception:
            known_notifications[n.id] = "Unknown App"
            
    print(f"Tracking {len(known_notifications)} existing notifications. Monitoring for updates...")
    
    # Poll for 15 seconds
    for _ in range(15):
        await asyncio.sleep(1)
        try:
            current_notifications = await listener.get_notifications_async(NotificationKinds.TOAST)
            current_ids = set()
            
            # Check for new notifications
            for n in current_notifications:
                nid = n.id
                current_ids.add(nid)
                if nid not in known_notifications:
                    # Found a new notification!
                    try:
                        app_name = n.app_info.display_info.display_name
                        visual = n.notification.visual
                        binding = visual.get_binding("ToastGeneric")
                        texts = []
                        if binding:
                            for text_element in binding.get_text_elements():
                                texts.append(text_element.text)
                        
                        known_notifications[nid] = app_name
                        print(f"\n[NEW] Notification from: {app_name} (ID: {nid})")
                        print(f"      Content: {texts}")
                    except Exception as e:
                        print(f"Error reading new notification details: {e}")
            
            # Check for dismissed notifications
            dismissed_ids = []
            for nid in list(known_notifications.keys()):
                if nid not in current_ids:
                    app_name = known_notifications[nid]
                    print(f"\n[DISMISSED] Notification from: {app_name} (ID: {nid})")
                    dismissed_ids.append(nid)
            
            for nid in dismissed_ids:
                del known_notifications[nid]
                
        except Exception as e:
            print(f"Error in polling loop: {e}")
            
    print("Done polling.")

if __name__ == "__main__":
    asyncio.run(main())
