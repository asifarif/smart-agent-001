from agents.ziauddin_agent import ZiauddinAgent

def test_extract_programs():
    agent = ZiauddinAgent()
    programs = agent.extract_programs()
    assert isinstance(programs, list)
    assert len(programs) > 0
