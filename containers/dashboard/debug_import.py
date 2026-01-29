import os
import sys

# Ensure src is in path
src_path = os.path.join(os.getcwd(), "src")
sys.path.append(src_path)

print(f"Checking imports from {src_path}...")

try:
    print("✅ Import SUCCESS: silvasonic_dashboard.main.app loaded.")
except Exception as e:
    print(f"❌ Import FAILED: {e}")
    import traceback

    traceback.print_exc()
