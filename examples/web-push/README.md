# Web Push Example

Simple example demonstrating Web Push notifications with Pushi.

## Files

* `index.html` - Browser client with subscribe/unsubscribe buttons
* `sw.js` - Service worker for displaying notifications
* `client.py` - Python client example

## Setup

1. Configure your Pushi server with VAPID credentials:

```text
vapid_key: <your-vapid-private-key>
vapid_email: mailto:your@email.com
```

2. Update `index.html` with your app key and server URLs:

```javascript
var APP_KEY = "YOUR_APP_KEY";
var pushi = new Pushi(APP_KEY, {
    baseUrl: "wss://your-server:9090/",
    baseWebUrl: "http://your-server:8080/"
});
```

3. Start the Pushi server with CORS enabled:

```bash
CORS=1 python -m pushi.app
```

4. Serve the example files (localhost works for service workers):

```bash
python -m http.server 8181 --directory .
```

5. Open `http://localhost:8181/examples/web-push/` in your browser and click "Enable Notifications".

## Sending Notifications

Use the Python client to trigger events:

```python
import pushi

api = pushi.API(
    app_id="YOUR_APP_ID",
    app_key="YOUR_APP_KEY",
    app_secret="YOUR_APP_SECRET",
    base_url="https://your-server:8080/"
)

api.trigger_event("notifications", {
    "title": "Hello!",
    "body": "This is a push notification"
})
```
