#!/bin/bash

docker buildx build --platform linux/amd64 -t hackinglab/kuma-zabbix-bridge:latest . --push
