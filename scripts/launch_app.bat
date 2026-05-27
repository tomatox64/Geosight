@echo off
call E:\Program\anaconda3\Scripts\activate.bat oymm
cd /d E:\oymm
start "" E:\Program\anaconda3\envs\oymm\python.exe -c "import sys; sys.path.insert(0,'E:/oymm'); from oymm_app.main import main; main()"
