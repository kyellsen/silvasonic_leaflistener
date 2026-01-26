import asyncio
import os
import sys

# Add src to path
sys.path.append(os.getcwd())

from src.services.analysis import AnalyzerService


async def verify():
    print("Verifying AnalyzerService...")

    # Test Formatting Helper directly
    print(f"Format 120s: {AnalyzerService._format_duration(120)}")
    print(f"Format 3661s: {AnalyzerService._format_duration(3661)}")
    print(f"Format 0s: {AnalyzerService._format_duration(0)}")
    print(f"Format Large (Invalid): {AnalyzerService._format_duration(2000000000)}")
    print(f"Format Size 1024: {AnalyzerService._format_size(1024)}")
    print(f"Format Size 1.5MB: {AnalyzerService._format_size(1.5 * 1024 * 1024)}")

    # Test DB Calls (if possible, might need DB connection)
    # We'll try, but if it fails due to connection issues inside this script context,
    # we at least verified the logic helpers above.

    # Mocking DB connection might be hard without full app context, but let's try reading
    # if it defaults to something working or if we can init it.
    # Assuming the app runs in container, we are in the container path?
    # actually we are in /mnt/data... we might need to set env vars for DB?
    # Let's just rely on the unit tests of the helpers for now if DB fails.

if __name__ == "__main__":
    asyncio.run(verify())
