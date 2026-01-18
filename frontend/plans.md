# Features Implementation
- [ ] Explore the idea of offloading the encoding only request, where clients will point to a file and ask it to be encoded in a specific format and quality, We can give option to client to use our server for encoding or use their own system for encoding. if they choose their own system for encoding, we can use node based ffmpeg for encoding, using client side resources, in this manner we can save our server resources and provide a better experience to the client, say they have very good gpu which can encode the video in much faster rate than our server, they can use their own system for encoding and we can provide them with the best quality video in much faster rate.

- [ ] Make a home page for the website, which will explain the idea of this website and in header will give option to encode your video, download yt-video segments, or login/signup to see list of their saved videos
- Encoding video page will have the following features:
    - [ ] select the codec and quality of the video
    - [ ] upload the video file
    - [ ] start the encoding process
    - [ ] show the progress of the encoding process
    - [ ] download the encoded video
- Download yt-video segments page will have the following features:
    - [ ] An input field to enter the url of the video
    - [ ] An embed video player to show the video
    - [ ] A dropdown to select resolution and format of the video( the data of available formats and resolutions will be fetched from the backend)
    - [ ] Two input fields to enter the start and end time of the video (If we can implement a slider to select the start and end time of the video and preview the selected segment, it will be great) ** Note: this will have no more than 120 seconds of video, if start time and end time is more than 120 seconds, it will not allow to download and give error, same if it is not provided at all **
    - [ ] A button to start the download process
    - [ ] A progress bar to show the progress of the download process
    - [ ] A button to download the video

- After logging in user can see list of their saved videos, which will have the following features:
    - [ ] List of all the videos saved by the user
    - [ ] A button to delete the video
    - [ ] A button to download the video (this will open a modal with the same features as the download yt-video segments page)
        - [ ] A dropdown to select resolution and format of the video( the data of available formats and resolutions will be fetched from the backend)
        - [ ] Two input fields to enter the start and end time of the video (If we can implement a slider to select the start and end time of the video and preview the selected segment, it will be great) ** Note: this will have no more than 120 seconds of video, if start time and end time is more than 120 seconds, it will not allow to download and give error, same if it is not provided at all **
        - [ ] A button to start the download process
        - [ ] A progress bar to show the progress of the download process
        - [ ] A button to download the video
    - [ ] A button to share the video
    