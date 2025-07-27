import subprocess
import sys
def run_step(description, command):
    print(f"\n:wrench: {description}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f":x: Step failed: {description}")
        sys.exit(1)
    print(f":white_check_mark: Step succeeded: {description}")
def main():
    print(":rocket: Starting CI pipeline...")
    # Step 1: Install requirements
    run_step("Installing dependencies", "pip install -r requirements.txt")
    # Step 2: Run flake8 linting
    run_step("Running flake8", "flake8 . --exclude=venv --max-line-length=100")
    # Step 3: Run tests with pytest
    run_step("Running tests", "pytest")
    # Step 4: Deploy (e.g., Docker or Flask run)
    run_step("Deploying to test environment", "python app/main.py")  # adjust as needed
    print(":tada: CI pipeline completed successfully.")
if __name__ == "__main__":
    main()