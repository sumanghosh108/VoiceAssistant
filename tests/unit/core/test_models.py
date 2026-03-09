"""Unit tests for buffer data models."""

import pytest
from datetime import datetime
from src.core.models import AudioBuffer, TokenBuffer, ConversationContext, Message
from src.core.events import AudioFrame, LLMTokenEvent


class TestAudioBuffer:
    """Tests for AudioBuffer class."""
    
    def test_audio_buffer_initialization(self):
        """Test AudioBuffer initializes with correct parameters."""
        buffer = AudioBuffer(duration_ms=1000, sample_rate=16000)
        
        assert buffer.duration_ms == 1000
        assert buffer.sample_rate == 16000
        assert buffer.frames == []
        assert buffer.total_samples == 0
        assert buffer.target_samples == 16000  # 16000 samples for 1 second at 16kHz
    
    def test_audio_buffer_append(self):
        """Test appending audio frames to buffer."""
        buffer = AudioBuffer(duration_ms=1000, sample_rate=16000)
        
        # Create a frame with 1000 samples (2000 bytes for 16-bit PCM)
        frame = AudioFrame(
            session_id="test",
            data=b'\x00' * 2000,
            timestamp=datetime.now(),
            sequence_number=1
        )
        
        buffer.append(frame)
        
        assert len(buffer.frames) == 1
        assert buffer.total_samples == 1000
    
    def test_audio_buffer_is_ready(self):
        """Test buffer readiness detection."""
        buffer = AudioBuffer(duration_ms=100, sample_rate=16000)
        
        # Target is 1600 samples (100ms at 16kHz)
        assert not buffer.is_ready()
        
        # Add frame with 1600 samples (3200 bytes)
        frame = AudioFrame(
            session_id="test",
            data=b'\x00' * 3200,
            timestamp=datetime.now(),
            sequence_number=1
        )
        buffer.append(frame)
        
        assert buffer.is_ready()
    
    def test_audio_buffer_get_audio_bytes(self):
        """Test concatenating audio frames."""
        buffer = AudioBuffer(duration_ms=1000, sample_rate=16000)
        
        frame1 = AudioFrame(
            session_id="test",
            data=b'\x01\x02',
            timestamp=datetime.now(),
            sequence_number=1
        )
        frame2 = AudioFrame(
            session_id="test",
            data=b'\x03\x04',
            timestamp=datetime.now(),
            sequence_number=2
        )
        
        buffer.append(frame1)
        buffer.append(frame2)
        
        audio_bytes = buffer.get_audio_bytes()
        assert audio_bytes == b'\x01\x02\x03\x04'
    
    def test_audio_buffer_clear(self):
        """Test clearing buffer."""
        buffer = AudioBuffer(duration_ms=1000, sample_rate=16000)
        
        frame = AudioFrame(
            session_id="test",
            data=b'\x00' * 100,
            timestamp=datetime.now(),
            sequence_number=1
        )
        buffer.append(frame)
        
        buffer.clear()
        
        assert buffer.frames == []
        assert buffer.total_samples == 0


