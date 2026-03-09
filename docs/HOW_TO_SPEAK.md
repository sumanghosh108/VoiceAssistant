# How to Speak with the Voice Assistant

Complete guide to interacting with your Real-Time Voice Assistant using voice.

## Quick Start

### Method 1: Web Interface (Easiest) 🌐

1. **Open the voice test page:**
   ```bash
   start voice_test.html
   ```
   Or double-click `voice_test.html` in File Explorer

2. **Click "Connect"** button

3. **Click the microphone button** 🎤

4. **Speak your question** (e.g., "Hello, how are you?")

5. **Click the microphone again** to stop recording

6. **Wait for the AI response**

---

### Method 2: Python Client 🐍

1. **Activate virtual environment:**
   ```bash
   .venv\Scripts\activate
   ```

2. **Run the example client:**
   ```bash
   python examples/voice_client.py --server ws://localhost:8000
   ```

3. **Follow the on-screen instructions**

---

## Detailed Instructions

### Using the Web Interface

#### Step 1: Make Sure Server is Running

Check if the server is running:
```bash
curl http://localhost:8001/health/live
```

Expected response: `{"status": "alive"}`

If not running, start it:
```bash
python -m src.main
```

#### Step 2: Open Voice Test Page

**Windows:**
```bash
start voice_test.html
```

**Or:** Double-click `voice_test.html` in File Explorer

#### Step 3: Grant Microphone Permission

When you first click the microphone button, your browser will ask:
```
localhost wants to use your microphone
[Block] [Allow]
```

**Click "Allow"** to enable voice input.

#### Step 4: Connect to Server

1. Click the **"Connect"** button
2. Wait for status to show: **"● Connected - Ready to speak"**
3. You should see: **"✓ Connected successfully!"**

#### Step 5: Start Speaking

1. **Click the microphone button** 🎤
2. Status changes to: **"🎤 Listening... (Click to stop)"**
3. **Speak clearly** into your microphone
4. Say something like:
   - "Hello, how are you?"
   - "What's the weather like?"
   - "Tell me a joke"
   - "What can you help me with?"

#### Step 6: Stop Recording

1. **Click the microphone button again** to stop
2. Status changes to: **"● Connected - Ready to speak"**
3. Your audio is being processed

#### Step 7: Receive Response

- The assistant will process your speech
- You'll see the transcript in the conversation area
- The AI response will be played back as audio
- The response text will appear in the transcript

---

## Using the Python Client

### Prerequisites

```bash
# Make sure you have pyaudio installed
pip install pyaudio

# If pyaudio installation fails on Windows:
pip install pipwin
pipwin install pyaudio
```

### Running the Client

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run the client
python examples/voice_client.py --server ws://localhost:8000
```

### Client Commands

Once the client is running:

- **Press SPACE** to start recording
- **Press SPACE again** to stop recording
- **Press Q** to quit
- **Press M** to mute/unmute audio output

---

## Troubleshooting

### "Microphone access denied"

**Solution:**
1. Check browser permissions
2. Go to browser settings → Privacy → Microphone
3. Allow microphone access for localhost
4. Refresh the page and try again

**Chrome:**
- Click the 🔒 icon in address bar
- Click "Site settings"
- Set Microphone to "Allow"

**Firefox:**
- Click the 🔒 icon in address bar
- Click "Connection secure" → "More information"
- Go to "Permissions" tab
- Check "Use the Microphone"

### "Connection failed"

**Check if server is running:**
```bash
curl http://localhost:8001/health/live
```

**If not running, start it:**
```bash
# Activate venv
.venv\Scripts\activate

