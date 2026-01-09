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

2. Update `index.html` with your app credentials:

```javascript
var APP_KEY = "YOUR_APP_KEY";
var APP_ID = "YOUR_APP_ID";
var APP_SECRET = "YOUR_APP_SECRET";

var pushi = new Pushi(APP_KEY, {
    baseUrl: "ws://localhost:9090/",
    baseWebUrl: "http://localhost:8080/",
    appId: APP_ID,
    appSecret: APP_SECRET
});
```

3. Start the Pushi server:

```bash
python -m pushi.app
```

4. Access the example from the Pushi server (recommended to avoid CORS issues):

```text
http://localhost:8080/static/examples/web-push/index.html
```

## Sending Notifications

Use the Python `notify.py` script to trigger events:

```bash
python examples/base/notify.py
```
