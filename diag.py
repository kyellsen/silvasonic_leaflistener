import importlib.util
import os
import sys

print(f"Python: {sys.version}")
print(f"CWD: {os.getcwd()}")


def check_module(name: str) -> None:
    try:
        if importlib.util.find_spec(name):
            print(f"{name}: ok")
        else:
            print(f"{name}: missing (not found)")
    except ImportError as e:
        print(f"{name}: missing {e}")
    except Exception as e:
        print(f"{name}: error checking {e}")


check_module("fastapi")
check_module("httpx")
check_module("silvasonic_uploader")