# Start server
python -m src.main
```

### "No audio output"

**Check:**
1. Your speakers/headphones are connected
2. Volume is not muted
3. Audio output device is selected correctly
4. Try the test page: `voice_test.html`

### "WhisperClient.transcribe() requires OpenAI API integration"

~~This error means the Whisper API client needs to be fully implemented. The WebSocket connection is working, but the actual speech recognition needs to be completed.~~

**FIXED!** All API clients are now fully implemented and integrated.

**Current Status:**
- ✅ WebSocket connection: Working
- ✅ Audio streaming: Working
- ✅ Speech recognition: **FULLY IMPLEMENTED**
- ✅ LLM response: **FULLY IMPLEMENTED**
- ✅ Text-to-speech: **FULLY IMPLEMENTED**

**You can now speak with the assistant and get voice responses!**

---

## Audio Format Requirements

The voice assistant expects audio in the following format:

- **Sample Rate:** 16,000 Hz (16 kHz)
- **Channels:** 1 (Mono)
- **Bit Depth:** 16-bit PCM
- **Encoding:** Raw PCM or WebM

The web interface automatically converts your microphone input to the correct format.

---

## Testing Without Voice

If you want to test the system without speaking:

### 1. Test WebSocket Connection

```bash
start test_websocket.html
```

Click "Connect to WebSocket" to verify the connection works.

### 2. Test HTTP Endpoints

```bash
# Health check
curl http://localhost:8001/health/live

# Metrics
curl http://localhost:8001/metrics

# Dashboard
start http://localhost:8001/dashboard
```

### 3. Send Test Audio

You can send a test audio file:

```python
import websockets
import asyncio

async def send_audio():
    uri = "ws://localhost:8000"
    async with websockets.connect(uri) as websocket:
        # Read audio file
        with open("test_audio.wav", "rb") as f:
            audio_data = f.read()
        
        # Send audio
        await websocket.send(audio_data)
        
        # Wait for response
        response = await websocket.recv()
        print(f"Received: {response}")

asyncio.run(send_audio())
```

---

## Example Conversations

### Example 1: Simple Greeting

**You:** "Hello, how are you?"

**Assistant:** "Hello! I'm doing well, thank you for asking. How can I help you today?"

### Example 2: Ask a Question

**You:** "What's the weather like today?"

**Assistant:** "I don't have access to real-time weather data, but I can help you with other questions. What else would you like to know?"

### Example 3: Request Information

**You:** "Tell me about artificial intelligence"

**Assistant:** "Artificial intelligence is a branch of computer science that focuses on creating systems capable of performing tasks that typically require human intelligence..."

---

## Advanced Usage

### Custom Audio Settings

Edit `voice_test.html` to change audio settings:

```javascript
const stream = await navigator.mediaDevices.getUserMedia({ 
    audio: {
        channelCount: 1,        // Mono
        sampleRate: 16000,      // 16 kHz
        echoCancellation: true, // Remove echo
        noiseSuppression: true, // Remove background noise
        autoGainControl: true   // Normalize volume
    } 
});
```

### Recording to File

To save your conversation:

```javascript
// Add this to voice_test.html
const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
const audioUrl = URL.createObjectURL(audioBlob);
const a = document.createElement('a');
a.href = audioUrl;
a.download = 'recording.webm';
a.click();
```

---

## Next Steps

1. **Test the connection:** Open `voice_test.html`
2. **Grant microphone access:** Allow when prompted
3. **Start speaking:** Click the mic button and talk
4. **Check the logs:** See what's happening in the server logs

```bash
# View server logs
python scripts/view_logs.py

# Filter for errors
python scripts/view_logs.py --level error
```

---

## Files for Voice Interaction

- **`voice_test.html`** - Web interface for voice interaction
- **`test_websocket.html`** - Simple WebSocket connection test
- **`examples/voice_client.py`** - Python client for voice interaction
- **`HOW_TO_SPEAK.md`** - This guide

---

## Summary

✅ **Web Interface:** Open `voice_test.html` and click the mic button  
✅ **Python Client:** Run `python examples/voice_client.py`  
✅ **Test Connection:** Use `test_websocket.html`  
✅ **Check Status:** `curl http://localhost:8001/health/live`  

**Start speaking with your AI assistant now!** 🎤🤖
