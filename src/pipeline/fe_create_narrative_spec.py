from typing import Annotated, Optional, Literal, Dict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END # START and END are special pre-defined edges
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
from openai import OpenAI
from contextlib import asynccontextmanager
import httpx
import asyncio
import json


import os

MAX_ITERATIONS = 5

class SpecState(TypedDict):
    iterations: int = 0
    pitch_input: str
    spec_dict: Optional[Dict]
    validated: Optional[bool] 
    timed_out: bool = False

async def get_spec(state: SpecState):
    state["iterations"] += 1

    pitch_input = state.get("pitch_input")
    
    post_url = f"http://localhost:8000/story_plan/?plan_input={pitch_input}"
    get_url = "/job-status/?_job_id="

    # submit
    # post input to the story_plan endpoint
    resp = await httpx.post(post_url)
    # deal with anything other than 200 OK
    job_id = resp.json()["job_id"]


    # poll
    for _ in range(60): # two minutes

        resp = await httpx.get(f"{get_url}{job_id}")
        data = resp.json()
        if data["status"] == 'finished' and data["result"] is not None:
            state["spec_dict"] = data["result"]
            return state
        await asyncio.sleep(2)

    state["timed_out"] = True
    return state
        

def validate_spec(state: SpecState) -> Literal["all_good", "get_spec", "failed_get_spec"]:
    
    iters = state.get("iterations")

    if iters >= MAX_ITERATIONS or state.get("timed_out"):
        return "failed_get_spec"
    

    title = state.get("spec_dict")['title']
    if title == "INVALID":
        return "get_spec"
    else:
        return "all_good"
    
def all_good(state: SpecState):
    state["validated"] = True
    return state

def failed_get_spec(state: SpecState):
    state["validated"] = False
    # raise an exception
    return state

graph_builder = StateGraph(SpecState)

# add the nodes
graph_builder.add_node("get_spec", get_spec)
graph_builder.add_node("all_good", all_good)
graph_builder.add_node("failed_get_spec", failed_get_spec)

# add edges
graph_builder.add_edge(START, "get_spec")
graph_builder.add_conditional_edges("get_spec", validate_spec)

graph_builder.add_edge("all_good", END)
graph_builder.add_edge("failed_get_spec", END)

compiled_graph = graph_builder.compile()


print("compile success")
print(compiled_graph.nodes)


async def create_narrative_spec(_pitch_input: str):

    updated_state: SpecState = compiled_graph.invoke(
        SpecState(
            {
                "pitch_input": _pitch_input
            }
        )
    )

    spec_dict = updated_state.get("spec_dict")
    print(json.dumps(spec_dict, indent=2))

asyncio.run(create_narrative_spec("Write a scary story about satanic cheerleaders"))