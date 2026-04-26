import asyncio
from api.gcp_services import gcp_client
import json

async def check():
    r = await gcp_client.get_run("54b43550")
    report = r.get("report")
    print(json.dumps(report, indent=2))
asyncio.run(check())
