@echo off
set "PATH=E:\Program\anaconda3\envs\oymm\Library\bin;%PATH%"
cd /d E:\oymm
E:\Program\anaconda3\envs\oymm\python.exe -c "import sys; sys.path.insert(0,'E:/oymm'); from oymm_app.main import main; main()" > E:\oymm\scripts\app_stdout.log 2> E:\oymm\scripts\app_stderr.log
echo Exit code: %ERRORLEVEL% >> E:\oymm\scripts\app_stderr.log
