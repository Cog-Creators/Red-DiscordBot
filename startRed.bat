@Echo off
chcp 65001

set get_pid_title=Red%DATE:/=-%@%TIME::=-%
TITLE %get_pid_title%
for /F "tokens=1-2" %%A in ('tasklist.exe /nh /fi "windowtitle eq %get_pid_title%"') do set red_pid=%%B
TITLE Red - Discordbot @ %red_pid%
echo %red_pid%> red.pid

python red.py
pause
