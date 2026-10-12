"""Developer diagnostics: print frame locations/types, never exception values/private inputs."""
import asyncio
import json
import os
from pathlib import Path
import sys
import traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.contracts import SearchRequest,TenantContext


async def main():
    app=create_app(Settings())
    session=json.loads((ROOT/"private-data/local-session.json").read_text())
    try:
        async with app.router.lifespan_context(app):
            result=await app.state.search.search(SearchRequest(query="arrendamiento de vivienda"),TenantContext(user_id=session["user_id"],tenant_id=session["tenant_id"],role="admin"),"diagnostic")
            print("Search results",len(result.results),result.engines,result.warnings)
    except Exception as error:
        print("Failure type:",type(error).__name__)
        traceback.print_tb(error.__traceback__)


if __name__=="__main__":
    if os.name=="nt":asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
