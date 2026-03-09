# Test Fixtures and Mock Services

This directory contains comprehensive test fixtures and mock services for testing the real-time voice assistant application without making actual API calls to external services.

## Files

- **`fixtures.py`**: Core fixtures module containing mock API clients, audio generators, and event generators
- **`test_fixtures.py`**: Unit tests for all fixtures to ensure they work correctly
- **`test_fixtures_integration_example.py`**: Integration test examples showing how to use fixtures in realistic scenarios
- **`FIXTURES_USAGE_GUIDE.md`**: Comprehensive guide on how to use the fixtures

## Quick Start

### Using Mock API Clients

```python
from tests.fixtures import MockWhisperClient, MockGeminiClient, MockElevenLabsClient

# Create mock clients
whisper_mock = MockWhisperClient(default_text="Test transcription")
gemini_mock = MockGeminiClient(default_tokens=["Hello", " ", "world"])
elevenlabs_mock = MockElevenLabsClient(default_chunks=[b'audio1', b'audio2'])

# Use in your service tests
asr_service.client = whisper_mock
reasoning_service.client = gemini_mock
tts_service.client = elevenlabs_mock
```

### Generating Test Audio

```python
from tests.fixtures import generate_audio_frames, generate_sine_wave

# Generate audio frames for testing
frames = generate_audio_frames(
    session_id="test_session",
    duration_ms=1000,
    audio_type="sine"  # or "silence" or "noise"
)

# Generate raw audio data
audio_data = generate_sine_wave(duration_ms=1000, frequency=440.0)
```

### Creating Test Events

```python
from tests.fixtures import (
    create_transcript_event,
    create_llm_token_events,
    create_tts_audio_events
)

# Create test events
transcript = create_transcript_event(text="Hello", partial=False)
tokens = create_llm_token_events(tokens=["Test", " ", "response"])
audio_events = create_tts_audio_events(num_chunks=3)
```

## Features

### Mock API Clients

All mock clients support:
- **Configurable responses**: Set custom return values
- **Error simulation**: Simulate timeouts, API errors, network errors
- **Latency simulation**: Add delays to simulate real API behavior
- **Call tracking**: Track all API calls for verification
- **Reset functionality**: Clear call history between tests

### Audio Data Generators

Generate realistic test audio:
- **Silence**: All-zero audio data
- **Sine waves**: Pure tone at specified frequency
- **White noise**: Random audio data
- **Audio frames**: Pre-packaged AudioFrame objects

### Event Generators

Create test events easily:
- **TranscriptEvent**: ASR transcription results
- **LLMTokenEvent**: Streaming LLM tokens
- **TTSAudioEvent**: Synthesized audio chunks
- **ErrorEvent**: Error notifications

## Running Tests

Run all fixture tests:
```bash
pytest tests/test_fixtures.py -v
```

Run integration examples:
```bash
pytest tests/test_fixtures_integration_example.py -v
```

Run with coverage:
```bash
pytest tests/test_fixtures.py --cov=tests.fixtures --cov-report=html
```

## Benefits

1. **No External Dependencies**: Test without real API keys or network access
2. **Fast Execution**: No network latency or API rate limits
3. **Deterministic**: Consistent, reproducible test results
4. **Error Testing**: Easy to simulate error conditions
5. **Latency Testing**: Simulate various latency scenarios
6. **Cost-Free**: No API usage costs during testing

## Requirements

This module validates **Requirement 7.3**: Create test fixtures and mock services for:
- Mock Whisper API client
- Mock Gemini API client
- Mock ElevenLabs API client
- Test audio data generators

## Documentation

For detailed usage instructions and examples, see:
- **`FIXTURES_USAGE_GUIDE.md`**: Complete usage guide with examples
- **`test_fixtures_integration_example.py`**: Real-world integration test examples

## Architecture

The fixtures are designed to be:
- **Drop-in replacements**: Same interface as real API clients
- **Highly configurable**: Customize behavior for different test scenarios
- **Observable**: Track all interactions for verification
- **Isolated**: No side effects or shared state between tests

## Example: Complete Service Test

```python
import asyncio
import pytest
from tests.fixtures import MockWhisperClient, generate_audio_frames
from src.asr_service import ASRService

@pytest.mark.asyncio
async def test_asr_service():
    # Setup
    asr_service = ASRService(api_key="test_key")
    mock_client = MockWhisperClient(default_text="Test transcription")
    asr_service.client = mock_client
    
    # Create test data
    frames = generate_audio_frames(
        session_id="test_session",
        duration_ms=1000,
        audio_type="sine"
    )
    
    # Create queues
    audio_queue = asyncio.Queue()
    transcript_queue = asyncio.Queue()
    
    # Add frames
    for frame in frames:
        await audio_queue.put(frame)
    
    # Process
    task = asyncio.create_task(
        asr_service.process_audio_stream(audio_queue, transcript_queue)
    )
    
    await asyncio.sleep(0.2)
    
    # Verify
    transcript = await transcript_queue.get()
    assert transcript.text == "Test transcription"
    assert mock_client.call_count == 1
    
    # Cleanup
    task.cancel()
```

## Contributing

When adding new fixtures:
1. Add the fixture to `fixtures.py`
2. Add unit tests to `test_fixtures.py`
3. Add integration examples to `test_fixtures_integration_example.py`
4. Update `FIXTURES_USAGE_GUIDE.md` with usage instructions

## License

Part of the real-time voice assistant project.
