from flask import Flask

app = Flask(__name__)


@app.route('/health')
def health_check():
    return 'OK', 200



def build_dev():
    subprocess.run("docker compose Devops/docker-compose.tests.yaml", check=True)
    if health_check() == True:
        print("Development environment built successfully.")
        return "Development environment built successfully."
    else:
        print("Failed to build development environment.")
        return "Failed to build development environment."

def build_prod():
    subprocess.run("docker compose Devops/docker-compose.prod.yaml", check=True)
    if health_check() == True:
        print("Production environment built successfully.")
        return "Production environment built successfully."
    else:
        print("Failed to build production environment.")
        return "Failed to build production environment."
    return "Production environment built successfully."

@app.route('/push-dev', methods=['POST'])
def push_dev(secret=None):
    print("Push to dev branch triggered")
    if build_dev() == "Development environment built successfully.":
        return "Development environment built successfully.", 200
    else:
        return "Failed to build development environment.", 500


@app.route('/push-main', methods=['POST'])
def push_main(secret=None):
    print("Push to main branch triggered")
    if build_dev() == "Development environment built successfully.":
        build_prod()
        # deploy_prod()
        return "Main environment built successfully.", 200
    else:
        return "Failed to build development environment.", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)