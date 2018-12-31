Web GUI for RuiDeng USB testers (UM34C, UM24C, UM25C) 
==

Simple web GUI written in Python 3. Measurements are stored in sqlite database. Tables and graphs are supported. 
Live preview and graphing is also available.

Tested on UM34C/UM24C/UM25C.

Based on https://github.com/sebastianha/um34c


Requirements
--
- **Python >3.6**
- USB meter needs to be connected as serial port
    - Pairing with Windows Settings works fine. After successful installation some serial ports are 
    installed in Device Manager. In my case two. One of them works.
    - On Linux `rfcomm` can be used


Installation
--
- Download from github or `git clone https://github.com/kolinger/rd-usb.git`
- Install requirements `pip install -r requirements.txt`
- Run with `python web.py` - this will spawn web server on http://127.0.0.1:5000, port can be changed 
with first argument: `python web.py 5555`

On Windows `python` can be found in Python's installation folder. 
For example replace `python` with `C:\Python37\python.exe web.py` 
and `pip` with `C:\Python37\python.exe -m pip install -r requirements.txt`.

On Linux use `python3` and `pip3`.

Setup
--

1. Find your serial port (in Device Manager) and fill serial port input.
2. Name your session. For example 'testing some power bank'. This is 
used to seperate multiple measurements from each other.
3. Select sample rate. Faster sample rate will result in more accurate data but also
will create a lot more data. For short measurements use faster sample rate. For longer 
use slower rate. Choose carefuly.
4. Click Connect
5. Connection will be hopefully successful and you will see measurements in log. 
Otherwise read log for error messages.

![setup](screenshots/setup.png)

Graphs
--

![tables](screenshots/graphs.png)

Tables
--

![tables](screenshots/tables.png)
