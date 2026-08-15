# tests/unit/test_audio_bus.py — Unit Tests for Single-Stream AudioBus
from __future__ import annotations

import time
import unittest
from voice.audio_bus import AudioBus, AudioFrame, AudioSubscriber, AudioBusMicrophoneSource


class TestAudioBus(unittest.TestCase):

    def setUp(self):
        self.bus = AudioBus.get_instance(sample_rate=16000, chunk_size=512)

    def test_audio_subscriber_queue_and_drain(self):
        sub = AudioSubscriber(name="test_sub", max_frames=10)
        frame = AudioFrame(
            sequence_id=1,
            timestamp=time.monotonic(),
            data=b"\x00" * 1024,
            sample_rate=16000,
            duration_ms=32.0,
            is_echo_gated=False
        )
        self.assertTrue(sub.put(frame))
        self.assertEqual(sub.qsize, 1)

        fetched = sub.get(timeout=0.1)
        self.assertEqual(fetched.sequence_id, 1)
        self.assertEqual(sub.qsize, 0)

        # Test drain
        sub.put(frame)
        sub.put(frame)
        self.assertEqual(sub.drain(), 2)
        self.assertEqual(sub.qsize, 0)

    def test_echo_gate_flag(self):
        self.bus.set_echo_gate(True)
        self.assertTrue(self.bus.is_echo_gate_active)
        self.bus.set_echo_gate(False)
        self.assertFalse(self.bus.is_echo_gate_active)

    def test_multiple_subscribers_broadcast(self):
        sub1 = self.bus.subscribe("sub_one")
        sub2 = self.bus.subscribe("sub_two")

        # Manually trigger callback with synthetic frame
        dummy_pcm = b"\x01\x00" * 512
        self.bus._audio_callback(dummy_pcm, 512, None, None)

        self.assertFalse(sub1.is_empty())
        self.assertFalse(sub2.is_empty())

        f1 = sub1.get(timeout=0.1)
        f2 = sub2.get(timeout=0.1)
        self.assertEqual(f1.sequence_id, f2.sequence_id)

        self.bus.unsubscribe("sub_one")
        self.bus.unsubscribe("sub_two")

    def test_preroll_buffer(self):
        self.bus.clear_preroll()
        dummy_pcm = b"\x02\x00" * 512
        self.bus._audio_callback(dummy_pcm, 512, None, None)
        preroll = self.bus.get_preroll_bytes()
        self.assertGreater(len(preroll), 0)
        self.bus.clear_preroll()
        self.assertEqual(len(self.bus.get_preroll_bytes()), 0)


if __name__ == "__main__":
    unittest.main()
