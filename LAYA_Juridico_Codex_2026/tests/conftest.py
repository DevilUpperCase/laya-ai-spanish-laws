import asyncio
import sys
import pytest


def pytest_asyncio_loop_factories(config,item):
    return {"selector":asyncio.SelectorEventLoop} if sys.platform=="win32" else {"default":asyncio.new_event_loop}
