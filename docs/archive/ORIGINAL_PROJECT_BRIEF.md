You are a senior AI systems engineer.

Your task is to design and implement a **real-time voice assistant application** with a production-ready architecture.

The system must handle the unique challenges of real-time streaming systems including:

- tight latency budgets
- asynchronous event pipelines
- streaming data processing
- fault tolerance and timeout handling
- observability and latency tracking

This system must NOT be designed like a batch pipeline. It must operate as a **low-latency streaming architecture**.

------------------------------------------------

SYSTEM OVERVIEW

Build a voice assistant pipeline with the following stages:

1. Audio Input
   - Capture microphone audio stream from the client
   - Send audio frames through WebSockets

2. Automatic Speech Recognition (ASR)
   - Use Whisper for real-time speech recognition
   - Convert audio stream into partial and final transcriptions

3. Reasoning Layer
   - Send transcriptions to Gemini for reasoning
   - Support streaming responses where possible

4. Text-To-Speech (TTS)
   - Convert the generated text response to speech
   - Use ElevenLabs streaming TTS API

5. Streaming Output
   - Send synthesized audio back to the client through WebSockets
   - Ensure playback starts before the full response completes

------------------------------------------------

TECH STACK

Speech Recognition:
Whisper

Reasoning Layer:
Gemini

Speech Synthesis:
ElevenLabs

Orchestration:
WebSockets

Backend:
Python (FastAPI recommended)

Event System:
Async streaming architecture

------------------------------------------------

PHASE 1 — STREAMING PIPELINE

Goal:
Get the end-to-end streaming pipeline functioning.

Requirements:

- Implement a WebSocket server
- Accept streaming audio input
- Send audio frames to Whisper
- Stream partial transcripts
- Send transcript to Gemini
- Stream LLM tokens
- Convert response text to speech via ElevenLabs
- Stream synthesized audio back to the client

Focus on:

- event-based pipeline
- non-blocking async design
- modular components

Define clear event structures such as:

AudioChunk
TranscriptEvent
LLMTokenEvent
TTSAudioEvent

------------------------------------------------

PHASE 2 — LATENCY TRACKING

Add detailed latency instrumentation across the pipeline.

Measure:

1. ASR latency
   - audio received → transcript generated

2. LLM latency
   - transcript sent → first token generated

3. TTS latency
   - response text → first audio byte

4. Network and orchestration overhead

Create a latency breakdown for every request.

Build a visualization dashboard showing:

- ASR latency
- LLM time-to-first-token
- TTS time-to-first-byte
- total pipeline latency

The system should log these metrics for observability.

------------------------------------------------

PHASE 3 — RESILIENCE AND DEBUGGING

Improve robustness of the system.

Implement:

Timeout handling
- ensure no stage blocks the pipeline

Retry mechanisms
- retry failed API calls safely

Replay Mode
- allow feeding recorded audio input into the pipeline
- useful for debugging and latency testing

Structured logging
- log every event with timestamps

Graceful degradation
- system should continue operating even if one component fails

------------------------------------------------

DELIVERABLES

Provide:

1. Full architecture design
2. Streaming event model
3. Production-ready Python code structure
4. WebSocket server implementation
5. Latency instrumentation
6. Debug replay system
7. Observability logging
8. Example client application

The system must prioritize:

low latency
high resilience
clean modular architecture
streaming-first design