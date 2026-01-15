## Plan

Create a youtube downloader using yt-dlp (https://github.com/yt-dlp/yt-dlp)
Inspired by https://streamsnip.com/
Take reference of feature and things to be handled from https://streamsnip.com/ (focus on the basics mentioned below first)

## Considerations
You can use python supported by the yt-dlp library
This will be hosted on linux server and needs to be run as a service, make sure you follow best practices for production ready application and make sure to handle all edge cases
User Firebase Config for environment variables, when starting the server load the config from firebase and inject it into environment variables then procees to run the application server
    - use Firebase Admin SDK the service account key file is provided in the repo

Assume all the environment variables needed are provided and valid, use the appropriate name of the environment variables and make a list of them, I'll add them later on.

## Features
use the mongodb database to store data
Allow general user management features like login, logout, register, change password, etc.
use auth token and redis-cache sessions for user authentication and authorization
store session in cache as well as in mongodb

one endpoint to accepts url as input and the start and end time of the video in seconds
    - This stores the url and the start and end time in the mongodb database against the userId of logged in user and returns the id of the document
    - This will have a separate token for authentication since this will be public facing api and this token can only be used to save the video info to be processed and downloaded later on by user

another api to extract the video along with audio and save it as a mp4 file (aac audio and h264 video) and then give user download option.
    - 30min after saving a video it will be deleted
    - This will use the normal auth token for authentication which will be private

Make a middleware to check the auth token and redis-cache session, if the token belongs to valid user session then we use the decoded userId to get the user data from mongodb and store it in the request object otherwise return 401 unauthenticated


## Version Control

- git

## Itteration 2 feature:

In the current implementation add a feature to encode other format videos to mp4 video.
ask for video encoding H.264, H.265, AV1, audio encoding aac so that we convert any video to supported mp4 format which can be used anywhere.

Note: We do not reduce any quality and conversion should be almost lossless

Inspired by: https://cloudconvert.com/

## Itteration 3 feature:

Add an api exposed to public, which accepts youtube live chat id and user's public token, using chat id we will determine the url of live video as well as the timestamp of that chat in respect to the video length(i.e., after how many seconds of the live stream the chat was made) using this value we will use save the data(url, start time, end time, additional message sent to be saved against the user whose public token is used) of this video to be downloaded later on. mainly this will be used to download the video from the point where the chat was made. 

We will use this api in nightbot like this `$(urlfetch https://${endpoint}/api/video/save/stream/${token}/$(chatid)/$(querystring))`
documentation: https://docs.nightbot.tv/variables/chatid , https://docs.nightbot.tv/variables/querystring



Add a feature to download the video in different formats and resolutions.