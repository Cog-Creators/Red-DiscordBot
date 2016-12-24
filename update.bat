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

:ban2x
FOR /F "tokens=* USEBACKQ" %%V IN (`python --version`) DO (
SET pt=%%V
)
set ptv=%pt:~7,1%
IF %ptv%== 2 (goto halt) else (goto choose)


:halt
echo Your default python version is lower than the requirements (Python 3.5 or higher)
echo OR this script is not able to detect it ... yet
CHOICE /M "You still want to continue?"
IF errorlevel 2 goto end
IF errorlevel 1 goto choose
PAUSE

:choose
set u=%username%
echo %u%
echo.
IF EXIST "C:\Users\%u%\AppData\Local\Programs\Python\Python35*" echo 1) Python 3.5.x
IF EXIST "C:\Users\%u%\AppData\Local\Programs\Python\Python36*" echo 2) Python 3.6.x
echo 3) Use AUTO Detect for default Python version

echo.
set /p a=
if %a%== 01 goto p35
if %a%== 1 goto p35
if %a%== 02 goto p36
if %a%== 2 goto p36
if %a%== 03 goto pyvars
if %a%== 3 goto pyvars

:p35
set ptv=3.5
echo %ptv%
goto startupdate

:p36
set ptv=3.6
echo %ptv%
goto startupdate

:pyvars
FOR /F "tokens=* USEBACKQ" %%V IN (`py.exe --version`) DO (
SET pt=%%V
)
set ptv=%pt:~7,3%
echo %ptv%

:startupdate
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
%SYSTEMROOT%\py.exe -%ptv% -m pip install --upgrade -r requirements.txt
PAUSE
GOTO end

::Attempts to start py launcher by relying on PATH
:attempt
py.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO lastattempt
py.exe -%ptv% -m pip install --upgrade -r requirements.txt
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
echo Couldn't find a valid Python 3.5 or higher installation. Python needs to be installed and available in the PATH environment variable.
echo https://twentysix26.github.io/Red-Docs/red_install_windows/#software
PAUSE
GOTO end

:gitmessage
echo Git is either not installed or not in the PATH environment variable. Install it again and add it to PATH like shown in the picture
echo https://twentysix26.github.io/Red-Docs/red_install_windows/#software
PAUSE

:end
