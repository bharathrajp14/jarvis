# tests/unit/test_voice_state_machine.py — Unit Tests for Voice State Machine
from __future__ import annotations

import unittest
from voice.state_machine import VoiceStateMachine, VoiceState, VoiceErrorType


class TestVoiceStateMachine(unittest.TestCase):

    def setUp(self):
        self.sm = VoiceStateMachine(initial_state=VoiceState.IDLE)

    def test_initial_state(self):
        self.assertEqual(self.sm.current_state, VoiceState.IDLE)
        self.assertEqual(self.sm.last_error, VoiceErrorType.NONE)

    def test_valid_transitions(self):
        # IDLE -> WAKE_DETECTION -> WAKE_CONFIRMED -> LISTENING_FOR_COMMAND -> CAPTURING -> TRANSCRIBING -> UNDERSTANDING -> EXECUTING -> SPEAKING -> IDLE
        self.assertTrue(self.sm.transition_to(VoiceState.WAKE_DETECTION))
        self.assertEqual(self.sm.current_state, VoiceState.WAKE_DETECTION)

        self.assertTrue(self.sm.transition_to(VoiceState.WAKE_CONFIRMED))
        self.assertEqual(self.sm.current_state, VoiceState.WAKE_CONFIRMED)

        self.assertTrue(self.sm.transition_to(VoiceState.LISTENING_FOR_COMMAND))
        self.assertEqual(self.sm.current_state, VoiceState.LISTENING_FOR_COMMAND)

        self.assertTrue(self.sm.transition_to(VoiceState.CAPTURING))
        self.assertEqual(self.sm.current_state, VoiceState.CAPTURING)

        self.assertTrue(self.sm.transition_to(VoiceState.TRANSCRIBING))
        self.assertEqual(self.sm.current_state, VoiceState.TRANSCRIBING)

        self.assertTrue(self.sm.transition_to(VoiceState.UNDERSTANDING))
        self.assertEqual(self.sm.current_state, VoiceState.UNDERSTANDING)

        self.assertTrue(self.sm.transition_to(VoiceState.EXECUTING))
        self.assertEqual(self.sm.current_state, VoiceState.EXECUTING)

        self.assertTrue(self.sm.transition_to(VoiceState.SPEAKING))
        self.assertEqual(self.sm.current_state, VoiceState.SPEAKING)

        self.assertTrue(self.sm.transition_to(VoiceState.IDLE))
        self.assertEqual(self.sm.current_state, VoiceState.IDLE)

    def test_invalid_transition_rejected(self):
        # SPEAKING -> TRANSCRIBING is not valid directly
        self.sm.transition_to(VoiceState.WAKE_DETECTION)
        self.sm.transition_to(VoiceState.WAKE_CONFIRMED)
        self.sm.transition_to(VoiceState.LISTENING_FOR_COMMAND)
        self.sm.transition_to(VoiceState.CAPTURING)
        self.sm.transition_to(VoiceState.TRANSCRIBING)
        self.sm.transition_to(VoiceState.UNDERSTANDING)
        self.sm.transition_to(VoiceState.EXECUTING)
        self.sm.transition_to(VoiceState.SPEAKING)

        # Invalid transition should return False
        self.assertFalse(self.sm.transition_to(VoiceState.TRANSCRIBING))
        self.assertEqual(self.sm.current_state, VoiceState.SPEAKING)

    def test_barge_in_interruption_transition(self):
        # SPEAKING -> INTERRUPTED -> CAPTURING
        self.sm.transition_to(VoiceState.WAKE_DETECTION)
        self.sm.transition_to(VoiceState.WAKE_CONFIRMED)
        self.sm.transition_to(VoiceState.LISTENING_FOR_COMMAND)
        self.sm.transition_to(VoiceState.CAPTURING)
        self.sm.transition_to(VoiceState.TRANSCRIBING)
        self.sm.transition_to(VoiceState.UNDERSTANDING)
        self.sm.transition_to(VoiceState.EXECUTING)
        self.sm.transition_to(VoiceState.SPEAKING)

        self.assertTrue(self.sm.transition_to(VoiceState.INTERRUPTED))
        self.assertEqual(self.sm.current_state, VoiceState.INTERRUPTED)

        self.assertTrue(self.sm.transition_to(VoiceState.CAPTURING))
        self.assertEqual(self.sm.current_state, VoiceState.CAPTURING)

    def test_error_state_and_classification(self):
        self.sm.set_error(VoiceErrorType.MICROPHONE_DISCONNECTED, "USB device detached")
        self.assertEqual(self.sm.current_state, VoiceState.ERROR)
        self.assertEqual(self.sm.last_error, VoiceErrorType.MICROPHONE_DISCONNECTED)
        self.assertIn("USB device", self.sm.error_message)

        self.sm.clear_error()
        self.assertEqual(self.sm.last_error, VoiceErrorType.NONE)

    def test_listeners_notification(self):
        events = []

        def on_change(old_st, new_st, ctx):
            events.append((old_st, new_st))

        self.sm.add_listener(on_change)
        self.sm.transition_to(VoiceState.WAKE_DETECTION)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], (VoiceState.IDLE, VoiceState.WAKE_DETECTION))


if __name__ == "__main__":
    unittest.main()
