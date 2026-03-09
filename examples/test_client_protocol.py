#!/usr/bin/env python3
"""
Test script to verify the client's message formatting and parsing logic.

This script tests the protocol implementation without requiring audio hardware
or a running server.
"""

import struct
from datetime import datetime


def create_audio_frame_message(audio_data: bytes, sequence_number: int) -> bytes:
    """
    Create a properly formatted audio frame message for the server.
    
    Message format:
    [8 bytes: timestamp (double, seconds since epoch)]
    [4 bytes: sequence_number (unsigned int)]
    [N bytes: audio data (PCM 16-bit)]
    """
    timestamp = datetime.now().timestamp()
    header = struct.pack('!dI', timestamp, sequence_number)
    return header + audio_data


def parse_audio_packet(packet: bytes) -> tuple[int, bool, bytes]:
    """
    Parse an audio packet from the server.
    
    Packet format:
    [4 bytes: sequence_number (unsigned int)]
    [1 byte: is_final flag (0 or 1)]
    [N bytes: audio data (PCM 16-bit)]
    """
    if len(packet) < 5:
        raise ValueError(f"Packet too short: {len(packet)} bytes")
        
    sequence_number, is_final_byte = struct.unpack('!IB', packet[:5])
    is_final = bool(is_final_byte)
    audio_data = packet[5:]
    
    return sequence_number, is_final, audio_data


def test_audio_frame_creation():
    """Test creating audio frame messages."""
    print("Testing audio frame creation...")
    
    # Create test audio data (1000 samples of 16-bit PCM)
    audio_data = b'\x00\x01' * 1000  # 2000 bytes
    
    # Create message
    message = create_audio_frame_message(audio_data, sequence_number=42)
    
    # Verify structure
    assert len(message) == 12 + 2000, f"Expected 2012 bytes, got {len(message)}"
    
    # Parse header
    timestamp, seq_num = struct.unpack('!dI', message[:12])
    
    assert seq_num == 42, f"Expected sequence 42, got {seq_num}"
    assert timestamp > 0, f"Expected positive timestamp, got {timestamp}"
    
    # Verify audio data
    assert message[12:] == audio_data, "Audio data mismatch"
    
    print(f"✓ Created message: {len(message)} bytes, seq={seq_num}, timestamp={timestamp:.3f}")


def test_audio_packet_parsing():
    """Test parsing audio packets."""
    print("\nTesting audio packet parsing...")
    
    # Create test packet
    sequence_number = 123
    is_final = True
    audio_data = b'\xFF\xFE' * 500  # 1000 bytes
    
    # Pack packet
    header = struct.pack('!IB', sequence_number, int(is_final))
    packet = header + audio_data
    
    # Parse packet
    parsed_seq, parsed_final, parsed_audio = parse_audio_packet(packet)
    
    assert parsed_seq == sequence_number, f"Expected seq {sequence_number}, got {parsed_seq}"
    assert parsed_final == is_final, f"Expected is_final={is_final}, got {parsed_final}"
    assert parsed_audio == audio_data, "Audio data mismatch"
    
    print(f"✓ Parsed packet: seq={parsed_seq}, is_final={parsed_final}, audio={len(parsed_audio)} bytes")


def test_round_trip():
    """Test round-trip encoding and decoding."""
    print("\nTesting round-trip...")
    
    # Client sends audio frame
    client_audio = b'\x12\x34' * 800  # 1600 bytes
    client_message = create_audio_frame_message(client_audio, sequence_number=1)
    
    print(f"✓ Client created message: {len(client_message)} bytes")
    
    # Server would process and respond...
    # Simulate server response
    server_audio = b'\x56\x78' * 600  # 1200 bytes
    server_packet = struct.pack('!IB', 1, 0) + server_audio
    
    # Client receives and parses
    seq, is_final, audio = parse_audio_packet(server_packet)
    
    print(f"✓ Client parsed response: seq={seq}, is_final={is_final}, audio={len(audio)} bytes")
    
    assert len(audio) == 1200, f"Expected 1200 bytes, got {len(audio)}"


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\nTesting edge cases...")
    
    # Test empty audio
    empty_message = create_audio_frame_message(b'', sequence_number=0)
    assert len(empty_message) == 12, "Empty audio should have 12-byte header"
    print("✓ Empty audio handled correctly")
    
    # Test large audio
    large_audio = b'\x00' * 100000  # 100KB
    large_message = create_audio_frame_message(large_audio, sequence_number=999)
    assert len(large_message) == 12 + 100000, "Large audio size mismatch"
    print("✓ Large audio handled correctly")
    
    # Test short packet (should raise error)
    try:
        parse_audio_packet(b'\x00\x00\x00')
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✓ Short packet rejected: {e}")
    
    # Test minimum valid packet
    min_packet = struct.pack('!IB', 0, 0)  # 5 bytes, no audio
    seq, is_final, audio = parse_audio_packet(min_packet)
    assert len(audio) == 0, "Minimum packet should have no audio"
    print("✓ Minimum packet handled correctly")


def test_sequence_numbers():
    """Test sequence number handling."""
    print("\nTesting sequence numbers...")
    
    audio = b'\x00' * 100
    
    # Test sequence progression
    for i in range(1, 11):
        message = create_audio_frame_message(audio, sequence_number=i)
        _, seq = struct.unpack('!dI', message[:12])
        assert seq == i, f"Expected seq {i}, got {seq}"
    
    print("✓ Sequence numbers 1-10 correct")
    
    # Test large sequence number
    large_seq = 2**32 - 1  # Max uint32
    message = create_audio_frame_message(audio, sequence_number=large_seq)
    _, seq = struct.unpack('!dI', message[:12])
    assert seq == large_seq, f"Expected seq {large_seq}, got {seq}"
    print(f"✓ Large sequence number {large_seq} handled correctly")


def test_is_final_flag():
    """Test is_final flag handling."""
    print("\nTesting is_final flag...")
    
    audio = b'\x00' * 100
    
    # Test is_final=False
    packet_false = struct.pack('!IB', 1, 0) + audio
    _, is_final, _ = parse_audio_packet(packet_false)
    assert is_final == False, "Expected is_final=False"
    print("✓ is_final=False parsed correctly")
    
    # Test is_final=True
    packet_true = struct.pack('!IB', 2, 1) + audio
    _, is_final, _ = parse_audio_packet(packet_true)
    assert is_final == True, "Expected is_final=True"
    print("✓ is_final=True parsed correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Voice Client Protocol Tests")
    print("=" * 60)
    
    try:
        test_audio_frame_creation()
        test_audio_packet_parsing()
        test_round_trip()
        test_edge_cases()
        test_sequence_numbers()
        test_is_final_flag()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1
        
    return 0


if __name__ == '__main__':
    exit(main())
