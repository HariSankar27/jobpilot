import asyncio
import sys

if sys.platform == "win32":
    # ponytail: psycopg's async driver refuses ProactorEventLoop (Windows' asyncio
    # default since 3.8); every entrypoint imports this package first, so set the
    # policy once here. Upgrade path: drop this once psycopg supports Proactor.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
