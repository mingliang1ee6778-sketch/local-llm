from backend.agents.base import BaseAgent


class USIMAgent(BaseAgent):
    mode = "usim"
    prompt_file = "usim.txt"
