@Echo off
chcp 65001
:Start

python red.py
timeout 3

goto Start