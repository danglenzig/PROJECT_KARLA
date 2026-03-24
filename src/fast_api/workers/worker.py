import sys
from pathlib import Path
import json

# from the project root, run:
# PYTHONPATH=src rq worker


# PROJECT_KARLA/src/
SRC_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SRC_ROOT))

# PROJECT_KARLA/src/"NARRATIVE_AGENT"
NARRATIVE_AGENT_PATH = SRC_ROOT / "NARRATIVE_AGENT"
sys.path.insert(0, str(NARRATIVE_AGENT_PATH))

# PROJECT_KARLA/src/core_data_models
CORE_DATA_MODELS_PATH = SRC_ROOT / "core_data_models"
sys.path.insert(0, str(CORE_DATA_MODELS_PATH))

from NARRATIVE_AGENT import get_story_plan
from core_data_models import StoryPlan

def story_plan(user_prompt: str):
    plan: StoryPlan = get_story_plan(user_prompt)
    # return json.dumps(
    #     plan.__dict__,
    #     indent=None
    #     ##indent=2
    # )
    return plan



# testing...
# input = "Write a story about a group of satanic cult cheerleaders"
# print(story_plan(input))
# ^^this works as expected (back end is all fine)