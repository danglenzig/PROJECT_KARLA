import asyncio
import httpx
from contextlib import asynccontextmanager
from typing import List, Dict, Any
import json
from pathlib import Path
import sys

# PROJECT_KARLA/src/
SRC_ROOT = Path(__file__).parent.parent  # src/pipeline -> src

# PROJECT_KARLA/src/core_data_models
CORE_DATA_MODELS_PATH = SRC_ROOT / "core_data_models"
sys.path.insert(0, str(CORE_DATA_MODELS_PATH))

from core_data_models import StoryPlan

class PipelineClient:
    def __init__(self, _base_url = "http://localhost:8000"):
        self.base_url = _base_url
        self.client = None

    @asynccontextmanager
    async def session(self):
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            self.client = client
            yield self
        self.client = None

    async def generate_story_plan(self, pitch_input: str):
        
        # submit
        #resp = await self.client.post("/story_plan/", json={"pitch_input": pitch_input})
        resp = await self.client.post("/story_plan/?plan_input=" + pitch_input)
        
        resp.raise_for_status() # raises an HTTP error is one occurs
        job_id = resp.json()["job_id"]

        # poll
        for _ in range(60): # 2 minute timeout

            resp = await self.client.get(f"/job-status/?_job_id={job_id}")
            
            data = resp.json()
            if data["status"] == 'finished' and data["result"] is not None:
                return data["result"] # VN spec
            await asyncio.sleep(2)
        raise TimeoutError(f"Job {job_id} timed out.")
    
# usage in main (here temporarity for testing)
async def main():
    narrative_client = PipelineClient()
    async with narrative_client.session():
        spec: StoryPlan = await narrative_client.generate_story_plan(
            "Write a scary story about a group of elderly nursing home residents who start acting strangly and malevolently after a newly discovered comet passes overhead."
        )
        print(json.dumps(spec, indent=2))
        print(f"\n\n{spec['title']}")

        ## if the agent needs to be re-run, spec['title'] == "INVALID"


asyncio.run(main())