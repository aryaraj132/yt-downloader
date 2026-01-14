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

## How to commit after code change

- Follow these instruction whenever user asks to commit any changes
- First ask for new branch or verify current branch if not on develop or main branch, We cannot commit to main branch and in develop we can only merge the changes of branch
- Follow this step by step to commit the changes 
  - use the command commit "commit message" - this command adds all the changes, commit with the commit message and push to github(create new branch if not created)
  - use the command gh pr create to create a PR, this will let you know if pr is already created
  - after every commit checkout to develop branch, use the command ckt develop and merge the branch into develop and push (In case of conflict let user clear the conflicts)
  - checkout back to the branch to continue
- Important commands ckt branchName To checkout to any branch; branch branchName to create new branch