"""Health-check all 7 services for the observability stack."""
import requests
import sys

def check_service(name: str, url: str, expected: str = None) -> bool:
    """Check if a service is healthy."""
    try:
        response = requests.get(url, timeout=3)
        if expected:
            return expected in response.text
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"    Error checking {name}: {e}")
        return False

def main():
    services = [
        ("app", "http://localhost:8000/healthz", None),
        ("prometheus", "http://localhost:9090/-/healthy", None),
        ("alertmanager", "http://localhost:9093/-/healthy", None),
        ("grafana", "http://localhost:3000/api/health", '"database"'),
        ("loki", "http://localhost:3100/ready", None),
        ("jaeger", "http://localhost:16686/", None),
        ("otel-collector", "http://localhost:8888/metrics", None),
    ]

    print("Checking services...")
    all_ok = True
    for name, url, expected in services:
        ok = check_service(name, url, expected)
        status = "OK" if ok else "FAIL"
        print(f"  {name:15s} {status}")
        if not ok:
            all_ok = False

    if all_ok:
        print("Stack healthy.")
        return 0
    else:
        print("Stack unhealthy!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
