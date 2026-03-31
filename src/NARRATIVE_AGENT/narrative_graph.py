# PROJECT_KARLA/src/NARRATIVE_AGENT/narrative_graph.py
"""
Narrative Graph Module - Core Logic for Story Plan Generation
Defines the NarrativeGraph class that orchestrates the transformation of
user prompts into structured StoryPlan JSON.
"""

import sys
import json
from pathlib import Path
from typing import TypedDict, Annotated, Sequence, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from dotenv import load_dotenv

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

from utility_functions import validate_story_plan, timer
from qdrant_tools import search_genre_examples, search_genre_howto
from prompt_builder import build_system_prompt # TODO: will simplify later
from core_data_models import AgentConfig, StoryPlan

load_dotenv()

AGENT_CONFIG = AgentConfig(
    "narrative_agent",
    #"gpt-4.1",
    "gpt-4.1-mini",
    "http://localhost:6333",
    20, 4000
)

# =============================================================================
# GRAPH STATE
# =============================================================================

class GraphState(TypedDict):
    """Explicit state for the narrative graph."""
    user_prompt: str
    messages: Annotated[Sequence[BaseModel], add_messages] # chat history with tool calls and observations
    genre: str # "romance", "horror", etc. -- used to condition tool calls and final output
    research: str # tool results
    story_plan: str # raw JSON
    validation_errors: list[str] # if validation fails, store errors here

# =============================================================================
# NARRATIVE GRAPH
# =============================================================================

class NarrativeGraph:
    """LangGraph-powered narrative planning agent."""
    def __init__(self, config: AgentConfig):
        self.config = config
        self.graph = self._build_graph()
        self.app = self.graph.compile()
    
    def _build_graph(self) -> StateGraph:
        """Define the graph structure"""
        workflow = StateGraph(GraphState)

        # Node 1: Classify the genre from the user prompt
        def classify_genre(state: GraphState) -> GraphState:
            """Classify the genre from the user prompt."""
            from openai import OpenAI
            client = OpenAI()
            # NOTE: update the genre list when new genre tools are added
            prompt = f"""
            CLASSIFY THE GENRE for this visual novel prompt only.
            User Prompt: {state['user_prompt']}

            Choose EXACTLY ONE from: "romance", "horror", "mystery"

            Respond with ONLY the genre name as plain text, nothing else.
            """

            response = client.chat.completions.create(
                model = self.config.openai_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )

            genre = response.choices[0].message.content.strip().lower()
            # Failsafe
            if genre not in [
                "romance", "horror", "mystery"
            ]:
                genre = "horror" # default to horror if classification fails for some reason

            return {
                "genre": genre,
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"Classified genre as {genre}."
                    }
                ]
            }
        
        # Node 2: Research the genre using tools
        def research_genre(state: GraphState) -> GraphState:
            """Call both how-to and examples tools for the classified genre."""
            genre = state["genre"]
            
            # call tools
            howto_result = search_genre_howto(genre, state["user_prompt"])
            examples_result = search_genre_examples(genre, state["user_prompt"])

            research = f"""
            HOWTO RESULT:
            {howto_result}:
            EXAMPLES RESULT:
            {examples_result}
            """

            return {
                "research": research,
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"Used tools to research genre {genre}: howto and examples retrieved."
                    }
                ]
            }
        
        # Node 3 Draft the story plan based on the research and user prompt
        def  draft_story_plan(state: GraphState) -> GraphState:
            """Draft the story plan based on the research and user prompt."""
            from openai import OpenAI
            client = OpenAI()

            prompt = build_system_prompt("draft_story", state["genre"], state["research"], state["user_prompt"])

            response = client.chat.completions.create(
                model= self.config.openai_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature = 0.7,
                max_tokens = self.config.max_tokens
            )

            story_json = response.choices[0].message.content.strip()
            return {
                "story_plan": story_json,
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"Drafted story plan based on research and user prompt."
                    }
                ]
            }



        workflow.add_node("classify_genre", classify_genre)
        workflow.add_node("research_genre", research_genre)
        workflow.add_node("draft_story_plan", draft_story_plan)


        # START -> classify_genre -> research_genre -> draft_story_plan -> END
        workflow.set_entry_point("classify_genre")
        workflow.add_edge("classify_genre", "research_genre")
        workflow.add_edge("research_genre", "draft_story_plan")
        workflow.add_edge("draft_story_plan", END)

        return workflow

    def generate_story_plan(self, user_prompt: str) -> StoryPlan:
        """Main entry point: prompt -> StoryPlan"""
        with timer("LangGraph Generation"):
            result = self.app.invoke({
                "user_prompt": user_prompt,
                "messages": [],
                "genre": "",
                "research": "",
                "story_plan": "",
                "validation_errors": []
            })
        
        # Extract and validate
        raw_plan = result["story_plan"]

        print("=== DEBUG GRAPH RESULT ===")
        for k,v in result.items():
            if isinstance(v, str) and len(v) > 100:
                print(f"{k}: {v[:100]}...") # print only the first 100 chars of long strings
            else:
                print(f"{k}: {v}")
        print("==========================")

        model_data = validate_story_plan(raw_plan)
        return StoryPlan(**model_data) # NOTE to self: **double_asterisk unpacks the dict into keyword args for the StoryPlan constructor
    
# Entry point for testing
def get_story_plan(user_prompt: str) -> StoryPlan:
    graph = NarrativeGraph(AGENT_CONFIG)
    return graph.generate_story_plan(user_prompt)

def ng_foo():
    print("ng BAR")

if __name__ == "__main__":
    print("Narrative Graph skeleton ready!")
    print("Test with: get_story_plan('Write a short visual novel story about a cursed nursing home.')")