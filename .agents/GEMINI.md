# NotiSync - Workspace Customization & Memory Map

This file contains the context, project mapping, and technical rules for the **NotiSync** application.

---

## 📋 Project Status Summary
NotiSync is a fully functional Windows-to-Mobile notification sync application. 
- **Backend:** FastAPI + Uvicorn server polling Windows notifications via the WinRT API.
- **Frontend:** Installable PWA with dark glassmorphic UI, live WebSocket updates, sound alerts, detail inspector modals, and an in-app QR scanner.
- **Capacitor Mobile App:** Wrapped native Android app using Capacitor to build an installable APK. Includes a persistent Java Foreground Service that runs an OkHttp WebSocket client, waking up the phone in the background to show notifications natively.
- **Tunnels:** Integrates with `localhost.run` SSH tunneling to allow internet access (e.g. from college).
- **Launcher:** Double-clickable Windows Batch launcher `start_notisync.bat` for one-click startup.

---

## 🗺️ File Directory Map

- [`main.py`](file:///c:/Users/aakas/OneDrive/Desktop/noti/main.py): FastAPI app, handles background polling loop of `UserNotificationListener` every 1s, maintains active notifications in-memory, exposes HTTP `/active_list` and WebSockets `/ws` endpoints for sync/dismiss commands.
- [`run.py`](file:///c:/Users/aakas/OneDrive/Desktop/noti/run.py): Detects local IP, prints terminal QR code. Spawns background thread for uvicorn + SSH tunnel process to `localhost.run` to parse and extract the public HTTPS address.
- [`start_notisync.bat`](file:///c:/Users/aakas/OneDrive/Desktop/noti/start_notisync.bat): Launcher file executing run.py within the active virtual environment.
- [`templates/index.html`](file:///c:/Users/aakas/OneDrive/Desktop/noti/templates/index.html): HTML structure with metadata for Apple/Android PWA standalone installations and the `html5-qrcode` scanner. Updated theme-color meta tag to `#00f0ff`.
- [`static/app.js`](file:///c:/Users/aakas/OneDrive/Desktop/noti/static/app.js): JS client implementing DOM diffing renderer (prevents flashing), synthesized bell tone chimes, and camera QR scanning redirects. Connects to Capacitor native plugin `NotificationService` to start/stop the background client.
- [`static/style.css`](file:///c:/Users/aakas/OneDrive/Desktop/noti/static/style.css): Overhauled to a vibrant **Electric Cyber-Cyan and Emerald Green** theme. Glassmorphic elements, scale transforms, neon pointer glows, and modal overlays.
- [`build_capacitor.py`](file:///c:/Users/aakas/OneDrive/Desktop/noti/build_capacitor.py): Python builder script that cleans and bundles web assets (`templates/`, `static/`) into Capacitor's distribution folder (`www/`).
- [`android/app/src/main/AndroidManifest.xml`](file:///c:/Users/aakas/OneDrive/Desktop/noti/android/app/src/main/AndroidManifest.xml): Declares service runtime permissions (`FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_DATA_SYNC`, `POST_NOTIFICATIONS`) and allows cleartext HTTP/WS local connections.
- [`android/app/src/main/java/com/notisync/app/NotificationForegroundService.java`](file:///c:/Users/aakas/OneDrive/Desktop/noti/android/app/src/main/java/com/notisync/app/NotificationForegroundService.java): Java service running in the background, utilizing OkHttp WebSockets to capture alerts and post/remove native Android notifications drawer items.
- [`android/app/src/main/java/com/notisync/app/NotificationServicePlugin.java`](file:///c:/Users/aakas/OneDrive/Desktop/noti/android/app/src/main/java/com/notisync/app/NotificationServicePlugin.java): Capacitor JS-to-Java plugin bridge to start/stop the foreground service.

---

## ⚙️ Development Guidelines for Future Agents

1. **Virtual Environment:**
   Always use the local virtual environment `.venv` inside the project root directory. Do NOT run global `pip install`. Install new packages using:
   ```powershell
   .venv\Scripts\pip install <package>
   ```
2. **WebSocket Package Dependency:**
   FastAPI requires `websockets` (installed) to run the `/ws` endpoint correctly. Verify its installation when debugging connection issues.
3. **Java SDK & Gradle Build version (CRITICAL):**
   - Gradle 8.2.1 is used for Android native builds. This Gradle version is **incompatible** with Java versions newer than Java 20 (it will crash with `Unsupported class file major version` script compiler errors).
   - Ensure the project always compiles using **Java 17** (e.g. Eclipse Temurin 17 JDK).
   - Always verify that the path to the Java 17 home directory is configured inside `android/gradle.properties`:
     `org.gradle.java.home=C:\\Program Files\\Eclipse Adoptium\\jdk-17.0.20.8-hotspot`
   - If Java compilation cache errors occur, stop active daemons and clear the script cache:
     ```cmd
     gradlew --stop
     rmdir /s /q C:\Users\aakas\.gradle\caches
     ```
4. **Rendering Strategy (Anti-Flickering):**
   Do NOT clear the DOM container (`innerHTML = ''`) during updates. Instead, use the DOM Diffing engine implemented in `static/app.js` to insert/remove elements at their indices to maintain layout and transition animations smoothly.
5. **Dismissal Glitch Prevention:**
   When dismissing a notification card:
   - Filter the local memory state array `notifications` **instantly** on click.
   - Only remove the DOM node from the layout at the end of the slide-out animation via `animationend`. This prevents race conditions where standard re-renders attempt to redraw a card that is half-dismissed.

