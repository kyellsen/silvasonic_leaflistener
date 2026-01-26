import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import fastapi
    print("FastAPI found")
    import starlette
    print("Starlette found")
    import src.auth
    print("src.auth imported")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
