import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class AlexaVerification(unittest.TestCase):
    @patch('voice.tts_engine.speak')
    @patch('utils.EventBus')
    def test_wake_confirmation(self, mock_eb_cls, mock_speak):
        """Verify JARVIS says 'Yes, sir?' when wake word is heard."""
        from voice.voice_input import VoiceListener
        eb = mock_eb_cls()
        listener = VoiceListener(eb)
        
        # Simulate wake word logic
        listener._on_jarvis_wake()
        
        # Assertions
        mock_speak.assert_called_with("Yes, sir?")
        print("✅ SUCCESS: Wake word confirmation verified.")

    @patch('voice.tts_engine.speak')
    @patch('utils.EventBus')
    def test_narration_presence(self, mock_eb_cls, mock_speak):
        """Verify InteractionLoop narrates actions."""
        from core.interaction_loop import InteractionLoop
        eb = mock_eb_cls()
        loop = InteractionLoop(eb)
        
        loop.narrate_action("open_app", "Discord")
        
        # Should have called speak with some version of "Launching Discord"
        self.assertTrue(any("Discord" in c.args[0] for c in mock_speak.call_args_list))
        print("✅ SUCCESS: Action narration verified.")

if __name__ == "__main__":
    unittest.main()
