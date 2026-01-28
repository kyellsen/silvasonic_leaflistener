import os
import sys

# Add src directories to path
sys.path.append(os.path.abspath("containers/recorder/src"))
sys.path.append(os.path.abspath("containers/uploader/src"))
sys.path.append(os.path.abspath("containers/birdnet/src"))
sys.path.append(os.path.abspath("containers/weather/src"))
sys.path.append(os.path.abspath("containers/livesound/src"))
sys.path.append(os.path.abspath("containers/controller/src"))

print("Importing Recorder...")
try:
    print("Recorder OK")
except Exception as e:
    print(f"Recorder Failed: {e}")

print("Importing Uploader...")
try:
    print("Uploader OK")
except Exception as e:
    print(f"Uploader Failed: {e}")

print("Importing BirdNET...")
try:
    print("BirdNET OK")
except Exception as e:
    print(f"BirdNET Failed: {e}")

print("Importing Weather...")
try:
    print("Weather OK")
except Exception as e:
    print(f"Weather Failed: {e}")

print("Importing Livesound...")
try:
    print("Livesound OK")
except Exception as e:
    print(f"Livesound Failed: {e}")

print("Importing Controller...")
try:
    print("Controller OK")
except Exception as e:
    print(f"Controller Failed: {e}")
