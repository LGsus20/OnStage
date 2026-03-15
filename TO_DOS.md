# Repo
- Documentation & Refactoring: Improve the documentation and refine the codebase once core features are complete.
- Deployment: Add setup instructions for Cloudflare and create a release build for easy installation on Raspberry Pi.
- Environment Setup: Create a .env.example file.

# Business Rules:
- BR1: Maintain a continuous playback queue.
- BR2: Allow users to skip songs by pressing the Play button.
- BR3: Search by Artist and Song Name; the system should look up the track on YouTube Music, retrieve the URL, and download it.
- BR4: A second option in which you have the option to download the song and after it has been download add it to the queue 
- BR5: Use sockets rather than HTTP polling 


# Nice to have:
0. Spotify Integration: Support Spotify links to automatically find and play the equivalent track on YouTube Music.
1. "Who Added This?": A mini-game to guess which guest added the current song. Perhaps have a hide button on the person that added the song to the queue, and have another button that shuffles the queue. at the end of the song it shows who entered the previous song and the name of that song 
2. Guess the Year: A challenge to guess the song's release date.
3. Guess the Views: A challenge to guess the total view count.
4. Upvote or downvote songs, and there's a button to import a list of the songs that you liked. Perhaps make it sent you a report via email or something like that 
5. Add a cap on the duration of the music (10min perhaps?) before downloading the song. 
6. In the reports, also add the YouTube music link (that would need to be stored at the time of download, leave empty if not available) 
7. Have the values: View count, release year and other data (like album) in the available music section, perhaps even sort by those values 
8. When clicking the generate report, do not download a .txt just show the text and the user can decide whether to download the .txt or not 
9. 