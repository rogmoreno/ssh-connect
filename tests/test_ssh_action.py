import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the parent directory of ssh_plugin to sys.path to allow imports like 'src.backend.PluginManager.ActionBase'
# In a real Stream Controller environment, 'src.backend' would be in the Python path already.
# This mock is for isolated testing of the plugin.
current_dir = os.path.dirname(os.path.abspath(__file__))
plugin_dir = os.path.dirname(current_dir) # Go up to ssh_plugin
rogmoreno_dir = os.path.dirname(plugin_dir) # Go up to Rogmoreno
sys.path.insert(0, rogmoreno_dir)

# Mock StreamController modules that SshAction depends on
class MockPluginBase:
    def __init__(self):
        self.PATH = plugin_dir # Simulate plugin base path

class MockActionBase:
    def __init__(self, *args, **kwargs):
        self._settings = {} # Internal storage for settings
        self.plugin_base = MockPluginBase() # Mock plugin_base

    def get_settings(self):
        return self._settings

    def set_settings(self, settings):
        self._settings = settings

    def set_media(self, media_path, size):
        pass # Mock this method
    
    def set_label(self, label):
        pass # Mock this method

# Temporarily replace the actual imports with mocks before importing SshAction
sys.modules['src.backend.PluginManager.ActionBase'] = MagicMock(return_value=MockActionBase)
sys.modules['src.backend.DeckManagement.DeckController'] = MagicMock()
sys.modules['src.backend.PageManagement.Page'] = MagicMock()
sys.modules['src.backend.PluginManager.PluginBase'] = MagicMock(return_value=MockPluginBase)

# Mock gi and Adw to prevent import errors and allow testing get_config_rows if needed later
mock_gi = MagicMock()
mock_gi.require_version.return_value = None
sys.modules['gi'] = mock_gi
sys.modules['gi.repository'] = MagicMock()
sys.modules['gi.repository.Gtk'] = MagicMock()
sys.modules['gi.repository.Adw'] = MagicMock()


# Import the SshAction class after setting up mocks
from ssh_plugin.SshAction import SshAction

# Restore original sys.path
sys.path.pop(0)

class TestSshAction(unittest.TestCase):

    def setUp(self):
        # Reset mocks before each test
        self.action = SshAction(
            id="test_action",
            name="Test Ssh Action",
            plugin_base=MockPluginBase()
        )
        # Ensure settings are clean for each test
        self.action._settings = {} 

    @patch('subprocess.Popen')
    def test_on_key_down_basic_ssh(self, mock_popen):
        self.action.set_settings({"server": "user@host"})
        self.action.on_key_down()
        mock_popen.assert_called_once_with(["gnome-terminal", "--", "ssh", "user@host"])

    @patch('subprocess.Popen')
    def test_on_key_down_with_key(self, mock_popen):
        self.action.set_settings({"server": "user@host", "key": "/path/to/key"})
        self.action.on_key_down()
        mock_popen.assert_called_once_with(["gnome-terminal", "--", "ssh", "-i", "/path/to/key", "user@host"])

    @patch('subprocess.Popen')
    def test_on_key_down_with_gui(self, mock_popen):
        self.action.set_settings({"server": "user@host", "gui": True})
        self.action.on_key_down()
        mock_popen.assert_called_once_with(["gnome-terminal", "--", "ssh", "-Y", "user@host"])

    @patch('subprocess.Popen')
    def test_on_key_down_with_custom_terminal(self, mock_popen):
        self.action.set_settings({"server": "user@host", "terminal_command": "konsole -e"})
        self.action.on_key_down()
        mock_popen.assert_called_once_with(["konsole", "-e", "--", "ssh", "user@host"])

    @patch('subprocess.Popen')
    def test_on_key_down_all_settings(self, mock_popen):
        self.action.set_settings({
            "server": "user@host",
            "key": "/path/to/key",
            "gui": True,
            "terminal_command": "xterm -T 'SSH Session'"
        })
        self.action.on_key_down()
        mock_popen.assert_called_once_with([
            "xterm", "-T", "SSH Session", "--", "ssh", "-Y", "-i", "/path/to/key", "user@host"
        ])

    @patch('subprocess.Popen')
    @patch('builtins.print') # Mock print to capture output
    def test_on_key_down_no_server(self, mock_print, mock_popen):
        self.action.set_settings({}) # No server set
        self.action.on_key_down()
        mock_popen.assert_not_called()
        mock_print.assert_called_once_with("SSH Error: Server not configured.")

    @patch('subprocess.Popen', side_effect=Exception("Terminal launch failed"))
    @patch('builtins.print')
    def test_on_key_down_terminal_launch_failure(self, mock_print, mock_popen):
        self.action.set_settings({"server": "user@host"})
        self.action.on_key_down()
        mock_popen.assert_called_once() # Popen is called, but fails
        mock_print.assert_called_once_with("Failed to launch terminal: Terminal launch failed")

    # TODO: Add tests for get_config_rows and on_setting_changed by mocking Gtk/Adw widgets
    # This is more complex due to GTK/Adw dependency, deferring for now.

if __name__ == '__main__':
    unittest.main()
