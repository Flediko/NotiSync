package com.notisync.app;

import android.content.Intent;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "NotificationService")
public class NotificationServicePlugin extends Plugin {

    @PluginMethod
    public void startService(PluginCall call) {
        String serverUrl = call.getString("serverUrl");
        if (serverUrl == null || serverUrl.trim().isEmpty()) {
            call.reject("serverUrl is required");
            return;
        }

        try {
            Intent intent = new Intent(getContext(), NotificationForegroundService.class);
            intent.putExtra("serverUrl", serverUrl);
            
            // Android Oreo (API 26) and above requires startForegroundService
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                getContext().startForegroundService(intent);
            } else {
                getContext().startService(intent);
            }
            
            JSObject result = new JSObject();
            result.put("status", "started");
            call.resolve(result);
        } catch (Exception e) {
            call.reject("Failed to start service: " + e.getMessage());
        }
    }

    @PluginMethod
    public void stopService(PluginCall call) {
        try {
            Intent intent = new Intent(getContext(), NotificationForegroundService.class);
            getContext().stopService(intent);
            
            JSObject result = new JSObject();
            result.put("status", "stopped");
            call.resolve(result);
        } catch (Exception e) {
            call.reject("Failed to stop service: " + e.getMessage());
        }
    }
}
