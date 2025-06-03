import pytest
from agents.iqra_agent import IqraAgent
from database.supabase_client import SupabaseClient
from unittest.mock import MagicMock

def test_compare_outputs():
    supabase_client = MagicMock()
    supabase_client.get_corrected_programs.return_value = {}
    agent = IqraAgent(supabase_client)

    agent_output = [
        {"program_name": "BS Computer Science", "category": "undergraduate", "admission_open": False, "deadlines": []}
    ]
    corrected_output = [
        {"program_name": "BS Computer Science", "category": "undergraduate", "admission_open": True, "deadlines": ["2025-12-31"]}
    ]

    differences = agent.compare_outputs(agent_output, corrected_output)
    assert len(differences) == 1
    assert differences[0]["program_name"] == "BS Computer Science"
    assert agent.known_programs["BS Computer Science"]["admission_open"] is True
    assert agent.known_programs["BS Computer Science"]["deadlines"] == ["2025-12-31"]