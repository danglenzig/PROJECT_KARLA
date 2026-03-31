# PROJECT_KARLA/src/NARRATIVE_AGENT/narrative_agent.py
"""
Narrative Agent v2.0 - Production-Ready Visual Novel Story Planner
Transforms user prompts into validated StoryPlan JSON via structured reasoning.
Part of Project Karla's Narrative Studio pipeline.

This is the new version of the narrative agent, built with LangGraph for better
structure, maintainability, and extensibility. The old version is in
narrative_agent_old.py and is kept for reference.
"""

from pathlib import Path
import json
import sys

# PROJECT_KARLA/src/
SRC_ROOT = Path(__file__).parent.parent  # src/TESTING -> src

NARRATIVE_AGENT_PATH = SRC_ROOT / "NARRATIVE_AGENT"
sys.path.insert(0, str(NARRATIVE_AGENT_PATH))
from narrative_graph import get_story_plan

plan = get_story_plan("Write a short visual novel story about a haunted library.")
plan_json_str = json.dumps(plan.__dict__, indent=2)
print(f"\n\n{plan_json_str}")
