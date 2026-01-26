import sys
import os
sys.path.append(os.getcwd())

print("Attempting to import DatabaseHandler...")
try:
    from src.services import DatabaseHandler
    print("DatabaseHandler imported.")
except ImportError as e:
    print(f"Failed DatabaseHandler: {e}")
except Exception as e:
    print(f"Error DatabaseHandler: {e}")

print("Attempting to import BirdNetService...")
try:
    from src.services import BirdNetService
    print("BirdNetService imported.")
except ImportError as e:
    print(f"Failed BirdNetService: {e}")
except Exception as e:
    print(f"Error BirdNetService: {e}")
