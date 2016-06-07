@Echo off
chcp 65001
:Start

python scootabot.py
timeout 3

goto Start