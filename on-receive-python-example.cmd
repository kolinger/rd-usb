@echo off

rem Example how to call python or other language
rem Replace python.exe with your python.exe
rem Replace on-receive-python-example.py with your .py script
rem The %* part is passing all arguments to .py script, required in order to make it work

call C:\Python311\python.exe on-receive-python-example.py %*
