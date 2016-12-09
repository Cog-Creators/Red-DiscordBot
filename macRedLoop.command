#! /bin/bash
cd "$(dirname "$0")"
while true
do
printf "\n+------\n------+\n+------\n+\n---------\n Starting red startup loop. ctrl+c a couple times quickly to stop :3 May also have to !shutdown bot on discord.\n ---------\n+------\n------+\n+------\n+------\n"
python3 red.py
printf "\n+\n+\n----Red stopped. If you haven't closed your terminal in a week, you should probably close it and reopen it----\n+\n+\n"
sleep 3
done
