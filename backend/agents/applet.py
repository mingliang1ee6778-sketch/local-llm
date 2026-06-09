from backend.agents.base import BaseAgent


class AppletAgent(BaseAgent):
    mode = "applet"
    prompt_file = "applet.txt"
