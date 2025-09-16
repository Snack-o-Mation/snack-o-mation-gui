# Snack-o-Mation TecDay Module

This folder contains the graphical user interface for the Snack-o-Mation TecDay Automation Module.

## License
* This project is licensed under the terms of the MIT license (see LICENSE.txt).
* This project uses icons from Google's Material Symbols / Material Icons, which are licensed under the Apache license version 2.0. 

## Dependencies
The following software libraries are required by the GUI:
* [Python 3](https://python.org)
* [pySerial](https://github.com/pyserial/pyserial)
* [pySide6](https://doc.qt.io/qtforpython-6/)
* [pydobot](https://github.com/luismesas/pydobot)

## Installation Guide
1. Install the dependencies using:  
   `pip install -r requirements.txt`  
   Hint: On Ubuntu you can alternatively install the dependencies using the `apt` package manager:  
   `sudo apt install python3-qtpy-pyside6 python3-serial`

2. Set group memberships for `tecday` user (Linux only, logout/login required):
    ```
    sudo usermod -a -G dialout tecday
    sudo usermod -a -G plugdev tecday
    ```

3.Install the udev rules (Linux only):
    ```
    cd udev
    sudo cp *.rules /etc/udev/rules.d/
    sudo udevadm control --reload-rules && sudo udevadm trigger
    ```

## User Guide
Start the UI with default serial port settings as follows:  
`python ui.py`

Start the UI with custom port settings as follows:  
`python ui.py --microbit <port-microbit> --left <port-dobot-left> --right <port-dobot-right>`

## Known Issues:
* The UI has issues when running on Windows 10/11. This might be related to a change in the virtual serial port driver by Silicon Labs, see here: https://community.silabs.com/s/question/0D58Y00009WHoU6SAL/latest-driver-v1120-works-incorrectly-with-cp210x-cp2102gmr-on-windows-10-pro?language=de