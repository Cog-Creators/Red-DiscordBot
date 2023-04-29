@echo off

if [%1] == [] goto help

if exist "%~dp0.venv\" (
    set "VENV_PYTHON=%~dp0.venv\Scripts\python"
) else (
    set VENV_PYTHON=python
)

goto %1

:reformat
echo - black:
"%VENV_PYTHON%" -m black "%~dp0."
echo - ruff:
"%VENV_PYTHON%" -m ruff --fix-only "%~dp0."
goto:eof

:stylecheck
echo - black:
"%VENV_PYTHON%" -m black --check "%~dp0."
if %errorlevel% neq 0 (
    goto:eof
)
echo - ruff:
"%VENV_PYTHON%" -m ruff --select I001 --no-fix "%~dp0."
goto:eof

:stylediff
echo WARNING: black and ruff diffs aren't combined! Consider using pre-commit instead.
echo - black:
"%VENV_PYTHON%" -m black --check --diff "%~dp0."
if %errorlevel% neq 0 (
    goto:eof
)
echo - ruff:
"%VENV_PYTHON%" -m ruff --fix-only --diff "%~dp0."
goto:eof

:newenv
py -3.8 -m venv --clear .venv
"%~dp0.venv\Scripts\python" -m pip install -U pip wheel
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
