# Test Suite Organization

## Overview

The test suite is organized to mirror the production code structure, making it easy to find and maintain tests for specific components.

## Structure

```
tests/
├── conftest.py                      # Shared pytest configuration and fixtures
├── __init__.py                      # Test package initialization
│
├── unit/                            # Unit tests (test individual components)
│   ├── core/                        # Tests for core domain models
│   │   └── test_models.py           # AudioBuffer, TokenBuffer, Session tests
│   ├── infrastructure/              # Tests for infrastructure components
│   │   ├── test_config.py           # Configuration management tests
│   │   ├── test_logging.py          # Structured logging tests
│   │   └── test_resilience.py       # Circuit breaker, retry, timeout tests
│   ├── observability/               # Tests for observability components
│   │   ├── test_health.py           # Health check system tests
│   │   ├── test_latency.py          # Latency tracking tests
│   │   └── test_metrics.py          # Metrics aggregation tests
│   ├── services/                    # Tests for external service integrations
│   │   ├── test_asr.py              # ASR service tests
│   │   ├── test_llm.py              # LLM service tests
│   │   └── test_tts.py              # TTS service tests
│   ├── session/                     # Tests for session management
│   │   ├── test_manager.py          # SessionManager tests
│   │   ├── test_recorder.py         # SessionRecorder tests
│   │   └── test_replay.py           # ReplaySystem tests
│   └── api/                         # Tests for API layer
│       └── test_websocket.py        # WebSocket server tests
│
├── integration/                     # Integration tests (test component interactions)
│   ├── test_event_pipeline.py       # Event pipeline integration tests
│   ├── test_main.py                 # Application startup tests
│   └── test_websocket.py            # WebSocket integration tests
│
├── e2e/                            # End-to-end tests (test complete workflows)
│   └── test_complete_flow.py        # Complete audio-to-audio flow tests
│
├── performance/                     # Performance and load tests
│   └── test_latency_budgets.py      # Latency budget validation tests
│
└── fixtures/                        # Shared test fixtures and mocks
    ├── __init__.py
    ├── mocks.py                     # Mock services (Whisper, Gemini, ElevenLabs)
    ├── test_fixtures.py             # Tests for fixtures themselves
    ├── test_integration_example.py  # Example of using fixtures
    ├── README.md                    # Fixtures documentation
    └── USAGE_GUIDE.md               # How to use fixtures
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation with mocked dependencies.

**Characteristics:**
- Fast execution (< 1 second per test)
- No external dependencies
- Mock all I/O operations
- Test single responsibility

**Example:**
```python
def test_audio_buffer_append():
    """Test that AudioBuffer correctly appends frames."""
    buffer = AudioBuffer(duration_ms=500)
    frame = AudioFrame(session_id="test", data=b'\x00' * 1000)
    
    buffer.append(frame)
    
    assert len(buffer.frames) == 1
    assert buffer.total_samples > 0
```

**Run unit tests:**
```bash
# All unit tests
pytest tests/unit/ -v

# Specific component
pytest tests/unit/core/test_models.py -v
pytest tests/unit/services/test_asr.py -v
```

### Integration Tests (`tests/integration/`)

Test interactions between multiple components.

**Characteristics:**
- Moderate execution time (1-5 seconds per test)
- Use mock external services
- Test component integration
- Verify event flow

**Example:**
```python
@pytest.mark.asyncio
async def test_event_pipeline_flow():
    """Test events flow through the complete pipeline."""
    # Create services with mocks
    asr_service = ASRService(...)
    llm_service = ReasoningService(...)
    tts_service = TTSService(...)
    
    # Create session
    session = await session_manager.create_session(websocket=None)
    
    # Feed audio
    await session.audio_queue.put(audio_frame)
    
    # Verify output
    output = await session.tts_queue.get()
    assert isinstance(output, TTSAudioEvent)
