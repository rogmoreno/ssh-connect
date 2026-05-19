import os
import json
import shlex

# Import StreamController modules
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

# Import python modules
import os
import subprocess
import shutil
import glob
import configparser # Added for finding executable path
import copy # Added for deep copying settings

# Import gtk modules - used for the config rows
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class SshAction(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Enable automatic configuration dialog when button is added
        self.has_configuration = True

        # The action_id attribute is already set by the parent ActionBase class.
        # We can directly use self.action_id here.

        # Ensure the settings directory exists
        os.makedirs(os.path.join(self.plugin_base.PATH, "settings"), exist_ok=True)
        self.settings_file = os.path.join(self.plugin_base.PATH, "settings", f"{self.action_id}.json")

        # Load settings from local file or fall back to internal settings
        local_settings = {}
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    local_settings = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {self.settings_file}. Starting with empty settings.")
            except Exception as e:
                print(f"Error loading settings from {self.settings_file}: {e}")
        
        # Merge local settings with the default settings (if any, from self.get_settings())
        # The internal self.get_settings() might provide default values that our local file could override.
        # We will prioritize local_settings.
        # IMPORTANT: Use copy.deepcopy to ensure each instance has its own independent settings dictionary
        self.settings = copy.deepcopy(self.get_settings()) # Get built-in defaults as a deep copy
        self.settings.update(local_settings) # Override with locally saved settings

        # Save the current state (merged with defaults) to ensure a file is created
        self._save_settings_to_file()

    def _save_settings_to_file(self):
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=4)
            # print(f"Settings saved to {self.settings_file}") # Debug print
        except Exception as e:
            print(f"Error saving settings to {self.settings_file}: {e}")

    def on_ready(self) -> None:
        server = self.settings.get("server", "")

        icon_path = os.path.join(self.plugin_base.PATH, "assets", "ssh.png")
        if os.path.exists(icon_path):
            self.set_media(media_path=icon_path, size=0.75)
        else:
            self.set_label("SSH")

        # Show visual indicator if not configured
        if not server:
            self.set_bottom_label("No config", font_size=10)

    def _update_button_label(self) -> None:
        """Update button label based on configuration status."""
        server = self.settings.get("server", "")
        username = self.settings.get("username", "")
        execute_command_mode = self.settings.get("execute_command", False)

        if not server:
            self.set_bottom_label("No config", font_size=10)
        else:
            # Show server name or username@server
            display_text = f"{username}@{server}" if username else server
            # Truncate if too long
            if len(display_text) > 15:
                display_text = display_text[:12] + "..."

            # Add indicator for command execution mode
            if execute_command_mode:
                display_text = "CMD: " + display_text
                if len(display_text) > 18:
                    display_text = display_text[:15] + "..."

            self.set_bottom_label(display_text, font_size=9)

    def on_key_down(self) -> None:
        server = self.settings.get("server", "")
        username = self.settings.get("username", "") # Retrieve username
        key = self.settings.get("key", "")
        port_str = self.settings.get("port", "22") # Get port as string
        gui = self.settings.get("gui", False)
        terminal_cmd_setting = self.settings.get("terminal_command", "x-terminal-emulator")
        terminal_cmd_parts = shlex.split(terminal_cmd_setting)
        execute_command_mode = self.settings.get("execute_command", False)
        remote_command = self.settings.get("remote_command", "")

        if not server:
            print("SSH Error: Server not configured. Please configure the SSH server in the button settings.")
            self.show_error(duration=2)
            return

        cmd = ["ssh"]

        try:
            port = int(port_str)
            if port != 22:
                cmd.extend(["-p", str(port)])
        except ValueError:
            print(f"Warning: Invalid port number '{port_str}'. Using default SSH port or none if error persists.")

        if gui:
            cmd.append("-Y")
        if key:
            cmd.extend(["-i", key])

        # Prepend username to server if provided
        target_server = f"{username}@{server}" if username else server
        cmd.append(target_server)

        # Check if we should execute a command instead of opening an interactive terminal
        if execute_command_mode and remote_command:
            # Execute command mode
            cmd.append(remote_command)
            self._execute_remote_command(cmd)
        else:
            # Interactive terminal mode
            ssh_command_str = " ".join(cmd)
            terminal_executable = terminal_cmd_parts[0]

            resolved_terminal_path = None

            # 1. Try to resolve via .desktop files (most robust for GUI apps)
            resolved_terminal_path = self._get_terminal_exec_path(terminal_executable)

            if resolved_terminal_path:
                print(f"Resolved terminal path via .desktop: {resolved_terminal_path}")
                self._launch_terminal_with_ssh(resolved_terminal_path, ssh_command_str, use_shell=False)
                return

            # 2. If not resolved via .desktop, try shutil.which as a path
            print(f"Could not resolve terminal path via .desktop for '{terminal_executable}'. Trying shutil.which.")
            full_terminal_path_from_which = shutil.which(terminal_executable)

            if full_terminal_path_from_which:
                print(f"Resolved terminal path via shutil.which: {full_terminal_path_from_which}")
                self._launch_terminal_with_ssh(full_terminal_path_from_which, ssh_command_str, use_shell=False)
                return

            # 3. Final fallback: use original terminal_executable with shell=True
            print(f"Could not resolve terminal path. Falling back to shell execution of original command '{terminal_executable}'.")
            self._launch_terminal_with_ssh(terminal_executable, ssh_command_str, use_shell=True)

    def on_setting_changed(self, widget, first_arg_from_signal, *remaining_args):
        # print(f"on_setting_changed called for widget: {type(widget)}, first_arg: {first_arg_from_signal}, remaining_args: {remaining_args}")
        actual_setting_key = None
        new_value = None

        if isinstance(widget, Adw.EntryRow):
            actual_setting_key = first_arg_from_signal
            new_value = widget.get_text()
        elif isinstance(widget, Adw.SwitchRow):
            actual_setting_key = remaining_args[0]
            new_value = widget.get_active()

        if actual_setting_key:
            # print(f"  Updating: setting_key={actual_setting_key}, new_value={new_value}") # Debug print
            # Directly update self.settings - no need for intermediate variable
            self.settings[actual_setting_key] = new_value

            # Save the updated settings to our local file
            self._save_settings_to_file()
            # print(f"Settings after save: {self.settings}") # Debug print

            # Update visual indicator when server is configured
            self._update_button_label()
        else:
            print(f"  Warning: Could not determine actual_setting_key for widget type: {type(widget)}")

    def get_config_rows(self) -> list:
        # Username Entry
        self.username_row = Adw.EntryRow()
        self.username_row.set_title("SSH Username (Optional)")
        self.username_row.set_text(self.settings.get("username", ""))
        self.username_row.connect("changed", self.on_setting_changed, "username")

        # Server Entry
        self.server_row = Adw.EntryRow()
        self.server_row.set_title("SSH Server")
        self.server_row.set_text(self.settings.get("server", ""))
        self.server_row.connect("changed", self.on_setting_changed, "server")

        # SSH Key Entry
        self.key_row = Adw.EntryRow()
        self.key_row.set_title("SSH Key Path")
        self.key_row.set_text(self.settings.get("key", ""))
        self.key_row.connect("changed", self.on_setting_changed, "key")
        
        # SSH Port Entry
        self.port_row = Adw.EntryRow()
        self.port_row.set_title("SSH Port")
        self.port_row.set_text(self.settings.get("port", "22"))
        self.port_row.set_input_purpose(Gtk.InputPurpose.DIGITS)
        self.port_row.connect("changed", self.on_setting_changed, "port")
        
        # GUI Switch
        self.gui_switch = Adw.SwitchRow()
        self.gui_switch.set_title("Enable GUI (X11 Forwarding)")
        self.gui_switch.set_active(self.settings.get("gui", False))
        self.gui_switch.connect("notify::active", self.on_setting_changed, "gui")

        # Terminal Command Entry
        self.terminal_row = Adw.EntryRow()
        print(dir(self.terminal_row))
        self.terminal_row.set_title("Terminal Command")
        self.terminal_row.set_text(self.settings.get("terminal_command", "gnome-terminal"))
        print("Attempting to get child of terminal_row for placeholder text.")
        
        # Access the internal Gtk.Entry to set placeholder text
        inner_box = self.terminal_row.get_child() # This is expected to be a Gtk.Box
        print(f"Type of inner_box: {type(inner_box)}")
        print(f"Dir of inner_box: {dir(inner_box)}")

        if inner_box and hasattr(inner_box, 'get_children'):
            for child_widget in inner_box.get_children():
                print(f"Child widget type: {type(child_widget)}")
                if not isinstance(child_widget, Gtk.Entry):
                    print(f"Dir of child widget (not Gtk.Entry): {dir(child_widget)}")
                if isinstance(child_widget, Gtk.Entry):
                    child_widget.set_placeholder_text("e.g., gnome-terminal, konsole, xterm")
                    break
        else:
            print("Warning: Could not find internal Gtk.Entry to set placeholder text for Adw.EntryRow.")

        self.terminal_row.connect("changed", self.on_setting_changed, "terminal_command")

        # Execute Command Switch
        self.execute_command_switch = Adw.SwitchRow()
        self.execute_command_switch.set_title("Execute Command Mode")
        self.execute_command_switch.set_subtitle("Execute a command instead of opening an interactive terminal")
        self.execute_command_switch.set_active(self.settings.get("execute_command", False))
        self.execute_command_switch.connect("notify::active", self.on_setting_changed, "execute_command")

        # Remote Command Entry
        self.remote_command_row = Adw.EntryRow()
        self.remote_command_row.set_title("Remote Command")
        self.remote_command_row.set_text(self.settings.get("remote_command", ""))
        self.remote_command_row.connect("changed", self.on_setting_changed, "remote_command")

        return [
            self.username_row,
            self.server_row,
            self.key_row,
            self.port_row,
            self.gui_switch,
            self.terminal_row,
            self.execute_command_switch,
            self.remote_command_row
        ]

    def _get_terminal_exec_path(self, terminal_name):
        desktop_files = glob.glob("/usr/share/applications/*.desktop")
        desktop_files += glob.glob(os.path.expanduser("~/.local/share/applications/*.desktop"))

        for desktop_file in desktop_files:
            config = configparser.ConfigParser(interpolation=None)
            try:
                config.read(desktop_file)
                entry = config['Desktop Entry']
                name = entry.get('Name')
                exec_cmd = entry.get('Exec')

                # Clean the Exec command (remove %u, %f, etc.)
                if exec_cmd:
                    exec_cmd = exec_cmd.split(' ')[0].strip() # Get only the executable part
                    
                # Check if the desktop entry's name or exec command matches the terminal_name
                # This might need refinement based on how the user names their terminals
                if name and name.lower() == terminal_name.lower() and exec_cmd:
                    return exec_cmd
                if exec_cmd and os.path.basename(exec_cmd).lower() == terminal_name.lower():
                    return exec_cmd
            except KeyError:
                continue
            except configparser.Error:
                # Handle malformed .desktop files
                continue
        return None

    def _execute_remote_command(self, ssh_cmd):
        """Execute a command on the remote host and display the output in a terminal window."""
        terminal_cmd_setting = self.settings.get("terminal_command", "x-terminal-emulator")
        terminal_cmd_parts = shlex.split(terminal_cmd_setting)
        terminal_executable = terminal_cmd_parts[0]

        # Build the SSH command as a string
        ssh_command_str = " ".join(shlex.quote(arg) for arg in ssh_cmd)

        # Wrap the command to keep the terminal open after execution
        # We use 'bash -c' to execute the command and then wait for user input
        command_with_pause = f"{ssh_command_str}; echo ''; echo 'Press Enter to close...'; read"
        quoted_command = shlex.quote(command_with_pause)
        command_to_execute = f"bash -c {quoted_command}"

        print(f"Executing remote command: {ssh_command_str}")

        resolved_terminal_path = None

        # Try to resolve terminal path
        resolved_terminal_path = self._get_terminal_exec_path(terminal_executable)

        if not resolved_terminal_path:
            resolved_terminal_path = shutil.which(terminal_executable)

        if not resolved_terminal_path:
            resolved_terminal_path = terminal_executable

        is_flatpak_env = is_in_flatpak()

        try:
            command_list = [resolved_terminal_path, "-e", command_to_execute]
            if is_flatpak_env:
                command_list.insert(0, "--host")
                command_list.insert(0, "flatpak-spawn")

            subprocess.Popen(command_list, start_new_session=True, cwd=os.path.expanduser("~"))
            print("Remote command executed successfully.")
        except Exception as e:
            print(f"Failed to execute remote command: {e}")
            self.show_error(duration=2)

    def _launch_terminal_with_ssh(self, terminal_executable_path, ssh_command_str, use_shell=False):
        # The key change is here: wrap ssh_command_str in `bash -c "..."`
        # This makes the command explicitly a shell command for the terminal emulator to run.
        quoted_ssh_command_for_bash = shlex.quote(ssh_command_str)
        command_to_execute_in_terminal = f"bash -c {quoted_ssh_command_for_bash}"

        print(f"Attempting to launch: {terminal_executable_path} -e '{command_to_execute_in_terminal}' (use_shell={use_shell})")

        is_flatpak_env = is_in_flatpak()

        try:
            if use_shell:
                # When use_shell=True, subprocess expects a single string command.
                # flatpak-spawn needs to be prepended to this string.
                # The full string will be: terminal_executable_path -e "bash -c 'ssh ...'"
                full_command_str = f"{terminal_executable_path} -e {shlex.quote(command_to_execute_in_terminal)}"
                if is_flatpak_env:
                    full_command_str = f"flatpak-spawn --host {full_command_str}"
                subprocess.Popen(full_command_str, shell=True, start_new_session=True, cwd=os.path.expanduser("~"))
            else:
                # When use_shell=False, subprocess expects a list of arguments.
                # flatpak-spawn --host needs to be the first elements of the list.
                command_list = [terminal_executable_path, "-e", command_to_execute_in_terminal]
                if is_flatpak_env:
                    command_list.insert(0, "--host")
                    command_list.insert(0, "flatpak-spawn")
                subprocess.Popen(command_list, start_new_session=True, cwd=os.path.expanduser("~"))
            print("Terminal launched successfully.")
        except Exception as e:
            print(f"Failed to launch terminal: {e}")

def is_in_flatpak() -> bool:
    return os.path.isfile('/.flatpak-info')
