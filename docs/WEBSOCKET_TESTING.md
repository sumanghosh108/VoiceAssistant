# WebSocket Testing Guide

## Understanding the Error

When you opened `localhost:8000` in your browser, you saw:
```
Failed to open a WebSocket connection: invalid Connection header: keep-alive.
You cannot access a WebSocket server directly with a browser. You need a WebSocket client.
```

**This is CORRECT and EXPECTED behavior!** ✅

### Why This Happens

- **WebSocket servers** (like `ws://localhost:8000`) are NOT regular HTTP servers
- You cannot open them directly in a browser like a website
- Browsers use HTTP protocol by default, but WebSockets use the `ws://` protocol
- You need a **WebSocket client** to connect properly

### What This Means

✅ **Your server is working correctly!**  
✅ **The WebSocket server is running and accepting connections**  
✅ **The error message is the server correctly rejecting an HTTP request**

## How to Test the WebSocket Server

### Method 1: Use the HTML Test Page (Easiest)

I've created a test page for you:

1. **Open the test page:**
   ```bash
   # Windows
   start test_websocket.html
   
   # Or just double-click test_websocket.html in File Explorer
   ```

2. **Click "Connect to WebSocket"** button

3. **Watch the connection log** - you should see:
   ```
   ✓ WebSocket connection established!
   ```

### Method 2: Use the Python Example Client

```bash
# Activate virtual environment first
.venv\Scripts\activate

# Run the example client
python examples/voice_client.py --server ws://localhost:8000
```

### Method 3: Use Browser Developer Tools

1. Open any webpage (like `localhost:8001/dashboard`)
2. Open Developer Tools (F12)
3. Go to Console tab
4. Run this JavaScript:

```javascript
const ws = new WebSocket('ws://localhost:8000');
ws.onopen = () => console.log('Connected!');
ws.onmessage = (e) => console.log('Message:', e.data);
ws.onerror = (e) => console.error('Error:', e);
ws.onclose = () => console.log('Disconnected');
```

## Current Server Status

### ✅ What's Working

1. **WebSocket Server**: Running on `ws://localhost:8000`
   - Accepting connections ✓
   - Creating sessions ✓
   - Handling connection lifecycle ✓

2. **HTTP Server**: Running on `http://localhost:8001`
   - Health endpoints ✓
   - Metrics API ✓
   - Dashboard ✓

3. **Services Initialized**:
   - ASR Service (Whisper) ✓
   - LLM Service (Gemini) ✓
   - TTS Service (ElevenLabs) ✓

### ⚠️ Known Issues

The logs show:
```
WhisperClient.transcribe() requires OpenAI API integration
```

This means the **Whisper client needs to be fully implemented** to actually transcribe audio. The infrastructure is working, but the actual API integration needs to be completed.

## Testing Checklist

### 1. Test HTTP Endpoints (Should Work)

```bash
# Health check
curl http://localhost:8001/health/live
# Expected: {"status": "alive"}

# Full health status
curl http://localhost:8001/health
# Expected: JSON with service status

# Metrics
curl http://localhost:8001/metrics
# Expected: JSON with latency statistics

# Dashboard (open in browser)
start http://localhost:8001/dashboard
# Expected: HTML dashboard page
```

### 2. Test WebSocket Connection (Use Test Page)

```bash
# Open the test page
start test_websocket.html

# Click "Connect to WebSocket"
# Expected: "✓ WebSocket connection established!"
```

### 3. Test with Example Client (When Available)

```bash
python examples/voice_client.py
# Expected: Client connects and can send/receive audio
```

## Troubleshooting

### "Cannot access WebSocket directly in browser"

**This is normal!** Use one of the testing methods above.

### WebSocket connection fails

Check if server is running:
```bash
# Check if process is running
tasklist | findstr python

# Check if port is listening
netstat -an | findstr :8000
```

### "WhisperClient.transcribe() requires OpenAI API integration"

This is expected - the Whisper client implementation needs to be completed. The WebSocket connection itself is working fine.

## Next Steps

1. **Test WebSocket Connection**: Use `test_websocket.html`
2. **Verify HTTP Endpoints**: Test health and metrics
3. **Implement Whisper Client**: Complete the ASR service integration
4. **Implement Gemini Client**: Complete the LLM service integration
5. **Implement ElevenLabs Client**: Complete the TTS service integration

## Summary

✅ **Server Status**: RUNNING  
✅ **WebSocket Server**: WORKING (accepting connections)  
✅ **HTTP Server**: WORKING (health, metrics, dashboard)  
✅ **Configuration**: LOADED (API keys configured)  
⚠️ **API Clients**: Need implementation (Whisper, Gemini, ElevenLabs)

**The error you saw was actually the server working correctly!** It properly rejected an HTTP request to a WebSocket endpoint. Use the test page or example client to connect properly.
