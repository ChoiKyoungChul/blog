@echo off
chcp 65001 > nul
cd /d C:\laragon\www\blog
python daily_post.py --publish >> daily_log.txt 2>&1
