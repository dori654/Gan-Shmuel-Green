#!/bin/bash

docker rm -f $(docker ps -aq) 2>/dev/null || true
docker build -t ci .
docker run -d -it --name ci_container ci

# curl -X POST http://172.17.0.2:8080/trigger   -H "Content-Type: application/json"   -H "X-G
# itHub-Event: push"   -d '{
#     "ref": "refs/heads/main",
#     "repository": {
#       "name": "example-repo"
#     }
#   }'

    # print(f"Received event: {event_type}")
    # return jsonify({'status': 'Ignored'}), 200  # Default response
    #