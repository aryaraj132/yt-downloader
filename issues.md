Current issues:
- YT-DLP error: Starts to fail with different youtube asking for signup (not a problem with code)
    - error: yt-dlp error: ERROR: [youtube] RQDCbgn2vDM: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies
    - Can we pass the cookies from the browser to yt-dlp from our frontend, so whenever we are downloading a video it will use the cookies from the browser of the client who is downloading the video to download the video from the frontend.

- Need to implement saving stream clips from nightbot: We want to save stream clips from nightbot by assigning a command to (eg: !clip) so whenever someone types !clip in the live chat of stream, it will save the clip from 60sec before the command was called to 10sec after the command was called, the issue is that we need to implement a way to get the stream url and when in stream the command was called to save the clip.
    - Currently night bot gives these variables: https://docs.nightbot.tv/variables we can use chatId: not sure how much information can i get from chat id.
    - Solution, Maybe we can drop the login method of username and pasword instead use google oauth instead and then use YouTube Data API v3 to fetch the stream url using the chatId and time difference of now and the time stream was published to get the stream url, start time and end time of the clip and save it in db.

    - also can we use this oAuth method to prevent 'yt-dlp error: ERROR: [youtube] RQDCbgn2vDM: Sign in to confirm you’re not a bot.'

All of these are the issue which will hinder the progress of the project to make it production ready.