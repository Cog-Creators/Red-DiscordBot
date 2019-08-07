@echo off

if [%1] == [] goto help

REM This allows us to expand variables at execution
setlocal ENABLEDELAYEDEXPANSION

REM This will set PYFILES as a list of tracked .py files
set PYFILES=
for /F "tokens=* USEBACKQ" %%A in (`git ls-files "*.py"`) do (
    set PYFILES=!PYFILES! %%A
)

goto %1

:reformat
black -l 99 !PYFILES!
exit /B %ERRORLEVEL%

:stylecheck
black -l 99 --check !PYFILES!
exit /B %ERRORLEVEL%

:newenv
py -3.7 -m venv --clear .venv
.\.venv\Scripts\python -m pip install -U pip setuptools
goto syncenv

:syncenv
.\.venv\Scripts\python -m pip install -Ur .\tools\dev-requirements.txt
exit /B %ERRORLEVEL%

:checkchangelog
REM This should be written for windows at some point I guess.
REM If we can swith to powershell, it can make this much easier.
echo This doesn^'t do anything on windows ^(yet^)
exit /b 0

:help
echo Usage:
echo   make ^<command^>
echo.
echo Commands:
echo   reformat                   Reformat all .py files being tracked by git.
echo   stylecheck                 Check which tracked .py files need reformatting.
echo   newenv                     Create or replace this project's virtual environment.
echo   syncenv                    Sync this project's virtual environment to Red's latest
echo                              dependencies.
