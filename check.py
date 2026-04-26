import asyncio
from api.gcp_services import gcp_client
async def check():
    runs = await gcp_client.list_runs(limit=5)
    for r in runs:
        print(f"Run: {r.get('run_id')} - Status: {r.get('status')} - Error: {r.get('error')}")
asyncio.run(check())
