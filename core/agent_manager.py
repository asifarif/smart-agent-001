from agents.ziauddin_agent import ZiauddinAgent

class AgentManager:
    def __init__(self):
        self.agents = [ZiauddinAgent()]

    def run_all(self):
        for agent in self.agents:
            agent.extract_programs()