class TestTokenBuffer:
    """Tests for TokenBuffer class."""
    
    def test_token_buffer_initialization(self):
        """Test TokenBuffer initializes with correct parameters."""
        buffer = TokenBuffer(max_tokens=10)
        
        assert buffer.max_tokens == 10
        assert buffer.tokens == []
    
    def test_token_buffer_append(self):
        """Test appending tokens to buffer."""
        buffer = TokenBuffer(max_tokens=10)
        
        token = LLMTokenEvent(
            session_id="test",
            token="Hello",
            is_first=True,
            is_last=False,
            timestamp=datetime.now(),
            token_index=0
        )
        
        buffer.append(token)
        
        assert len(buffer.tokens) == 1
    
    def test_token_buffer_is_phrase_complete_max_tokens(self):
        """Test phrase completion by max tokens."""
        buffer = TokenBuffer(max_tokens=3)
        
        assert not buffer.is_phrase_complete()
        
        for i in range(3):
            token = LLMTokenEvent(
                session_id="test",
                token="word",
                is_first=i == 0,
                is_last=False,
                timestamp=datetime.now(),
                token_index=i
            )
            buffer.append(token)
        
        assert buffer.is_phrase_complete()
    
    def test_token_buffer_is_phrase_complete_sentence_boundary(self):
        """Test phrase completion by sentence boundary."""
        buffer = TokenBuffer(max_tokens=10)
        
        # Add token without boundary
        token1 = LLMTokenEvent(
            session_id="test",
            token="Hello",
            is_first=True,
            is_last=False,
            timestamp=datetime.now(),
            token_index=0
        )
        buffer.append(token1)
        assert not buffer.is_phrase_complete()
        
        # Add token with period
        token2 = LLMTokenEvent(
            session_id="test",
            token=" world.",
            is_first=False,
            is_last=False,
            timestamp=datetime.now(),
            token_index=1
        )
        buffer.append(token2)
        assert buffer.is_phrase_complete()
    
    def test_token_buffer_sentence_boundaries(self):
        """Test all sentence boundary punctuation."""
        for punct in ['.', '!', '?', '\n']:
            buffer = TokenBuffer(max_tokens=10)
            
            token = LLMTokenEvent(
                session_id="test",
                token=f"text{punct}",
                is_first=True,
                is_last=False,
                timestamp=datetime.now(),
                token_index=0
            )
            buffer.append(token)
            
            assert buffer.is_phrase_complete(), f"Failed for punctuation: {punct}"
    
    def test_token_buffer_get_text(self):
        """Test concatenating tokens into text."""
        buffer = TokenBuffer(max_tokens=10)
        
        tokens_text = ["Hello", " ", "world", "!"]
        for i, text in enumerate(tokens_text):
            token = LLMTokenEvent(
                session_id="test",
                token=text,
                is_first=i == 0,
                is_last=False,
                timestamp=datetime.now(),
                token_index=i
            )
            buffer.append(token)
        
        assert buffer.get_text() == "Hello world!"
    
    def test_token_buffer_clear(self):
        """Test clearing buffer."""
        buffer = TokenBuffer(max_tokens=10)
        
        token = LLMTokenEvent(
            session_id="test",
            token="test",
            is_first=True,
            is_last=False,
            timestamp=datetime.now(),
            token_index=0
        )
        buffer.append(token)
        
        buffer.clear()
        
        assert buffer.tokens == []


class TestConversationContext:
    """Tests for ConversationContext class."""
    
    def test_conversation_context_initialization(self):
        """Test ConversationContext initializes with correct parameters."""
        context = ConversationContext(max_turns=10)
        
        assert context.max_turns == 10
        assert context.messages == []
    
    def test_add_user_message(self):
        """Test adding user message."""
        context = ConversationContext(max_turns=10)
        
        context.add_user_message("Hello")
        
        assert len(context.messages) == 1
        assert context.messages[0].role == "user"
        assert context.messages[0].content == "Hello"
        assert isinstance(context.messages[0].timestamp, datetime)
    
    def test_add_assistant_message(self):
        """Test adding assistant message."""
        context = ConversationContext(max_turns=10)
        
        context.add_assistant_message("Hi there!")
        
        assert len(context.messages) == 1
        assert context.messages[0].role == "assistant"
        assert context.messages[0].content == "Hi there!"
    
    def test_conversation_context_history_trimming(self):
        """Test that history is trimmed to max_turns."""
        context = ConversationContext(max_turns=2)
        
        # Add 3 turns (6 messages)
        for i in range(3):
            context.add_user_message(f"User message {i}")
            context.add_assistant_message(f"Assistant message {i}")
        
        # Should only keep last 2 turns (4 messages)
        assert len(context.messages) == 4
        assert context.messages[0].content == "User message 1"
        assert context.messages[-1].content == "Assistant message 2"
    
    def test_get_messages_for_api(self):
        """Test formatting messages for API."""
        context = ConversationContext(max_turns=10)
        
        context.add_user_message("Hello")
        context.add_assistant_message("Hi there!")
        
        api_messages = context.get_messages_for_api()
        
        assert len(api_messages) == 2
        assert api_messages[0] == {"role": "user", "content": "Hello"}
        assert api_messages[1] == {"role": "assistant", "content": "Hi there!"}
    
    def test_conversation_context_empty(self):
        """Test empty conversation context."""
        context = ConversationContext(max_turns=10)
        
        api_messages = context.get_messages_for_api()
        
        assert api_messages == []


class TestMessage:
    """Tests for Message dataclass."""
    
    def test_message_creation(self):
        """Test creating a Message."""
        timestamp = datetime.now()
        message = Message(
            role="user",
            content="Test message",
            timestamp=timestamp
        )
        
        assert message.role == "user"
        assert message.content == "Test message"
        assert message.timestamp == timestamp
