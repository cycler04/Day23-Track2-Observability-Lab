"""Generate error requests to populate SLO burn-rate dashboard."""
import requests
import time

for i in range(30):
    try:
        requests.post(
            "http://localhost:8000/predict",
            json={"prompt": "test", "fail": True},
            timeout=2
        )
        print(f"Error request {i+1}/30 sent")
        time.sleep(0.2)
    except requests.exceptions.RequestException:
        print(f"Request {i+1} failed (expected 503)")

print("Error generation complete")
