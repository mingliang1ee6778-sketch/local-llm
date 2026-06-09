from backend.agents.applet import AppletAgent
from backend.agents.base import BaseAgent
from backend.agents.cos import COSAgent
from backend.agents.usim import USIMAgent
from backend.schemas import Mode


def get_agent(mode: Mode, settings) -> BaseAgent:
    agents = {
        "applet": AppletAgent,
        "cos": COSAgent,
        "usim": USIMAgent,
    }
    return agents[mode](settings)
