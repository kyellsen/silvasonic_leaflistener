import asyncio
import os
import sys

# Add src to path just in case
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from services.database import db
from sqlalchemy import text

async def check():
    print(f"Checking Database Connection to: {db.db_url}")
    try:
        async with db.get_connection() as conn:
            print("Connected successfully.")
            
            # Check birdnet schema
            try:
                res = await conn.execute(text("SELECT count(*) FROM birdnet.detections"))
                count = res.scalar()
                print(f"Count in birdnet.detections: {count}")
                
                if count > 0:
                    res_max = await conn.execute(text("SELECT MAX(timestamp) FROM birdnet.detections"))
                    max_ts = res_max.scalar()
                    print(f"Max timestamp: {max_ts}")
                else:
                    print("Table is empty.")
                    
            except Exception as e:
                print(f"Error querying table: {e}")
                
    except Exception as eobj:
        print(f"Connection failed: {eobj}")

if __name__ == "__main__":
    asyncio.run(check())
