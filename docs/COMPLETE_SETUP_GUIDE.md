# Complete Setup and Usage Guide

## Real-Time Voice Assistant - Full Working Process

This guide provides step-by-step instructions for setting up and using the Real-Time Voice Assistant with Groq Whisper API, OpenRouter LLM, and ElevenLabs TTS.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Using the Voice Assistant](#using-the-voice-assistant)
7. [Architecture](#architecture)
8. [Troubleshooting](#troubleshooting)
9. [API Providers](#api-providers)

---

## System Overview

The Real-Time Voice Assistant is a streaming voice-to-voice AI system that:
- **Listens** to your speech via microphone
- **Transcribes** audio using Groq Whisper API (fast & accurate)
- **Generates** responses using OpenRouter LLM (free tier available)
- **Synthesizes** speech using ElevenLabs TTS
- **Streams** audio back to you in real-time

### Technology Stack
- **Backend**: Python 3.11+ with asyncio
- **ASR**: Groq Whisper API (whisper-large-v3-turbo)
- **LLM**: OpenRouter (liquid/lfm-2.5-1.2b-instruct:free)
- **TTS**: ElevenLabs (eleven_turbo_v2_5)
- **Protocol**: WebSocket for real-time communication
- **Frontend**: HTML5 + Web Audio API

---

## Prerequisites

### Required Software

- **Python**: Version 3.11 or higher
- **pip**: Python package manager
- **Web Browser**: Chrome, Firefox, or Edge (for microphone access)
- **Internet Connection**: Required for API calls

### Required API Keys

You need three API keys (all have free tiers):

1. **Groq API Key** (for Whisper speech recognition)
   - Sign up: https://console.groq.com/
   - Free tier: Generous limits for testing
   - Model: whisper-large-v3-turbo

2. **OpenRouter API Key** (for LLM responses)
   - Sign up: https://openrouter.ai/
   - Free tier: 50 requests/day with free models
   - Model: liquid/lfm-2.5-1.2b-instruct:free

3. **ElevenLabs API Key** (for text-to-speech)
   - Sign up: https://elevenlabs.io/
   - Free tier: 10,000 characters/month
   - Model: eleven_turbo_v2_5

---

## Installation

### Step 1: Clone or Download the Project

```bash
cd /path/to/your/project
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `groq` - Groq API client for Whisper
- `elevenlabs` - ElevenLabs TTS client
- `websockets` - WebSocket server
- `aiohttp` - Async HTTP client
- `pydantic` - Data validation
- Other supporting packages

---

## Configuration

### Step 1: Copy Environment File


The `.env` file is already configured in the project root.

### Step 2: Add Your API Keys

Edit the `.env` file and add your API keys:

```env
# Groq API key for Whisper speech recognition
WHISPER_API_KEY="your_groq_api_key_here"

# OpenRouter API key for language model
GEMINI_API_KEY="your_openrouter_api_key_here"
GEMINI_MODEL="liquid/lfm-2.5-1.2b-instruct:free"

# ElevenLabs API key and voice ID
ELEVENLABS_API_KEY="your_elevenlabs_api_key_here"
ELEVENLABS_VOICE_ID="Hp4kwPGydiEKQ38qYLC8"
```

### Step 3: Verify Configuration

Run the setup checker:

```bash
python check_setup.py
```

This will verify:
- Python version
- All dependencies installed
- API keys configured
- Environment ready

---

## Running the Application

### Step 1: Start the Server

```bash
# Windows
$env:PYTHONPATH="."; .venv\Scripts\python.exe src/main.py

# Linux/Mac
PYTHONPATH=. python src/main.py
```

You should see:

```
{"event": "Groq Whisper API client initialized", "level": "info"}
{"event": "Reasoning service initialized", "model": "liquid/lfm-2.5-1.2b-instruct:free"}
{"event": "TTS service initialized", "voice_id": "Hp4kwPGydiEKQ38qYLC8"}
{"event": "WebSocket server started", "port": 8000}
{"event": "Real-Time Voice Assistant started successfully"}
```

### Step 2: Access the Web Interface

Open `voice_test.html` in your web browser:

```bash
# Windows
start voice_test.html

# Linux
xdg-open voice_test.html

# Mac
open voice_test.html
```

Or manually open the file in Chrome/Firefox/Edge.

---

## Using the Voice Assistant

### Step-by-Step Usage


1. **Click "Connect"**
   - Connects to WebSocket server at `ws://localhost:8000`
   - Status changes to "Connected - Ready to speak"

2. **Allow Microphone Access**
   - Browser will prompt for microphone permission
   - Click "Allow" to grant access

3. **Click the Microphone Button**
   - Button turns red and shows "Listening..."
   - Speak clearly into your microphone
   - Audio is captured at 16kHz, mono, 16-bit PCM

4. **Click Again to Stop Recording**
   - Audio is sent to server for processing
   - Status shows "Processing..."

5. **Wait for Response**
   - Transcription appears in the transcript area
   - LLM generates a response
   - TTS synthesizes speech
   - Audio plays automatically through your speakers

6. **Continue Conversation**
   - Click microphone again to ask another question
   - Conversation context is maintained (last 10 turns)

### Example Conversation

```
You: "What is Python?"
Assistant: "Python is a high-level programming language..."

You: "What are its main features?"
Assistant: "Python's main features include..."
```

---

## Architecture

### System Components

```
┌─────────────┐
│   Browser   │
│ (voice_test │
│   .html)    │
└──────┬──────┘
       │ WebSocket
       │ (audio PCM)
       ▼
┌─────────────────────────────────────┐
│     WebSocket Server (Port 8000)    │
│  - Receives audio frames             │
│  - Sends audio responses             │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│      Event Pipeline (asyncio)        │
│                                      │
│  ┌──────────┐  ┌──────────┐        │
│  │  Audio   │→ │Transcript│        │
│  │  Queue   │  │  Queue   │        │
│  └──────────┘  └──────────┘        │
│       ↓             ↓               │
│  ┌──────────┐  ┌──────────┐        │
│  │  Token   │← │   TTS    │        │
│  │  Queue   │  │  Queue   │        │
│  └──────────┘  └──────────┘        │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│          Services Layer              │
│                                      │
│  ┌──────────────────────────────┐  │
│  │  ASR Service                  │  │
│  │  - Groq Whisper API           │  │
│  │  - whisper-large-v3-turbo     │  │
│  └──────────────────────────────┘  │
│                                      │
│  ┌──────────────────────────────┐  │
│  │  LLM Service                  │  │
│  │  - OpenRouter API             │  │
│  │  - LiquidAI model             │  │
│  └──────────────────────────────┘  │
│                                      │
│  ┌──────────────────────────────┐  │
│  │  TTS Service                  │  │
│  │  - ElevenLabs API             │  │
│  │  - eleven_turbo_v2_5          │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```
