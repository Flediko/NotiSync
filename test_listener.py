import asyncio
import sys
# pyrefly: ignore [missing-import]
from winrt.windows.ui.notifications.management import UserNotificationListener, UserNotificationListenerAccessStatus
from winrt.windows.ui.notifications import NotificationKinds

# Configure stdout to support UTF-8 characters (like emojis) without crashing
sys.stdout.reconfigure(encoding='utf-8')

def on_notification_changed(listener, event_args):
    try:
        nid = event_args.user_notification_id
        change_type = event_args.change_kind # UserNotificationChangedKind enum
        print(f"\n[Event] Notification ID: {nid} changed. Change Kind: {change_type}")
        
        # If it was added, let's fetch the notification details
        # ChangeKind 0 is typically 'added', 1 is 'removed'
        # Let's try to get it. Note: if it's removed, get_notification(nid) might return None or raise an exception.
        if change_type == 0: # Added
            notification = listener.get_notification(nid)
            if notification:
                app_name = notification.app_info.display_info.display_name
                visual = notification.notification.visual
                binding = visual.get_binding("ToastGeneric")
                texts = []
                if binding:
                    for text_element in binding.get_text_elements():
                        texts.append(text_element.text)
                print(f"  --> NEW Notification from {app_name}: {texts}")
            else:
                print(f"  --> Could not retrieve notification {nid} details (might have been dismissed already)")
        elif change_type == 1: # Removed
            print(f"  --> Notification {nid} was removed/dismissed.")
    except Exception as e:
        print(f"Error handling event: {e}")

async def main():
    listener = UserNotificationListener.current
    access_status = await listener.request_access_async()
    print(f"Access status: {access_status}")
    
    if access_status == UserNotificationListenerAccessStatus.ALLOWED:
        print("Registering notification event listener...")
        token = listener.add_notification_changed(on_notification_changed)
        print("Listening for changes for 15 seconds... Please trigger a notification if you can.")
        await asyncio.sleep(15)
        print("Removing listener...")
        listener.remove_notification_changed(token)
        print("Done.")
    else:
        print("Access denied.")

if __name__ == "__main__":
    asyncio.run(main())
