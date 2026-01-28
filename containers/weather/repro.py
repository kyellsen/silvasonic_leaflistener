import traceback

from wetterdienst.provider.dwd.observation import DwdObservationRequest

try:
    print("Attempting to instantiate DwdObservationRequest...")
    req = DwdObservationRequest(parameter=["temperature_air_mean_2m"], resolution="10_minutes")
    print("Success")
except Exception:
    traceback.print_exc()

import inspect

print("\nSignature:")
try:
    print(inspect.signature(DwdObservationRequest.__init__))
except Exception:
    print("Could not get signature")