```

**Run integration tests:**
```bash
# All integration tests
pytest tests/integration/ -v

# Specific integration
pytest tests/integration/test_event_pipeline.py -v
```

### End-to-End Tests (`tests/e2e/`)

Test complete workflows from start to finish.

**Characteristics:**
- Slower execution (5-30 seconds per test)
- Test complete user scenarios
- Verify system behavior
- Test error recovery

**Example:**
```python
@pytest.mark.asyncio
async def test_complete_audio_to_audio_flow():
    """Test complete flow from audio input to audio output."""
    # Create session
    session = await session_manager.create_session(websocket=None)
    
    # Generate test audio
    audio_frames = generate_audio_frames(...)
    
    # Feed audio through pipeline
    for frame in audio_frames:
        await session.audio_queue.put(frame)
    
    # Wait for processing
    await asyncio.sleep(1.0)
    
    # Verify output was generated
    assert not session.tts_queue.empty()
```

**Run e2e tests:**
```bash
# All e2e tests
pytest tests/e2e/ -v

# Specific scenario
pytest tests/e2e/test_complete_flow.py::TestCompleteAudioToAudioFlow -v
```

### Performance Tests (`tests/performance/`)

Test system performance and validate latency budgets.

**Characteristics:**
- Measure execution time
- Validate latency requirements
- Test under load
- Generate performance reports

**Example:**
```python
@pytest.mark.asyncio
async def test_asr_latency_budget():
    """Test that ASR latency is within budget (500ms)."""
    start_time = datetime.now()
    
    # Process audio
    result = await asr_service.transcribe(audio_data)
    
    end_time = datetime.now()
    latency_ms = (end_time - start_time).total_seconds() * 1000
    
    # Verify latency budget
    assert latency_ms < 500, f"ASR latency {latency_ms}ms exceeds budget"
```

**Run performance tests:**
```bash
# All performance tests
pytest tests/performance/ -v

# With detailed output
pytest tests/performance/ -v -s
```

## Running Tests

### Run All Tests
```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Parallel execution (faster)
pytest tests/ -n auto
```

### Run by Category
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# E2E tests only
pytest tests/e2e/ -v

# Performance tests only
pytest tests/performance/ -v
```

### Run by Component
```bash
# Core tests
pytest tests/unit/core/ -v

# Service tests
pytest tests/unit/services/ -v

# Infrastructure tests
pytest tests/unit/infrastructure/ -v

# Observability tests
pytest tests/unit/observability/ -v
```

### Run Specific Tests
```bash
# Single test file
pytest tests/unit/core/test_models.py -v

# Single test class
pytest tests/unit/core/test_models.py::TestAudioBuffer -v

# Single test method
pytest tests/unit/core/test_models.py::TestAudioBuffer::test_append -v
```

### Run with Markers
```bash
# Async tests only
pytest tests/ -m asyncio -v

# Slow tests only
pytest tests/ -m slow -v

# Skip slow tests
pytest tests/ -m "not slow" -v
```

## Test Fixtures

Shared fixtures are available in `tests/fixtures/mocks.py`:

### Mock Services
- `MockWhisperClient` - Mock ASR service
- `MockGeminiClient` - Mock LLM service
- `MockElevenLabsClient` - Mock TTS service

### Test Data Generators
- `generate_audio_frames()` - Generate test audio data
- `generate_transcript_events()` - Generate test transcripts
- `generate_token_events()` - Generate test tokens

### Usage Example
```python
from tests.fixtures.mocks import MockWhisperClient, generate_audio_frames

@pytest.fixture
def asr_service(mock_whisper_client):
    """Create ASR service with mock client."""
    service = ASRService(api_key="test_key")
    service.client = mock_whisper_client
    return service

def test_transcription(asr_service):
    """Test transcription with mock service."""
    audio_frames = generate_audio_frames(duration_ms=1000)
    result = await asr_service.transcribe(audio_frames)
    assert result.text == "Hello, how can I help you?"
```

