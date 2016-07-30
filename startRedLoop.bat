@Echo off
chcp 65001
pushd %~dp0
:Start

python red.py
timeout 3

goto Start
