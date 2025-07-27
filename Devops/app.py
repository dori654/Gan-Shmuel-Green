
import sys, time
import requests

def test_service(name, url):
    """Test a service health endpoint"""
    print(f"Testing {name} service at {url}")
    for attempt in range(1, 11):
        try:
            r = requests.get(url, timeout=3)
            if r.ok:
                print(f"? {name} passed:", r.text[:80])
                return True
            print(f"? {name} unexpected status", r.status_code)
        except Exception as exc:
            print(f"? {name} {attempt}/10 waiting? {exc}")
        time.sleep(3)
    return False

# Test both services
services = [
    ("Weight", "http://weight-app:5005/health"),
    ("Billing", "http://billing-app:5002/health")
]

all_passed = True
for name, url in services:
    if not test_service(name, url):
        print(f"? {name} CI failed ? service not healthy")
        all_passed = False
    print()

if all_passed:
    print("?? All services are healthy! CI passed")
    sys.exit(0)
else:
    print("? CI failed ? one or more services not healthy")
    sys.exit(1)
