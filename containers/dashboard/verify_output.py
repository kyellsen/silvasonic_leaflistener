import sys
import os

with open("verify_result.txt", "w") as f:
    f.write("Starting verification...\n")
    try:
        from src.services import DatabaseHandler, SystemService, BirdNetService
        f.write("Imports successful!\n")
    except ImportError as e:
        f.write(f"ImportError: {e}\n")
    except Exception as e:
        f.write(f"Exception: {e}\n")
