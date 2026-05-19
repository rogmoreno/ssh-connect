# main.py for SSH Plugin
from src.backend.PluginManager.PluginBase import PluginBase
from .SshAction import SshAction # Import your action here

from src.backend.PluginManager.ActionHolder import ActionHolder # Import your action here

class SshPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lm = self.locale_manager

        self.add_action_holder(ActionHolder(
            plugin_base = self,
            action_base = SshAction,
            action_id = "rogmoreno_ssh::SshAction",
            action_name = self.lm.get("actions.ssh.name"),
        )) # Register your action(s) here

        # Register plugin
        self.register(
            plugin_name = self.lm.get("plugin.name"),
            github_repo = "https://github.com/StreamController/ssh_plugin", # Placeholder
            plugin_version = "0.0.1", # Placeholder
            app_version = "1.0.0-alpha" # Placeholder
        )

    def on_unload(self):
        # Perform any cleanup here if necessary
        pass

    def on_load(self):
        # Perform any setup here if necessary
        pass
