from backend.agents.base import BaseAgent


class COSAgent(BaseAgent):
    mode = "cos"
    prompt_file = "cos.txt"
