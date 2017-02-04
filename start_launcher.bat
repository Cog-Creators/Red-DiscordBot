@echo off

title Red Discord Bot - Windows Launcher

::Replace with 0C for the Red experience
color 0F

mode con: cols=85 lines=14
pushd %~dp0

::Filling the voice on first launch
echo(
echo( Please wait
echo(

chcp 65001 > NUL
cls


::Attempts to start py launcher without relying on PATH
%SYSTEMROOT%\py.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO attempt1
%SYSTEMROOT%\py.exe -3.5 --version
IF %ERRORLEVEL% NEQ 0 GOTO attempt
%SYSTEMROOT%\py.exe -3.5 launcher.py
GOTO end

:attempt
%SYSTEMROOT%\py.exe -3 launcher.py
IF %ERRORLEVEL% NEQ 0 goto attempt1
GOTO end

::Attempts to start py launcher by relying on PATH
:attempt1
py.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO lastattempt
py.exe -3.5 --version
IF %ERRORLEVEL% NEQ 0 GOTO attempt2
py.exe -3.5 launcher.py
GOTO end

:attempt2
py.exe -3 --version
IF %ERRORLEVEL% NEQ 0 GOTO lastattempt
py.exe -3 launcher.py
GOTO end

::As a last resort, attempts to start whatever Python there is
:lastattempt
python.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO message
python.exe launcher.py
GOTO end

:message
cks
echo( Couldn't find a valid Python ^>3.5 installation. Python needs to be installed and available in the PATH environment
echo( variable.
echo( Please visit https://twentysix26.github.io/Red-Docs/red_win_requirements/#software
echo(
goto message

:end
exit
