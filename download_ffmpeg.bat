@echo off
pushd %~dp0
IF "%PROCESSOR_ARCHITECTURE%"=="x86" (GOTO 32bit) else (GOTO 64bit)
echo Couldn't detect system bitness.
PAUSE
GOTO end

:32bit
echo Windows 32bit detected. You'll need to manually install ffmpeg. Once you press enter I'm going to open a web page.
echo Keep following the instructions.
PAUSE
start "" https://ffmpeg.zeranoe.com/builds/
echo Download "FFmpeg 32-bit Static"
echo Open the file and copy the 3 exe files from the "bin" folder into the Red-DiscordBot folder
PAUSE
GOTO end

:64bit
echo Downloading files... Do not close.
echo Downloading ffmpeg.exe (1/3)...
powershell -Command "(New-Object Net.WebClient).DownloadFile('https://github.com/Twentysix26/Red-DiscordBot/raw/master/ffmpeg.exe', 'ffmpeg.exe')"
echo Downloading ffplay.exe (2/3)...
powershell -Command "(New-Object Net.WebClient).DownloadFile('https://github.com/Twentysix26/Red-DiscordBot/raw/master/ffplay.exe', 'ffplay.exe')"
echo Downloading ffprobe.exe (3/3)...
powershell -Command "(New-Object Net.WebClient).DownloadFile('https://github.com/Twentysix26/Red-DiscordBot/raw/master/ffprobe.exe', 'ffprobe.exe')"
PAUSE

:end