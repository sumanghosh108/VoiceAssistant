"""
Unit tests for event pipeline architecture verification.

This test suite verifies that the asyncio.Queue-based event pipeline meets
all requirements for non-blocking event delivery, session isolation, and
FIFO ordering.

Task 14.1: Verify asyncio.Queue-based event pipeline
Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.7
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from src.core.models import Session, SessionManager
from src.core.events import AudioFrame, TranscriptEvent, LLMTokenEvent, TTSAudioEvent
from src.observability.latency import LatencyTracker


class TestEventPipelineNonBlocking:
    """Test that event pipeline provides non-blocking event delivery.
    
    Requirement 6.3: Event pipeline SHALL deliver events to subscribed 
    components without blocking the emitter.
    """
    
    @pytest.mark.asyncio
    async def test_queue_put_nowait_non_blocking(self):
        """Test that queue.put_nowait() does not block when queue has space."""
        queue = asyncio.Queue(maxsize=10)
        
        # Put items without blocking
        start_time = asyncio.get_event_loop().time()
        for i in range(10):
            queue.put_nowait(f"item_{i}")
        end_time = asyncio.get_event_loop().time()
        
        # Should complete instantly (< 10ms)
        assert (end_time - start_time) < 0.01
        assert queue.qsize() == 10
        
    @pytest.mark.asyncio
    async def test_queue_put_with_await_non_blocking_when_space_available(self):
        """Test that await queue.put() does not block when queue has space."""
        queue = asyncio.Queue(maxsize=10)
        
        # Put items with await - should not block when space available
        start_time = asyncio.get_event_loop().time()
        for i in range(10):
            await queue.put(f"item_{i}")
        end_time = asyncio.get_event_loop().time()
        
        # Should complete quickly (< 50ms)
        assert (end_time - start_time) < 0.05
        assert queue.qsize() == 10
        
    @pytest.mark.asyncio
    async def test_producer_not_blocked_by_slow_consumer(self):
        """Test that producer can buffer events in queue even with slow consumer.
        
        Note: With asyncio.Queue, the producer will eventually block when the queue
        is full, but the queue provides buffering that allows the producer to run
        ahead of the consumer up to the maxsize limit.
        """
        queue = asyncio.Queue(maxsize=100)
        produced_count = 0
        consumed_count = 0
        
        async def fast_producer():
            nonlocal produced_count
            for i in range(50):
                await queue.put(f"event_{i}")
                produced_count += 1
                await asyncio.sleep(0.001)  # Fast producer (1ms per event)
                
        async def slow_consumer():
            nonlocal consumed_count
            await asyncio.sleep(0.1)  # Delay before starting
            for i in range(50):
                await queue.get()
                consumed_count += 1
                await asyncio.sleep(0.01)  # Slow consumer (10ms per event)
                
        # Start both tasks
        producer_task = asyncio.create_task(fast_producer())
        consumer_task = asyncio.create_task(slow_consumer())
        
        # Wait a bit for producer to get ahead
        await asyncio.sleep(0.15)
        
        # Producer should have produced many events while consumer is slow
        assert produced_count > consumed_count
        # Queue should have buffered events
        assert queue.qsize() > 0
        
        # Wait for both to complete
        await asyncio.gather(producer_task, consumer_task)
        assert produced_count == 50
        assert consumed_count == 50


class TestEventPipelineSessionIsolation:
    """Test that each session has isolated queues.
    
    Requirement 6.2: Event pipeline SHALL support concurrent processing 
    of multiple Sessions.
    
    Requirement 6.5: Event pipeline SHALL isolate failures in one Session 
    from affecting other Sessions.
    """
    
    @pytest.mark.asyncio
    async def test_sessions_have_separate_queue_instances(self):
        """Test that each session gets its own queue instances."""
        # Create mock services
        asr_service = Mock()
        asr_service.process_audio_stream = AsyncMock()
        
        llm_service = Mock()
        llm_service.process_transcript_stream = AsyncMock()
        
        tts_service = Mock()
        tts_service.process_token_stream = AsyncMock()
        
        manager = SessionManager(
            asr_service=asr_service,
            llm_service=llm_service,
            tts_service=tts_service
        )
        
        # Create multiple sessions
        session1 = await manager.create_session(Mock())
        session2 = await manager.create_session(Mock())
        session3 = await manager.create_session(Mock())
        
        # Verify all queues are different instances
        assert session1.audio_queue is not session2.audio_queue
        assert session1.audio_queue is not session3.audio_queue
        assert session2.audio_queue is not session3.audio_queue
        
        assert session1.transcript_queue is not session2.transcript_queue
        assert session1.token_queue is not session2.token_queue
        assert session1.tts_queue is not session2.tts_queue
        
        # Cleanup
        await manager.cleanup_session(session1.session_id)
        await manager.cleanup_session(session2.session_id)
        await manager.cleanup_session(session3.session_id)
        
    @pytest.mark.asyncio
    async def test_events_in_one_session_do_not_affect_another(self):
        """Test that events in one session's queue don't appear in another session."""
        queue1 = asyncio.Queue(maxsize=10)
        queue2 = asyncio.Queue(maxsize=10)
        
        # Put events in queue1
        await queue1.put("event_1_a")
        await queue1.put("event_1_b")
        await queue1.put("event_1_c")
        
        # Put events in queue2
        await queue2.put("event_2_a")
        await queue2.put("event_2_b")
        
        # Verify queue sizes
        assert queue1.qsize() == 3
        assert queue2.qsize() == 2
        
        # Verify queue1 only has its events
        item1 = await queue1.get()
        item2 = await queue1.get()
        item3 = await queue1.get()
        assert item1 == "event_1_a"
        assert item2 == "event_1_b"
        assert item3 == "event_1_c"
        assert queue1.empty()
        
        # Verify queue2 only has its events
        item1 = await queue2.get()
        item2 = await queue2.get()
        assert item1 == "event_2_a"
        assert item2 == "event_2_b"
        assert queue2.empty()
        
    @pytest.mark.asyncio
    async def test_exception_in_one_session_does_not_affect_others(self):
        """Test that an exception in one session's processing doesn't affect other sessions."""
        results = {"session1": None, "session2": None, "session3": None}
        
        async def process_session(session_id, should_fail=False):
            queue = asyncio.Queue()
            await queue.put("event")
            
            try:
                event = await queue.get()
                if should_fail:
                    raise ValueError(f"Simulated error in {session_id}")
                results[session_id] = "success"
            except Exception as e:
                results[session_id] = f"error: {str(e)}"
                
        # Run three sessions, one fails
        await asyncio.gather(
            process_session("session1", should_fail=False),
            process_session("session2", should_fail=True),
            process_session("session3", should_fail=False),
            return_exceptions=True
        )
        
        # Verify session1 and session3 succeeded despite session2 failing
        assert results["session1"] == "success"
        assert "error" in results["session2"]
        assert results["session3"] == "success"


class TestEventPipelineFIFOOrdering:
    """Test that queue.put() and queue.get() maintain FIFO ordering.
    
    Requirement 6.4: Event pipeline SHALL maintain event ordering within 
    each Session.
    """
    
    @pytest.mark.asyncio
    async def test_queue_maintains_fifo_order(self):
        """Test that asyncio.Queue maintains FIFO (first-in-first-out) order."""
        queue = asyncio.Queue()
        
        # Put events in order
        events = ["event_1", "event_2", "event_3", "event_4", "event_5"]
        for event in events:
            await queue.put(event)
            
        # Get events and verify order
        retrieved = []
        for _ in range(len(events)):
            retrieved.append(await queue.get())
            
        assert retrieved == events
        
    @pytest.mark.asyncio
    async def test_fifo_order_with_timestamps(self):
        """Test FIFO ordering with timestamped events."""
        queue = asyncio.Queue()
        
        # Create events with timestamps
        events = []
        for i in range(10):
            event = AudioFrame(
                session_id="test",
                data=f"audio_{i}".encode(),
                timestamp=datetime.now(),
                sequence_number=i,
                sample_rate=16000,
                channels=1
            )
            events.append(event)
            await queue.put(event)
            await asyncio.sleep(0.001)  # Small delay to ensure different timestamps
            
        # Retrieve events and verify order
        retrieved = []
        for _ in range(len(events)):
            retrieved.append(await queue.get())
            
        # Verify sequence numbers are in order
        for i, event in enumerate(retrieved):
            assert event.sequence_number == i
            
    @pytest.mark.asyncio
    async def test_fifo_order_under_concurrent_access(self):
        """Test that FIFO order is maintained even with concurrent producers."""
        queue = asyncio.Queue()
        
        async def producer(start_id, count):
            for i in range(count):
                event_id = start_id + i
                await queue.put(event_id)
                await asyncio.sleep(0.001)
                
        # Start multiple producers
        await asyncio.gather(
            producer(0, 10),
            producer(100, 10),
            producer(200, 10)
        )
        
        # Retrieve all events
        retrieved = []
        while not queue.empty():
            retrieved.append(await queue.get())
            
        # Verify we got all 30 events
        assert len(retrieved) == 30
        
        # Verify each producer's events are in order relative to themselves
        producer1_events = [e for e in retrieved if e < 100]
        producer2_events = [e for e in retrieved if 100 <= e < 200]
        producer3_events = [e for e in retrieved if e >= 200]
        
        assert producer1_events == sorted(producer1_events)
        assert producer2_events == sorted(producer2_events)
        assert producer3_events == sorted(producer3_events)
        
    @pytest.mark.asyncio
    async def test_fifo_order_through_pipeline_stages(self):
        """Test that events maintain order through multiple pipeline stages."""
        audio_queue = asyncio.Queue()
        transcript_queue = asyncio.Queue()
        
        # Simulate ASR service that processes in order
        async def asr_processor():
            while True:
                try:
                    audio = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                    # Process and emit transcript
                    transcript = TranscriptEvent(
                        session_id="test",
                        text=f"transcript_{audio.sequence_number}",
                        partial=False,
                        confidence=0.95,
                        timestamp=datetime.now(),
                        audio_duration_ms=1000
                    )
                    await transcript_queue.put(transcript)
                except asyncio.TimeoutError:
                    break
                    
        # Start processor
        processor_task = asyncio.create_task(asr_processor())
        
        # Put audio frames in order
        for i in range(5):
            audio = AudioFrame(
                session_id="test",
                data=f"audio_{i}".encode(),
                timestamp=datetime.now(),
                sequence_number=i,
                sample_rate=16000,
                channels=1
            )
            await audio_queue.put(audio)
            
        # Wait for processing
        await asyncio.sleep(0.1)
        processor_task.cancel()
        
        # Verify transcripts are in order
        transcripts = []
        while not transcript_queue.empty():
            transcripts.append(await transcript_queue.get())
            
        assert len(transcripts) == 5
        for i, transcript in enumerate(transcripts):
            assert transcript.text == f"transcript_{i}"


class TestEventPipelineBackpressure:
    """Test event pipeline backpressure mechanisms.
    
    Requirement 6.6: Event pipeline SHALL provide backpressure mechanisms 
    when consumers cannot keep pace.
    """
    
    @pytest.mark.asyncio
    async def test_queue_blocks_when_full(self):
        """Test that queue.put() blocks when queue is full."""
        queue = asyncio.Queue(maxsize=5)
        
        # Fill the queue
        for i in range(5):
            await queue.put(f"item_{i}")
            
        assert queue.full()
        
        # Try to put another item - should block
        put_completed = False
        
        async def try_put():
            nonlocal put_completed
            await queue.put("item_6")
            put_completed = True
            
        put_task = asyncio.create_task(try_put())
        
        # Wait a bit - put should still be blocked
        await asyncio.sleep(0.05)
        assert not put_completed
        assert not put_task.done()
        
        # Consume one item to make space
        await queue.get()
        
        # Now put should complete
        await asyncio.sleep(0.01)
        assert put_completed
        assert put_task.done()
        
    @pytest.mark.asyncio
    async def test_queue_maxsize_enforces_backpressure(self):
        """Test that queue maxsize enforces backpressure on producers."""
        queue = asyncio.Queue(maxsize=5)  # Smaller queue for clearer backpressure
        produced = 0
        producer_blocked = False
        
        async def producer():
            nonlocal produced, producer_blocked
            for i in range(20):
                if i == 10:
                    # Check if we're blocked at this point
                    producer_blocked = (produced < 10)
                await queue.put(f"item_{i}")
                produced += 1
                
        async def slow_consumer():
            await asyncio.sleep(0.1)  # Wait before starting to consume
            for i in range(20):
                await asyncio.sleep(0.01)  # Slow consumer
                await queue.get()
                
        # Start both
        producer_task = asyncio.create_task(producer())
        consumer_task = asyncio.create_task(slow_consumer())
        
        # Wait a bit for producer to fill queue
        await asyncio.sleep(0.05)
        
        # Producer should be blocked by backpressure (queue is full)
        # It should have produced at most maxsize items
        assert produced <= 5  # Queue maxsize
        assert queue.full()
        
        # Wait for completion
        await asyncio.gather(producer_task, consumer_task)
        assert produced == 20


class TestEventPipelineLogging:
    """Test event pipeline logging requirements.
    
    Requirement 6.7: Event pipeline SHALL log all events with Session 
    identifiers and timestamps.
    """
    
    @pytest.mark.asyncio
    async def test_events_have_session_identifiers(self):
        """Test that all event types include session_id."""
        session_id = "test-session-123"
        
        # AudioFrame
        audio = AudioFrame(
            session_id=session_id,
            data=b"audio_data",
            timestamp=datetime.now(),
            sequence_number=1,
            sample_rate=16000,
            channels=1
        )
        assert audio.session_id == session_id
        
        # TranscriptEvent
        transcript = TranscriptEvent(
            session_id=session_id,
            text="test transcript",
            partial=False,
            confidence=0.95,
            timestamp=datetime.now(),
            audio_duration_ms=1000
        )
        assert transcript.session_id == session_id
        
        # LLMTokenEvent
        token = LLMTokenEvent(
            session_id=session_id,
            token="test",
            is_first=True,
            is_last=False,
            timestamp=datetime.now(),
            token_index=0
        )
        assert token.session_id == session_id
        
        # TTSAudioEvent
        tts = TTSAudioEvent(
            session_id=session_id,
            audio_data=b"tts_audio",
            timestamp=datetime.now(),
            sequence_number=1,
            is_final=False
        )
        assert tts.session_id == session_id
        
    @pytest.mark.asyncio
    async def test_events_have_timestamps(self):
        """Test that all event types include timestamps."""
        session_id = "test-session-123"
        
        # AudioFrame
        audio = AudioFrame(
            session_id=session_id,
            data=b"audio_data",
            timestamp=datetime.now(),
            sequence_number=1,
            sample_rate=16000,
            channels=1
        )
        assert isinstance(audio.timestamp, datetime)
        
        # TranscriptEvent
        transcript = TranscriptEvent(
            session_id=session_id,
            text="test transcript",
            partial=False,
            confidence=0.95,
            timestamp=datetime.now(),
            audio_duration_ms=1000
        )
        assert isinstance(transcript.timestamp, datetime)
        
        # LLMTokenEvent
        token = LLMTokenEvent(
            session_id=session_id,
            token="test",
            is_first=True,
            is_last=False,
            timestamp=datetime.now(),
            token_index=0
        )
        assert isinstance(token.timestamp, datetime)
        
        # TTSAudioEvent
        tts = TTSAudioEvent(
            session_id=session_id,
            audio_data=b"tts_audio",
            timestamp=datetime.now(),
            sequence_number=1,
            is_final=False
        )
        assert isinstance(tts.timestamp, datetime)


class TestEventPipelineIntegration:
    """Integration tests for complete event pipeline flow."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_event_flow(self):
        """Test events flow through complete pipeline maintaining order and isolation."""
        # Create session queues
        audio_queue = asyncio.Queue(maxsize=100)
        transcript_queue = asyncio.Queue(maxsize=50)
        token_queue = asyncio.Queue(maxsize=200)
        tts_queue = asyncio.Queue(maxsize=100)
        
        session_id = "test-session"
        
        # Simulate pipeline stages
        async def asr_stage():
            while True:
                try:
                    audio = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                    transcript = TranscriptEvent(
                        session_id=session_id,
                        text=f"transcript_{audio.sequence_number}",
                        partial=False,
                        confidence=0.95,
                        timestamp=datetime.now(),
                        audio_duration_ms=1000
                    )
                    await transcript_queue.put(transcript)
                except asyncio.TimeoutError:
                    break
                    
        async def llm_stage():
            while True:
                try:
                    transcript = await asyncio.wait_for(transcript_queue.get(), timeout=0.1)
                    # Extract sequence number from text
                    seq = int(transcript.text.split("_")[1])
                    token = LLMTokenEvent(
                        session_id=session_id,
                        token=f"token_{seq}",
                        is_first=True,
                        is_last=True,
                        timestamp=datetime.now(),
                        token_index=seq
                    )
                    await token_queue.put(token)
                except asyncio.TimeoutError:
                    break
                    
        async def tts_stage():
            while True:
                try:
                    token = await asyncio.wait_for(token_queue.get(), timeout=0.1)
                    tts = TTSAudioEvent(
                        session_id=session_id,
                        audio_data=f"audio_{token.token_index}".encode(),
                        timestamp=datetime.now(),
                        sequence_number=token.token_index,
                        is_final=True
                    )
                    await tts_queue.put(tts)
                except asyncio.TimeoutError:
                    break
                    
        # Start pipeline stages
        asr_task = asyncio.create_task(asr_stage())
        llm_task = asyncio.create_task(llm_stage())
        tts_task = asyncio.create_task(tts_stage())
        
        # Inject audio frames
        for i in range(5):
            audio = AudioFrame(
                session_id=session_id,
                data=f"audio_{i}".encode(),
                timestamp=datetime.now(),
                sequence_number=i,
                sample_rate=16000,
                channels=1
            )
            await audio_queue.put(audio)
            
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Cancel tasks
        asr_task.cancel()
        llm_task.cancel()
        tts_task.cancel()
        
        # Verify output
        tts_events = []
        while not tts_queue.empty():
            tts_events.append(await tts_queue.get())
            
        assert len(tts_events) == 5
        for i, tts in enumerate(tts_events):
            assert tts.sequence_number == i
            assert tts.session_id == session_id
