@echo off
chcp 65001
echo.
pushd %~dp0

net session >nul 2>&1
if NOT %errorLevel% == 0 (
    echo This script NEEDS to be run as administrator.
    echo Right click on it ^-^> Run as administrator
    echo.
    PAUSE
    GOTO end  
)

::Checking git and updating
git.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO gitmessage
echo Updating Red...
git stash
git pull

echo.
echo Updating requirements...
::Attempts to start py launcher without relying on PATH
%SYSTEMROOT%\py.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO attempt
%SYSTEMROOT%\py.exe -3.5 -m pip install --upgrade -r requirements.txt
PAUSE
GOTO end

::Attempts to start py launcher by relying on PATH
:attempt
py.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO lastattempt
py.exe -3.5 -m pip install --upgrade -r requirements.txt
PAUSE
GOTO end

::As a last resort, attempts to start whatever Python there is
:lastattempt
python.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO pythonmessage
python.exe -m pip install --upgrade -r requirements.txt
PAUSE
GOTO end

:pythonmessage
echo Couldn't find a valid Python 3.5 installation. Python needs to be installed and available in the PATH environment variable.
echo https://twentysix26.github.io/Red-Docs/red_install_windows/#software
PAUSE
GOTO end

:gitmessage
echo Git is either not installed or not in the PATH environment variable. Install it again and add it to PATH like shown in the picture
echo https://twentysix26.github.io/Red-Docs/red_install_windows/#software
PAUSE

:end
