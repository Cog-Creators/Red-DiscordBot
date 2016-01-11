# Red - A multifunction Discord bot
#### *Fun bringer, admin helper and music bot*  
[<img align="right" title="Art by Supergiant Games" src="https://www.supergiantgames.com/static/images/transistor/cartoon_red.png">](https://www.supergiantgames.com/games/transistor/)
[**[Official Server - Announcements & Help]**](https://discord.gg/0k4npTwMvTpv9wrh)  

### Cool title, but what does it do exactly?
A bit of everything. Seriously though:  
It has the [most common features](#general-commands) of many chatbots (!flip, !8, stopwatch, etc.), **custom commands** (inspired by Twitch's [Nightbot](https://www.nightbot.tv/)).  
It features some games such as **Trivia**, rock paper scissors, [users can earn and play with credits](#economy-commands) in the slot machine.  
[The audio part is quite fleshed out](#audio-commands). Users can **stream youtube videos**, create **playlists** that everyone will be able to play and control (previous/next song, pause/resume, shuffle...).  
**MP3 and flac files can also be streamed** (see [FAQ](#faq) for details on local playlists)  
**Twitch's online notifications**: Red will notify the channels you want whenever you favorite Twitch streamers are online.  
As for the moderation tools, it includes a **powerful message filter with regular expression capabilities** and **mass messages cleanup**.  
[I'm planning to expand all this much more](#todo-list).  
See the [command list](#general-commands) for an even better idea of what this bot can do.

### I don't even know what I'm looking at. How do I install this?
Do not panic. Follow these steps:  
- Download the bot and unpack it.  
- [Install Python](https://www.python.org/downloads/). This bot needs 3.5.1 32bit or superior. Remember to check "Add python to path".  
- [Install Git](https://git-scm.com/download/win), don't forget to check "Use Git from the Windows Command Prompt"  
- Open the start menu, type cmd, right click and open the command prompt as admin. Now, do:  
```
pip install git+git://github.com/Rapptz/discord.py.git@5a1d7a2d942c75a2f374b4b0add6ad50fdd227d7
pip install requests
pip install youtube_dl
pip install beautifulsoup4
```
If for some reason pip install doesn't work do these commands with 
```
python -m pip install
```
instead. Now, about the configuration.  
- Open settings.json with a text editor and replace EMAILHERE and PASSWORDHERE with your bot's account details (make a dedicated discord account).  
- Run startRed.bat  

That's it. Remember to make the bot join your server (login into its account through Discord and join it manually) and create a role called "Transistor" in the server to be able to use the admin commands.  
Take a look at the command list and have fun.

### General commands

| Command                                       | Description                                |
|-----------------------------------------------|--------------------------------------------|
| !flip                                         | Flip a coin                                |
| !rps [rock/paper/scissors]                    | Play  RPS                                  |
| !proverb                                      | Random proverb                             |
| !choose [option1 or option2 or option3 (...)] | Random choice. Supports multiple words     |
| !8 [question?]                                | Ask 8 ball a question                      |
| !sw                                           | Start/stop the stopwatch                   |
| !trivia                                       | Trivia help and lists                      |
| !trivia [list]                                | Start a trivia session                     |
| !trivia stop                                  | Stop a trivia session                      |
| !twitch [stream]                              | Check if stream is online                  |
| !twitchalert [stream]                         | Red sends an alert in the channel when the stream is online (admin only)|
| !stoptwitchalert [stream]                     | Stop stream alerts (admin only)      |
| !roll [number]                                | Random number between 0 and chosen number. |
| !gif [text]                                   | GIF search                                 |
| !addcom [command] [text]                      | Add a custom command                       |
| !editcom [command] [text]                     | Edit a custom command                      |
| !delcom [command]                             | Delete a custom command                    |
| !customcommands                               | Custom commands' list                      |
| !help                                         | Command list                               |
| !audio help                                   | Audio command list and playlist explanation.|
| !economy                                      | Explanation of the economy module          |
| !admin help                                   | Admin commands list                        |

### Audio commands

| Command                    | Description                                                         |
|----------------------------|---------------------------------------------------------------------|
| !youtube [link]            | Play a youtube video in a voice channel                             |
| !sing                      | Make Red sing                                                       |
| !stop                      | Stop any voice channel activity                                     |
| !play [playlist_name]      | Play chosen playlist                                                |
| !playlists                 | Playlist's list                                                     |
| !next or !skip             | Next song                                                           |
| !prev                      | Previous song                                                       |
| !pause                     | Pause song                                                          |
| !resume                    | Resume song                                                         |
| !replay or !repeat         | Replay current song                                                 |
| !title or !song            | Current song's title + link                                         |
| !shuffle                   | Mix current playlist                                                |
| !volume [0-1]              | Sets Red's output volume                                            |
| !addplaylist [name] [link] | Add a youtube playlist                                              |
| !delplaylist [name]        | Delete a youtube playlist. Limited to author and admins             |
| !getplaylist               | Get the current playlist through DM. This also works with favorites |
| !addfavorite               | Add song to your favorites                                          |
| !delfavorite               | Remove song from your favorites                                     |
| !playfavorites             | Play your favorites                                                 |
| !local [playlist_name]     | Play chosen local playlist                                          |
| !local or !locallist       | Local playlists' list                                               |
| !downloadmode              | Enables or disables download mode. (admin only)                     |

### Admin commands

| Command                                                   | Description                                       |
|-----------------------------------------------------------|---------------------------------------------------|
| !addwords [word1 word2 (...)] [phrase/with/many/words]    | Add words to message filter                       |
| !removewords [word1 word2 (...)] [phrase/with/many/words] | Remove words from message filter                  |
| !addregex [regex]                                         | Add regular expression to message filter          |
| !removeregex [regex]                                      | Remove regular expression from message filter     |
| !shutdown                                                 | Close the bot                                     |
| !join [invite]                                            | Join another server                               |
| !leaveserver                                              | Leave server                                      |
| !shush                                                    | Ignore the current channel                        |
| !talk                                                     | Stop ignoring the current channel                 |
| !reload                                                   | Reload most files. Useful in case of manual edits |
| !name [name]                                              | Change the bot's name                             |
| !cleanup [number]                                         | Delete the last [number] messages                 |
| !cleanup [name/mention] [number]                          | Delete the last [number] of messages by [name]    |


### Economy commands

| Command     | Description                          |
|-------------|--------------------------------------|
| !register   | Register a new account               |
| !balance    | Check your balance                   |
| !slot [bid] | Play the slot machine                |
| !slot help  | Slot machine explanation and payouts |
| !payday     | Receive credits                      |

### FAQ
>I've done everything the README asked me to and it still doesn't work! Were you drunk when you coded this?  

You're probably missing something.  
Feel free to join [my server](https://discord.gg/0k4npTwMvTpv9wrh) and head to #support to get some help! Oh, and my drinking habits are none of your business.  

>Does this bot work on multiple servers?  

Sure it does. Should you do it? Maybe. The permissions system is not that great at the moment but if you trust the people running the server it's ok. It's not advisable to send the bot in random servers at the moment.   
Custom commands only work in the server they were created in. Same for the message filter. This is by design. Also, remember that the bot can only be in one voice channel at once.

>Will you implement [feature]?  

Suggestions are always very welcome.

>How do local playlists work?

Make as many folders as you want inside the localtracks folder. Names must be without spaces. Every folder counts as a different playlist. Every playlist can contain mp3 and flac files. Users can stream them by doing !local [playlist_name] and see the full list
with !local or !locallist. They can also add tracks to their favorites.

>What's download mode?

Everytime you play the audio of a youtube video with download mode on the audio will be first downloaded and stored into the "cache" folder. It is recommended that you use this mode to avoid streaming problems. This is the default mode, you can switch between modes with !downloadmode.

>Why is this bot called Red and the admin role "Transistor"? What's the meaning of !sing?

They're all references to [Transistor](https://www.supergiantgames.com/games/transistor/), a videogame by Supergiant Games.

### TODO List
- [ ] Redesign trivia, been broken since I moved to async branch
    - [ ] Find / make some decent questions list(s) for it
- [ ] Economy module is barebones. Expand it
- [ ] Make more admin commands
- [ ] More fleshed out permissions system
- [ ] Support more playlist link types
- [x] Add streaming of local mp3/flac files
- [ ]  ~~Bundle some malware and slowly build up a botnet for world domination~~
