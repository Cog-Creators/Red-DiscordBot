@echo off

if [%1] == [] goto help

REM This allows us to expand variables at execution
setlocal ENABLEDELAYEDEXPANSION

goto %1

:reformat
black "%~dp0."
exit /B %ERRORLEVEL%

:stylecheck
black --check "%~dp0."
exit /B %ERRORLEVEL%

:stylediff
black --check --diff "%~dp0."
exit /B %ERRORLEVEL%

:newenv
py -3.8 -m venv --clear .venv
.\.venv\Scripts\python -m pip install -U pip setuptools wheel
goto syncenv

:syncenv
.\.venv\Scripts\python -m pip install -Ur .\tools\dev-requirements.txt
exit /B %ERRORLEVEL%

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
