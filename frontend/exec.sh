#!/bin/bash

docker stop yt-downloader-frontend || true && docker rm yt-downloader-frontend || true
docker pull aryaraj132/yt-downloader:latest

docker run -dp 3000:3000 --restart=always --name yt-downloader-frontend \
  --interactive --tty \
  aryaraj132/yt-downloader:latest

dangling=$(sudo docker images --filter "dangling=true" -q)

if [[ -z "$dangling" ]]
    then
    echo "no dangling image found"
    else
    echo "dangling image found and will be removed" $dangling
    sudo docker rmi $dangling
fi
history -c
sudo rm ~/.docker/config.json
