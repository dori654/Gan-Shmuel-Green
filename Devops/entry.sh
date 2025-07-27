#!/bin/bash

docker rm -f $(docker ps -aq) 2>/dev/null || true
docker build -t ci .
docker run -d -it --name ci_container ci