#!/bin/bash

docker stop yt-downloader-backend || true && docker rm yt-downloader-backend || true
docker login -u="aryaraj132" -p="$1"
docker pull aryaraj132/yt-downloader-backend:latest

docker run -dp 5000:5000 --restart=always --name yt-downloader-backend \
  --interactive --tty \
  aryaraj132/yt-downloader-backend:latest

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
