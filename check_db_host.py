import asyncio
import os
import sys

# Define path to dashboard src relative to this script location (assuming script is in root or dashboard/src)
# If this file is in silvasonic/containers/dashboard/src/, then:
# We need to render "src" (dashboard logic) importable.
# But services is in src.services.

# Let's adjust sys.path to find 'src' as a package OR adjust imports.
# The dashboard code uses `from src.services ...` which implies `src` is top level package in PYTHONPATH.
# Or `from services ...` if PYTHONPATH is `containers/dashboard/src`.

# Let's assume we run this from `silvasonic/` (pkg root) and PYTHONPATH includes `containers/dashboard/src`.

# Hardcode connection string for host test
DB_URL = "postgresql+asyncpg://silvasonic:silvasonic@127.0.0.1:5432/silvasonic"

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    print(f"Checking Database Connection to: {DB_URL}")
    engine = create_async_engine(DB_URL)
    try:
        async with engine.connect() as conn:
            print("Connected successfully.")
            
            # Check birdnet schema
            try:
                res = await conn.execute(text("SELECT count(*) FROM birdnet.detections"))
                count = res.scalar()
                print(f"Count in birdnet.detections: {count}")
                
                if count > 0:
                    res_max = await conn.execute(text("SELECT MAX(timestamp) FROM birdnet.detections"))
                    max_ts = res_max.scalar()
                    print(f"Max timestamp: {max_max_ts}") # Typo fix: max_ts
                    print(f"Max timestamp: {max_ts}")
                else:
                    print("Table is empty.")
                    
            except Exception as e:
                print(f"Error querying table: {e}")
                
    except Exception as eobj:
        print(f"Connection failed: {eobj}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
