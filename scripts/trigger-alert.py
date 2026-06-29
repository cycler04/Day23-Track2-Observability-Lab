"""Trigger an alert by killing the app, wait for it to fire, then restore."""
import subprocess
import time
import requests
import sys

def run_cmd(cmd):
    """Run a shell command."""
    subprocess.run(cmd, shell=True, check=True)

def get_active_alerts():
    """Get count of active alerts from Alertmanager."""
    try:
        response = requests.get("http://localhost:9093/api/v2/alerts", timeout=3)
        return response.text.count('"state":"active"')
    except requests.exceptions.RequestException:
        return 0

def main():
    print("Step 1: kill app container")
    run_cmd("docker stop day23-app")
    
    print("Step 2: wait 90s for ServiceDown alert to fire")
    for i in range(1, 19):
        time.sleep(5)
        alerts = get_active_alerts()
        if alerts > 0:
            print(f"  alert fired (after {i}*5s)")
            break
        print(f"  no alert yet ({i}*5s)")
    
    print("Step 3: restart app")
    run_cmd("docker start day23-app")
    
    print("Step 4: wait 60s for alert to resolve")
    for i in range(1, 13):
        time.sleep(5)
        alerts = get_active_alerts()
        if alerts == 0:
            print("  alert resolved")
            return 0
    
    print("alert did not resolve within 60s", file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main())
