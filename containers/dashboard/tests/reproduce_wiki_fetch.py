import asyncio
import logging
import sys

# Add src to path
sys.path.append("/mnt/data/dev/packages/silvasonic/containers/dashboard/src")

from silvasonic_dashboard.wikimedia import WikimediaService

# Configure logging
logging.basicConfig(level=logging.INFO)


async def test_fetch():
    species_to_test = [
        "Parus major",  # Great Tit (Should exist)
        "Cyanistes caeruleus",  # Blue Tit (Should exist)
        "Turducken",  # Fake bird (Should NOT exist)
        "Sitta europaea",  # Nuthatch (Should exist)
    ]

    print("--- Starting Wikimedia Fetch Test ---")
    for sp in species_to_test:
        print(f"\nFetching: {sp}")
        data = await WikimediaService.fetch_species_data(sp)
        if data:
            print(f"✅ Success for {sp}:")
            print(f"   - Image: {data.get('image_url')}")
            print(f"   - German: {data.get('german_name')}")
            print(f"   - Desc Len: {len(data.get('description', '') or '')}")
        else:
            print(f"❌ No data found for {sp} (Expected for 'Turducken')")


if __name__ == "__main__":
    asyncio.run(test_fetch())
