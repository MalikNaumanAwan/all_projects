# create_tables.py
import asyncio
from db.models import Base
from db.session import engine
async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(create())
