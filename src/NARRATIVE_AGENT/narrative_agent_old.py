# PROJECT_KARLA/src/NARRATIVE_AGENT/narrative_agent_old.py
"""
Narrative Agent v2.0 - Production-Ready Visual Novel Story Planner
Transforms user prompts into validated StoryPlan JSON via structured reasoning.
Part of Project Karla's Narrative Studio pipeline.

DEPRECATED: This is the old version of the narrative agent, kept for reference. The new version is in narrative_agent.py and uses LangGraph for better structure and maintainability.

"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI

CLI_MODE: bool = True

# PROJECT_KARLA/src/
SRC_ROOT = Path(__file__).parent.parent  # src/TESTING -> src

# PROJECT_KARLA/src/utility_functions/
UTILITY_PATH = SRC_ROOT / "utility_functions" 
sys.path.insert(0, str(UTILITY_PATH))

# PROJECT_KARLA/src/qdrant_tools/
QDRANT_PATH = SRC_ROOT / "qdrant_tools"
sys.path.insert(0, str(QDRANT_PATH))

# PROJECT_KARLA/src/prompt_builder
PROMPT_BLDR_PATH = SRC_ROOT / "prompt_builder"
sys.path.insert(0, str(PROMPT_BLDR_PATH))

# PROJECT_KARLA/src/core_data_models
CORE_DATA_MODELS_PATH = SRC_ROOT / "core_data_models"
sys.path.insert(0, str(CORE_DATA_MODELS_PATH))

from utility_functions import timer, load_schema, foo, validate_story_plan
from qdrant_tools import qdrant_foo, search_genre_examples, search_genre_howto
from prompt_builder import prompt_builder_foo, build_system_prompt
from core_data_models import dm_foo, StepType, ReasoningStep, StoryPlan, AgentConfig



# print(foo()) # should print "bar"
# print(qdrant_foo()) # --> "qdrant_bar"
# print(prompt_builder_foo()) # --> "prompt_builder_bar"
# print(dm_foo()) # -->

# configure logging first -- production best practice
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("narrative_agent.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("narrative_agent")

# load environment variables
load_dotenv()

AGENT_CONFIG = AgentConfig(
    "narrative_agent",
    "gpt-4.1",
    #"gpt-4o-mini"
    "http://localhost:6333",
    20, 4000
)
logger.info(f"AgentConfig loaded: {AGENT_CONFIG.agent_name}")

TOOLS = {
    "search_genre_howto": search_genre_howto,
    "search_genre_examples": search_genre_examples
}

# =============================================================================
# NARRATIVE AGENT (Main Logic)
# =============================================================================

class NarrativeAgent:
    """Production narrative planning agent."""
    def __init__(self, agent_config_: AgentConfig):
        self.agent_config = agent_config_
        self.openai_client = OpenAI()
        self.messages_: List[Dict[str, str]] = []
        self.iteration = 0
        self.messages_.append(
            {"role": "system", "content": build_system_prompt(self.agent_config.agent_name)}
        )

    
    def process_user_input(self, prompt: str) -> StoryPlan:
        """Prompt -> Narrative Spec"""
        self.messages_.append(
            {"role": "user", "content": prompt}
        )
        self.iteration = 0

        with timer("Full reasoning"):
            while self.iteration < self.agent_config.max_iterations:
                self.iteration += 1
                step = self._take_step()

                if step.step == StepType.OUTPUT:
                    return self._handle_output(step)
                elif step.step == StepType.TOOL:
                    self._handle_tool_call(step)
            raise RuntimeError(f"Max iterations exceeded")
    
    def _take_step(self) -> ReasoningStep:

        response = self.openai_client.chat.completions.create(
            model = self.agent_config.openai_model,

            messages = self.messages_,

            # not supported on mini
            # max_tokens = self.config.max_tokens,
            # temperature = 0.1
        )

        raw_content = response.choices[0].message.content
        self.messages_.append(
            {"role": "assistant", "content": raw_content}
        )

        # tolerant parsing
        try:
            # Case 1: Proper ReasoningStep (your prompt works)
            step = ReasoningStep.model_validate_json(raw_content)
        except ValidationError:
        # Case 2: LLM output StoryPlan JSON directly (crash cause)
            logger.warning("LLM skipped wrapper - forcing OUTPUT step")
            step = ReasoningStep(
                step=StepType.OUTPUT,
                content=raw_content,  # Raw StoryPlan JSON
                tool=None, 
                tool_input=None, 
                tool_output=None
            )
        logger.info(f"Iter {self.iteration}: {step.step}, \nCONTENT:\n{step.content}\n")

        return step
    
    def _handle_tool_call(self, step: ReasoningStep):
        """Execute + inject OBSERVE"""
        _tool_name = step.tool
        _tool_input_dict = json.loads(step.tool_input)
        _tool_fn = TOOLS[_tool_name]
        _result = _tool_fn(_tool_input_dict["genre_name"], _tool_input_dict["search_query"])

        observe_step = ReasoningStep(
            step = StepType.OBSERVE,
            content = "Tool results processed",
            tool = _tool_name,
            tool_input = step.tool_input,
            tool_output = _result
        )
        self.messages_.append(
            {"role": "assistant", "content": observe_step.model_dump_json()}
        )

    def _handle_output(self, step: ReasoningStep)->str:
        """Final validation"""

        # try:
        #     model_data = validate_story_plan(step.content)
        #     plan = StoryPlan(**model_data)
        #     return step.content
        # except Exception as e:
        #     print(f"INVALID STORY PLAN, Error: {e}")
        #     return "INVALID STORY PLAN"
        
        model_data = validate_story_plan(step.content)
        plan = StoryPlan(**model_data)
        logger.info("StoryPlan validated")
        return plan
    

def get_story_plan(user_prompt: str):
    agent = NarrativeAgent(AGENT_CONFIG)
    #plan: StoryPlan = agent.process_user_input(user_prompt.strip())
    plan: str= agent.process_user_input(user_prompt.strip()) # this is just a string now
    return plan
    
def main():

    if not CLI_MODE:
        return

    # for CLI testing

    print("🎭 Narrative Agent v2.1 - Enter prompts below:")
    agent = NarrativeAgent(AGENT_CONFIG)

    try:
        while True:
            prompt = input("---> ").strip()
            if not prompt:
                continue

            print("Thinking...")
            plan = agent.process_user_input(prompt) # this is just a string now

            print("\n---STORY PLAN---\n")
            #print(json.dumps(plan.__dict__, indent=2))
            print(plan)



    except KeyboardInterrupt:
        print("\nExiting")
    except Exception as e:
        logger.error(f"Fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
