import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestAudioDucking(unittest.TestCase):
    @patch('pygame.mixer.init')
    @patch('pygame.mixer.music.get_busy')
    @patch('pygame.mixer.music.get_volume')
    @patch('pygame.mixer.music.set_volume')
    @patch('pygame.mixer.Sound')
    @patch('pygame.mixer.Channel')
    @patch('voice.tts_engine.TTSEngine._synthesize')
    def test_ducking_logic(self, mock_synth, mock_channel_cls, mock_sound_cls, mock_set_vol, mock_get_vol, mock_busy, mock_init):
        from voice.tts_engine import TTSEngine
        import time
        import threading
        
        # Setup mocks
        mock_busy.return_value = True
        mock_get_vol.return_value = 0.8
        mock_channel = MagicMock()
        mock_channel_cls.return_value = mock_channel
        mock_channel.get_busy.side_effect = [True, False] # Busy then done
        
        engine = TTSEngine()
        
        # We need to wait for the thread
        engine.speak("Test")
        
        # Give it a moment to run the thread
        time.sleep(1.0)
        
        # Verify ducking called
        mock_set_vol.assert_any_call(0.8 * 0.2) # Initial ducking
        mock_set_vol.assert_any_call(0.8) # Restoration
        
        # Verify channel play called
        mock_channel.play.assert_called()
        print("✅ SUCCESS: Audio ducking and channel play verified.")

if __name__ == "__main__":
    unittest.main()