See [fixtures/README.md](fixtures/README.md) for detailed documentation.

## Writing New Tests

### 1. Choose the Right Category

- **Unit test** if testing a single component in isolation
- **Integration test** if testing component interactions
- **E2E test** if testing a complete user workflow
- **Performance test** if validating performance requirements

### 2. Follow Naming Conventions

```python
# Test files: test_<component>.py
tests/unit/services/test_asr.py

# Test classes: Test<Component>
class TestASRService:
    pass

# Test methods: test_<behavior>
def test_transcribe_audio_successfully():
    pass
```

### 3. Use Descriptive Names

```python
# Good
def test_audio_buffer_is_ready_when_target_samples_reached():
    pass

# Bad
def test_buffer():
    pass
```

### 4. Follow AAA Pattern

```python
def test_example():
    # Arrange - Set up test data
    buffer = AudioBuffer(duration_ms=500)
    frame = AudioFrame(...)
    
    # Act - Execute the behavior
    buffer.append(frame)
    
    # Assert - Verify the result
    assert buffer.is_ready()
```

### 5. Use Fixtures for Setup

```python
@pytest.fixture
def audio_buffer():
    """Create audio buffer for testing."""
    return AudioBuffer(duration_ms=500)

def test_append(audio_buffer):
    """Test appending frames to buffer."""
    frame = AudioFrame(...)
    audio_buffer.append(frame)
    assert len(audio_buffer.frames) == 1
```

### 6. Mock External Dependencies

```python
@pytest.fixture
def mock_whisper_client():
    """Create mock Whisper client."""
    client = MockWhisperClient()
    client.configure_response("Test transcription")
    return client

def test_with_mock(mock_whisper_client):
    """Test using mock client."""
    result = await mock_whisper_client.transcribe(audio_data)
    assert result == "Test transcription"
```

## Test Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    performance: marks tests as performance tests
```

### conftest.py

Shared configuration and fixtures in `tests/conftest.py`:
- Automatic pytest configuration
- Shared fixtures available to all tests
- Test utilities and helpers

## Coverage

### Generate Coverage Report

```bash
# HTML report
pytest tests/ --cov=src --cov-report=html

# Terminal report
pytest tests/ --cov=src --cov-report=term

# XML report (for CI/CD)
pytest tests/ --cov=src --cov-report=xml
```

### View Coverage

```bash
# Open HTML report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

### Coverage Goals

- **Unit tests**: > 90% coverage
- **Integration tests**: > 80% coverage
- **Overall**: > 85% coverage

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Best Practices

1. **Keep tests independent** - Each test should run in isolation
2. **Use descriptive names** - Test names should describe what they test
3. **Test one thing** - Each test should verify one behavior
4. **Use fixtures** - Reuse common setup code
5. **Mock external services** - Don't make real API calls in tests
6. **Test edge cases** - Test boundary conditions and error cases
7. **Keep tests fast** - Unit tests should run in milliseconds
8. **Write tests first** - TDD helps design better code
9. **Maintain tests** - Update tests when code changes
10. **Document complex tests** - Add docstrings explaining what's being tested

## Troubleshooting

### Tests Not Found

```bash
# Make sure you're in the project root
cd /path/to/project

# Run with verbose output
pytest tests/ -v

# Check test discovery
pytest --collect-only
```

### Import Errors

```bash
# Install in development mode
pip install -e .

# Or add src to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Async Test Failures

```bash
# Make sure pytest-asyncio is installed
pip install pytest-asyncio

# Check pytest.ini has asyncio_mode = auto
```

### Fixture Not Found

```bash
# Check fixture is defined in conftest.py or test file
# Check fixture name matches usage
# Check fixture scope is appropriate
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Test Fixtures Guide](fixtures/README.md)
- [Fixtures Usage Guide](fixtures/USAGE_GUIDE.md)
