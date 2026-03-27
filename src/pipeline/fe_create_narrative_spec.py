from typing import Annotated, Optional, Literal, Dict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END # START and END are special pre-defined edges
from langgraph.graph.state import CompiledStateGraph
import httpx
import asyncio
import json

MAX_ITERATIONS = 5

class SpecState(TypedDict):
    iterations: int
    pitch_input: str
    spec_dict: Optional[Dict]
    validated: Optional[bool] 
    timed_out: bool

async_client = httpx.AsyncClient(
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
    timeout=httpx.Timeout(30.0)  # Adjust as needed
)

async def get_spec(state: SpecState):

    pitch_input = state.get("pitch_input")
    

    # The agent that lives behind this API runs a RAG assisted CoT loop,
    # and eventually outputs a formatted story spec for a visual novel.
    # The agent does its own schema validation, so whatever it produces
    # will at least be structured correctly. If that validation fails on
    # the agent side, then the value of the "title" key will be "INVALID",
    # and the dict contain placeholder data. The agent produces a valid 
    # spec 99% of the time, but it occasionally screws up the JSON and 
    # returns the placeholder dict with "INVALID" as the title.
    post_url = f"http://localhost:8000/story_plan/?plan_input={pitch_input}"
    get_url = "http://localhost:8000/job-status/?_job_id="

    # submit
    # post input to the story_plan endpoint, FAPI tells RQ to enque the job
    resp = await async_client.post(post_url)
    resp.raise_for_status() # raise HTTP errors if any
    job_id = resp.json()["job_id"]


    # poll
    for _ in range(60): # two minutes

        resp = await async_client.get(f"{get_url}{job_id}")
        resp.raise_for_status()
        data = resp.json()
        if data["status"] == 'finished' and data["result"] is not None:
            state["spec_dict"] = data["result"]
            state["iterations"] += 1
            return state
        await asyncio.sleep(2)

    state["iterations"] += 1
    state["timed_out"] = True
    return state
        

def validate_spec(state: SpecState) -> Literal["all_good", "get_spec", "failed_get_spec"]:
    
    iters = state.get("iterations")

    # repeated validation failures or timeout...
    if iters >= MAX_ITERATIONS or state.get("timed_out"):
        return "failed_get_spec"

    title = state.get("spec_dict")['title']
    if title == "INVALID":
        return "get_spec" # i.e. try again...
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

compiled_graph: CompiledStateGraph = graph_builder.compile()


print("compile success")
print(compiled_graph.nodes)

async def create_narrative_spec(_pitch_input: str):
    initial_state = SpecState(
        iterations = 0,
        pitch_input= _pitch_input,
        spec_dict = None,
        validated = None,
        timed_out = False
    )
    updated_state: SpecState = await compiled_graph.ainvoke(initial_state)
    spec_dict = updated_state.get("spec_dict")
    print(json.dumps(spec_dict, indent=2))

async def main():
    try:
        await create_narrative_spec("Write a scary story about satanic cheerleaders")
    finally:
        await async_client.aclose()

asyncio.run(main())