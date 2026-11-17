@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 add_to_max.py %*) || (python add_to_max.py %*)
pause
