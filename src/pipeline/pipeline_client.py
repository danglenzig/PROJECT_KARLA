import asyncio
import httpx
from contextlib import asynccontextmanager
from typing import List, Dict, Any

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
        spec = await narrative_client.generate_story_plan(
            "Write a scary story about satanic cheerleaders"
        )
        print(spec) # send to narrative and art agents

asyncio.run(main())