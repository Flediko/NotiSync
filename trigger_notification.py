import subprocess
import time

print("Waiting 3 seconds before triggering notification...")
time.sleep(3)

ps_script = """
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$toastXml = [xml]$template.GetXml()
$toastXml.toast.visual.binding.text[0].InnerText = "Test Notification"
$toastXml.toast.visual.binding.text[1].InnerText = "This is a test notification generated from Python!"
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($toastXml.OuterXml)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("NotiSync").Show($toast)
"""

subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
print("Toast notification shown!")
