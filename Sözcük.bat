@echo off
rem Sözcük'ü projenin sanal ortamıyla (konsol penceresi açmadan) başlatır.
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py" %*
