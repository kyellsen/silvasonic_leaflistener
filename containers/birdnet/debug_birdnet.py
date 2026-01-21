import sys
import os
import datetime
from pathlib import Path

# Try importing standard BirdNET-Analyzer
try:
    import birdnet_analyzer.analyze as bn_analyze
    print("[INFO] Successfully imported birdnet_analyzer.analyze")
except ImportError as e:
    print(f"[ERROR] Failed to import birdnet_analyzer: {e}")
    sys.exit(1)

def run_debug(audio_path, output_path=None):
    print(f"[INFO] Analyzing: {audio_path}")
    if not os.path.exists(audio_path):
        print(f"[ERROR] File not found: {audio_path}")
        return

    # Basic params
    lat = 51.1657
    lon = 10.4515
    week = datetime.datetime.now().isocalendar()[1]
    min_conf = 0.01 # Keep low to see raw
    overlap = 0.25
    threads = 1
    
    print(f"[INFO] Params: lat={lat}, lon={lon}, week={week}, min_conf={min_conf}")

    try:
        # Call analyze
        # NOTE: output=None usually returns the result dict
        start_time = datetime.datetime.now()
        result = bn_analyze.analyze(
            audio_input=str(audio_path),
            min_conf=min_conf,
            lat=lat,
            lon=lon,
            week=week,
            overlap=overlap,
            threads=threads,
            output=None 
        )
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"[INFO] Analysis took {duration:.2f}s")
        print(f"[INFO] Result Type: {type(result)}")
        
        if result:
            print(f"[INFO] Result keys (timestamps): {list(result.keys())[:5]}")
            count = 0
            for k, v in result.items():
                count += len(v)
                # Print first few
                if count <= 5:
                   print(f"  {k}: {v}")
            print(f"[INFO] Total segments: {len(result)}")
            print(f"[INFO] Total predictions: {count}")
        else:
            print("[WARN] Result is None or empty!")
            
    except Exception as e:
        print(f"[ERROR] Exception during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Check for generated test file
        test_file = "/data/db/test_sine.wav"
        if os.path.exists(test_file):
            print(f"Using default test file: {test_file}")
            run_debug(test_file)
        else:
             print("Usage: python debug_birdnet.py <path_to_wav>")
             sys.exit(1)
    else:
        run_debug(sys.argv[1])
