# create_db.py (run this once)
import asyncio
from app.db.models import Base
from app.db.db_session import engine

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init_db())
