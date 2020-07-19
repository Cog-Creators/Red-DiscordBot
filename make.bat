@echo off

if [%1] == [] goto help

goto %1

:reformat
"%~dp0.venv\Scripts\black" "%~dp0."
goto:eof

:stylecheck
"%~dp0.venv\Scripts\black" --check "%~dp0."
goto:eof

:stylediff
"%~dp0.venv\Scripts\black" --check --diff "%~dp0."
goto:eof

:newenv
py -3.8 -m venv --clear .venv
"%~dp0.venv\Scripts\python" -m pip install -U pip setuptools wheel
goto syncenv

:syncenv
"%~dp0.venv\Scripts\python" -m pip install -Ur .\tools\dev-requirements.txt
goto:eof

:activateenv
CALL "%~dp0.venv\Scripts\activate.bat"
goto:eof

:help
echo Usage:
echo   make ^<command^>
echo.
echo Commands:
echo   reformat                   Reformat all .py files being tracked by git.
echo   stylecheck                 Check which tracked .py files need reformatting.
echo   stylediff                  Show the post-reformat diff of the tracked .py files
echo                              without modifying them.
echo   newenv                     Create or replace this project's virtual environment.
echo   syncenv                    Sync this project's virtual environment to Red's latest
echo                              dependencies.
echo   activateenv                Activates project's virtual environment.
