# SSH Plugin

This plugin provides a convenient way to establish SSH connections to remote servers directly from the Stream Controller application. It launches your preferred terminal emulator and executes an SSH command with configurable parameters, simplifying the process of connecting to various environments.

## Features

*   **Configurable SSH Parameters:** Easily set the target SSH server, username, authentication key file path, and port.
*   **X11 Forwarding Support:** Option to enable X11 forwarding for graphical applications (`-Y` flag).
*   **Customizable Terminal Emulator:** Specify your preferred terminal application (e.g., `gnome-terminal`, `konsole`, `xterm`) to launch the SSH session.
*   **Automatic Terminal Detection:** Attempts to resolve the terminal executable path using `.desktop` files and system PATH.
*   **Flatpak Compatibility:** Includes support for launching commands within Flatpak environments.

## Usage

Once the plugin is installed and configured, activating the SSH action will open a new terminal window on your system, establishing an SSH connection to the specified server using the provided credentials and settings.

### Configuration

The SSH action offers the following configuration options within its settings:

*   **SSH Username (Optional):** The username to use for the SSH connection.
*   **SSH Server:** The hostname or IP address of the remote SSH server.
*   **SSH Key Path:** The absolute path to your SSH private key file (e.g., `~/.ssh/id_rsa`).
*   **SSH Port:** The port number for the SSH connection (defaults to `22`).
*   **Enable GUI (X11 Forwarding):** A toggle to enable X11 forwarding (equivalent to `ssh -Y`).
*   **Terminal Command:** The command used to launch your desired terminal emulator. Examples: `gnome-terminal`, `konsole`, `xterm`.

