import asyncio
import logging
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ["LANGCHAIN_TRACING_V2"]="false"
os.environ["LANGSMITH_TRACING"]="false"
os.environ["HF_HUB_OFFLINE"]="1"
os.environ["TRANSFORMERS_OFFLINE"]="1"


if __name__=="__main__":
    if os.name=="nt":asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # SQL/parser/model error logs can include private inputs. Emit only our explicit codes.
    for name in ("psycopg.pool","uvicorn.error","httpx","httpcore","langsmith","langgraph"):
        logging.getLogger(name).disabled=True
    import torch
    torch.set_num_threads(4)
    import uvicorn
    config=uvicorn.Config("services.api.app.main:app",host="127.0.0.1",port=8000,access_log=False,log_config=None,loop="none")
    server=uvicorn.Server(config)
    if os.name=="nt":asyncio.run(server.serve(),loop_factory=asyncio.SelectorEventLoop)
    else:asyncio.run(server.serve())
