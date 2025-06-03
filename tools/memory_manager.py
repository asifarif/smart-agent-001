# tools/memory_manager.py

import json
import os
from deepdiff import DeepDiff

def save_memory(agent_name, data, kind="output"):
    os.makedirs(f"memory/{agent_name}", exist_ok=True)
    with open(f"memory/{agent_name}/{kind}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_memory(agent_name, kind="output"):
    path = f"memory/{agent_name}/{kind}.json"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []

def compare_outputs(agent_name):
    raw = load_memory(agent_name, "output")
    corrected = load_memory(agent_name, "corrected")
    diff = DeepDiff(raw, corrected, ignore_order=True)
    
    with open(f"memory/{agent_name}/diffs.json", "w", encoding="utf-8") as f:
        json.dump(diff, f, indent=2)
    
    return diff
