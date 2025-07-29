import subprocess
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")

def notify_slack(message):
    if not SLACK_WEBHOOK:
        print("No Slack webhook URL configured, skipping notification.")
        return
    print(f"Sending notification to Slack: {message}")
    requests.post(SLACK_WEBHOOK, json={"text": message})

def run_cmd(desc, cmd):
    print(f"Running {desc}: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        notify_slack(f"Failed: {desc}")
        raise Exception(f"Step failed: {desc}")
    print(f"Done: {desc}")
    return result

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

def get_latest_stable_commit():
    try:
        result = subprocess.run("git rev-parse HEAD", shell=True, check=True, capture_output=True, text=True)
        commit_hash = result.stdout.strip()
        print(f"Current commit hash: {commit_hash}")
        return commit_hash
    except Exception as e:
        print(f"Error getting latest stable commit: {e}")
        return '3a3aab312c5837e57a1a21ca8e219ae82c0a28d9'  # Fallback to a known commit hash
    
def sync_branch(branch):
  try:
    subprocess.run(f"git fetch", shell=True, check=True)
    print("KOBI - git fetch")
    subprocess.run(f"git checkout {branch}", shell=True, check=True)
    print(f"KOBI - git checkout {branch}")
    subprocess.run(f"git fetch origin {branch}", shell=True, check=True)
    print(f"KOBI - git fetch origin {branch}")
    subprocess.run(f"git reset --hard origin/{branch}", shell=True, check=True)
    print(f"KOBI - git reset --hard origin/{branch}")
    subprocess.run(f"git pull", shell=True, check=True)
    print(f"KOBI - git pull")
    print(f"{branch} is up to date")
  except Exception as e:
    print(f"Error syncing branch {branch}: {e}")

def run_ci_pipeline(payload):
    # You can extract branch, repo, etc. from the payload here
    ref = payload.get('ref', '')
    branch = ref.split('/')[-1] if ref else None
    commit_message = payload.get('head_commit', {}).get('message', 'unknown')
    pusher_name = payload.get('pusher', {}).get('name', 'unknown')




    commit_hash = payload.get('head_commit', {}).get('id', 'unknown')

    print(f"Running CI for branch: {branch}, pusher: {pusher_name}, commit: {commit_message}")
    try:
        notify_slack(f"CI Started for branch: `{branch}` by `{pusher_name}`. Commit: `{commit_message}`")

        if branch == "devops_build_tests":
          run_cmd("clone repo", "git clone https://github.com/dori654/Gan-Shmuel-Green.git /builder")
          os.chdir("/builder")

          latest_stable_commit = get_latest_stable_commit()
          try:
              
            # pull the latest commit
            #git fetch origin devops_build_tests
            print(f"Pulling latest commit for branch: {branch}")
            sync_branch(branch)

            #export environment variables
            run_cmd("Export environment variables", "export $(cat .env | xargs)")


            #build weight image
            os.chdir("/builder/Weight")
            print("Building weight image")
            build_weight_result = run_cmd("Build weight image", 'docker compose run --rm app sh -c "ls -R /app"')
            if build_weight_result.returncode != 0:
                raise Exception("Failed to build weight image")
            

            # #test weight image
            # test_weight_result = run_cmd("Run Pytest on Weight", "docker compose -f /builder/Weight/docker-compose.yml exec -T weight pytest")
            # if test_weight_result.returncode != 0:
            #     raise Exception("Pytest failed for Weight service")

            #build billing image
            os.chdir("/builder/Billing")
            print("Building billing image")
            build_billing_result = run_cmd("Build billing image", "docker compose up -d --build")
            if build_billing_result.returncode != 0:
                raise Exception("Failed to build billing image")

            # #test billing image
            # test_billing_result = run_cmd("Run Pytest on Billing", "docker compose -f /builder/Billing/docker-compose.yml exec -T billing pytest")
            # if test_billing_result.returncode != 0:
            #     raise Exception("Pytest failed for Billing service")

          except Exception as e:
            notify_slack(f"🔥 CI failed for `{branch}`: {str(e)}")
            #rollback to the latest stable commit
            # run_cmd("Rollback to latest stable commit", f"git reset --hard {latest_stable_commit}")
            # notify_slack(f"Rolled back to latest stable commit: `{latest_stable_commit}`")
            # build_latest_stable_result = run_cmd("Build latest stable image", "docker compose -f ./Devops/docker-compose.yml up -d --build")
            # if build_latest_stable_result.returncode != 0:
                # notify_slack("🔥 Failed to build latest stable image after rollback")
                # return "CI failed after rollback"
            # notify_slack(f"✅ Rolled back and built latest stable image: `{latest_stable_commit}`")
            # return "CI failed after rollback"
          
            


        # run_cmd("Start test env", "docker compose -f docker-compose.test.yaml up -d --build")
        # run_cmd("Run Pytest", "docker compose -f docker-compose.test.yaml exec -T app pytest")

        if not health_check("http://localhost:8080/health"):
          raise Exception("Health check failed")

        notify_slack(f"✅ CI passed for `{branch}`")

        if branch == "main":
          run_cmd("Tear down prod", "docker compose -f docker-compose.prod.yaml  down")
          run_cmd("Deploy prod", "docker compose -f docker-compose.prod.yaml up -d --build")
          notify_slack("🚢 Deployed to production")

        return "CI complete!"

    except Exception as e:
        notify_slack(f"🔥 CI failed for `{branch}`: {str(e)}")
        return "CI failed"

#Small check to ensure the /
# script is running as intended
#plox work for me. 

