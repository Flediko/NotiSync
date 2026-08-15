import asyncio
import sys
from winrt.windows.ui.notifications.management import UserNotificationListener, UserNotificationListenerAccessStatus
from winrt.windows.ui.notifications import NotificationKinds
async def main():
    listener = UserNotificationListener.current
    
    print("Requesting notification listener access...")
    # request_access_async returns a UserNotificationListenerAccessStatus enum
    access_status = await listener.request_access_async()
    print(f"Access status: {access_status}")
    
    if access_status == UserNotificationListenerAccessStatus.ALLOWED:
        print("Access granted! Fetching notifications...")
        notifications = await listener.get_notifications_async(NotificationKinds.TOAST)
        print(f"Total active notifications: {len(notifications)}")
        for idx, n in enumerate(notifications):
            try:
                app_name = n.app_info.display_info.display_name
                # Get notification details
                visual = n.notification.visual
                binding = visual.get_binding("ToastGeneric")
                texts = []
                if binding:
                    for text_element in binding.get_text_elements():
                        texts.append(text_element.text)
                
                print(f"{idx + 1}. App: {app_name} | ID: {n.id}")
                print(f"   Texts: {texts}")
            except Exception as e:
                print(f"{idx + 1}. Error reading notification: {e}")
    elif access_status == UserNotificationListenerAccessStatus.DENIED:
        print("Access denied. Please check your Windows privacy settings under Settings > Privacy & Security > Notifications.")
    else:
        print("Access state is unspecified.")

if __name__ == "__main__":
    asyncio.run(main())
