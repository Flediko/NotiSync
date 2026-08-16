package com.notisync.app;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import androidx.core.app.NotificationCompat;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

import org.json.JSONObject;

import java.util.concurrent.TimeUnit;

public class NotificationForegroundService extends Service {
    private static final String SERVICE_CHANNEL_ID = "notisync_service";
    private static final String ALERTS_CHANNEL_ID = "notisync_alerts";
    private static final int SERVICE_NOTIFICATION_ID = 1;
    private static final int ANTIGRAVITY_NOTIFICATION_ID = 9999;

    private final java.util.Set<Integer> activeAntigravityIds = new java.util.HashSet<>();
    private String serverUrl = "";
    private OkHttpClient okHttpClient;
    private WebSocket webSocket;
    private final Handler reconnectHandler = new Handler(Looper.getMainLooper());
    private boolean isDestroyed = false;

    private final Runnable reconnectRunnable = new Runnable() {
        @Override
        public void run() {
            if (!isDestroyed) {
                android.util.Log.i("NotiSyncService", "Attempting WebSocket Reconnect...");
                connectWebSocket();
            }
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        okHttpClient = new OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(0, TimeUnit.MILLISECONDS) // infinite read timeout for WebSockets
                .build();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && intent.hasExtra("serverUrl")) {
            String url = intent.getStringExtra("serverUrl");
            if (url != null && !url.trim().isEmpty() && !url.equals(serverUrl)) {
                serverUrl = url;
                android.util.Log.i("NotiSyncService", "Updating server URL to: " + serverUrl);
                disconnectWebSocket();
                connectWebSocket();
            }
        }
        
        startForegroundWithNotification();
        return START_STICKY;
    }

    private void startForegroundWithNotification() {
        NotificationManager notificationManager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (notificationManager == null) return;

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    SERVICE_CHANNEL_ID,
                    "NotiSync Service Status",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Keeps NotiSync connected to your laptop in the background");
            notificationManager.createNotificationChannel(channel);
        }

        // Tap the status notification to open app
        Intent intent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this,
                0,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, SERVICE_CHANNEL_ID)
                .setSmallIcon(getApplicationInfo().icon)
                .setContentTitle("NotiSync Active")
                .setContentText("Connected to laptop in the background")
                .setContentIntent(pendingIntent)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setOngoing(true);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(SERVICE_NOTIFICATION_ID, builder.build(), ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
        } else {
            startForeground(SERVICE_NOTIFICATION_ID, builder.build());
        }
    }

    private synchronized void connectWebSocket() {
        if (serverUrl == null || serverUrl.trim().isEmpty() || isDestroyed) return;
        if (webSocket != null) return;

        // Convert serverUrl to WebSocket protocol ws:// or wss://
        String wsUrl = serverUrl.replace("http://", "ws://").replace("https://", "wss://");
        if (!wsUrl.endsWith("/ws")) {
            wsUrl = wsUrl.replaceAll("/+$", "") + "/ws";
        }

        android.util.Log.i("NotiSyncService", "Connecting WebSocket to: " + wsUrl);
        Request request = new Request.Builder().url(wsUrl).build();

        webSocket = okHttpClient.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onOpen(WebSocket ws, Response response) {
                android.util.Log.i("NotiSyncService", "WebSocket Connection Opened successfully.");
                reconnectHandler.removeCallbacks(reconnectRunnable);
            }

            @Override
            public void onMessage(WebSocket ws, String text) {
                android.util.Log.i("NotiSyncService", "Received Message: " + text);
                try {
                    JSONObject json = new JSONObject(text);
                    String type = json.optString("type");

                    if ("added".equals(type)) {
                        JSONObject n = json.getJSONObject("notification");
                        int id = n.getInt("id");
                        String appName = n.optString("app_name", "Unknown App");
                        String title = n.optString("title", "");
                        String body = n.optString("body", "");
                        showNativeNotification(id, appName, title, body);
                    } else if ("removed".equals(type)) {
                        int id = json.getInt("id");
                        cancelNativeNotification(id);
                    }
                } catch (Exception e) {
                    android.util.Log.e("NotiSyncService", "Error parsing incoming JSON: " + e.getMessage());
                }
            }

            @Override
            public void onClosed(WebSocket ws, int code, String reason) {
                android.util.Log.w("NotiSyncService", "WebSocket Closed. Code: " + code + ", Reason: " + reason);
                webSocket = null;
                scheduleReconnect();
            }

            @Override
            public void onFailure(WebSocket ws, Throwable t, Response response) {
                android.util.Log.e("NotiSyncService", "WebSocket Failure: " + t.getMessage());
                webSocket = null;
                scheduleReconnect();
            }
        });
    }

    private void scheduleReconnect() {
        if (isDestroyed) return;
        reconnectHandler.removeCallbacks(reconnectRunnable);
        reconnectHandler.postDelayed(reconnectRunnable, 5000); // Retry in 5 seconds
    }

    private void disconnectWebSocket() {
        reconnectHandler.removeCallbacks(reconnectRunnable);
        if (webSocket != null) {
            webSocket.close(1000, "Service configuration updated");
            webSocket = null;
        }
    }

    private void showNativeNotification(int id, String appName, String title, String body) {
        NotificationManager notificationManager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (notificationManager == null) return;

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    ALERTS_CHANNEL_ID,
                    "Synced Alerts",
                    NotificationManager.IMPORTANCE_HIGH
            );
            channel.setDescription("Notifications synced from your Windows laptop");
            notificationManager.createNotificationChannel(channel);
        }

        boolean isAntigravity = (appName != null && appName.toLowerCase().contains("antigravity"));
        int targetId = id;
        Intent intent = null;

        if (isAntigravity) {
            synchronized (activeAntigravityIds) {
                activeAntigravityIds.add(id);
            }
            targetId = ANTIGRAVITY_NOTIFICATION_ID;
            intent = getPackageManager().getLaunchIntentForPackage("com.google.chromeremotedesktop");
            if (intent != null) {
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            }
        }

        if (intent == null) {
            intent = new Intent(this, MainActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        }

        PendingIntent pendingIntent = PendingIntent.getActivity(
                this,
                targetId,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, ALERTS_CHANNEL_ID)
                .setSmallIcon(getApplicationInfo().icon)
                .setContentTitle(title)
                .setContentText(body)
                .setSubText(appName)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setContentIntent(pendingIntent)
                .setAutoCancel(true);

        if (isAntigravity) {
            Intent crdIntent = getPackageManager().getLaunchIntentForPackage("com.google.chromeremotedesktop");
            if (crdIntent != null) {
                crdIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
                PendingIntent crdPendingIntent = PendingIntent.getActivity(
                        this,
                        targetId + 1,
                        crdIntent,
                        PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                );
                builder.addAction(0, "Open Remote Desktop", crdPendingIntent);
            }
        }

        notificationManager.notify(targetId, builder.build());
    }

    private void cancelNativeNotification(int id) {
        NotificationManager notificationManager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (notificationManager != null) {
            boolean isAntigravity = false;
            synchronized (activeAntigravityIds) {
                if (activeAntigravityIds.contains(id)) {
                    isAntigravity = true;
                    activeAntigravityIds.remove(id);
                }
            }
            if (isAntigravity) {
                notificationManager.cancel(ANTIGRAVITY_NOTIFICATION_ID);
            } else {
                notificationManager.cancel(id);
            }
        }
    }

    @Override
    public void onDestroy() {
        isDestroyed = true;
        disconnectWebSocket();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null; // Not a bound service
    }
}
