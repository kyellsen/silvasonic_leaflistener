import asyncio
import sys

# Add src to path
sys.path.append("/mnt/data/dev/packages/silvasonic/containers/dashboard")

from sqlalchemy import text
from src.services.database import db


async def check():
    """Check database connection and basic statistics."""
    print("Checking DB connection...")
    try:
        async with db.get_connection() as conn:
            print("Connected!")

            # Check birdnet.detections
            print("Checking birdnet.detections count...")
            count = (await conn.execute(text("SELECT COUNT(*) FROM birdnet.detections"))).scalar()
            print(f"Total detections: {count}")

            # Check for recent
            print("Checking recent detections (last 24h)...")
            recent = (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM birdnet.detections "
                        "WHERE timestamp > NOW() - INTERVAL '24 HOURS'"
                    )
                )
            ).scalar()
            print(f"Recent detections: {recent}")

            # Check schema
            print("Checking one row...")
            row = (await conn.execute(text("SELECT * FROM birdnet.detections LIMIT 1"))).fetchone()
            if row:
                print(f"Row keys: {row._mapping.keys()}")
            else:
                print("Table is empty.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(check())
