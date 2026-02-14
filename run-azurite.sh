#!/bin/bash
docker stop azurite || true && docker rm azurite || true
docker pull mcr.microsoft.com/azure-storage/azurite:latest
docker run -v $(pwd)/azurite:/data --restart=always --name=azurite \
  -p 10001:10001 \
  --interactive --tty \
  -d mcr.microsoft.com/azure-storage/azurite:latest \
    azurite-queue --queueHost 0.0.0.0 --queuePort 10001
