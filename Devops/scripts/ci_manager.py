import subprocess
import requests
import time
import os

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")

def notify_slack(message):
    requests.post(SLACK_WEBHOOK, json={"text": message})

def run_cmd(desc, cmd):
    print(f"🔧 {desc}: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        notify_slack(f"❌ Failed: {desc}")
        raise Exception(f"Step failed: {desc}")
    print(f"✅ Done: {desc}")

def health_check(url):
    for i in range(5):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2 ** i)
    return False

def run_ci_pipeline(branch):
    try:
        notify_slack(f"🚀 CI Started for branch: `{branch}`")

        run_cmd("Start test env", "docker compose -f docker-compose.test.yaml up -d --build")
        run_cmd("Run Pytest", "docker compose -f docker-compose.test.yaml exec -T app pytest")

        if not health_check("http://localhost:8080/health"):
            raise Exception("Health check failed")

        notify_slack(f"✅ CI passed for `{branch}`")

        if branch == "main":
            run_cmd("Tear down prod", "docker compose -f docker-compose.prod.yaml down")
            run_cmd("Deploy prod", "docker compose -f docker-compose.prod.yaml up -d --build")
            notify_slack("🚢 Deployed to production")

        return "CI complete"

    except Exception as e:
        notify_slack(f"🔥 CI failed for `{branch}`: {str(e)}")
        return "CI failed"
