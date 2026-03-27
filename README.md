# Snack-o-Mation TecDay Module

This folder contains the graphical user interface for the Snack-o-Mation automation module developed by [ABB](https://www.abb.com) Corporate Research Switzerland for the [SATW TecDays](https://mint.satw.ch/de/tecdays). This work has also been presented at the [IoT Teaching Workshop](https://blogs.uni-bremen.de/teachingiot/) at [EWSN 2025](https://www.ewsn25.cs.kuleuven.be/) in Leuven, Belgium. You can download our research paper [here](https://blogs.uni-bremen.de/teachingiot/files/teach-iot25-final14.pdf).

## License
* This project is licensed under the terms of the MIT license (see LICENSE.txt).
* This project uses icons from Google's Material Symbols / Material Icons, which are licensed under the Apache license version 2.0. 

## Dependencies
The following software libraries are required by the GUI:
* [Python 3](https://python.org)
* [pySerial](https://github.com/pyserial/pyserial)
* [pySide6](https://doc.qt.io/qtforpython-6/)
* [pydobot](https://github.com/luismesas/pydobot) (Note: we use our own [repository](../pydobot) of pydobot, which is forked version with some time.sleep() statements removed during read/write from/to the serial port)

## Installation Guide
1. Install the dependencies using:  
   `pip install -r requirements.txt`  
   Hint: On Ubuntu you can alternatively install the dependencies using the `apt` package manager:  
   `sudo apt install python3-qtpy-pyside6 python3-serial`

2. Set group memberships for your current user (Linux only, logout/login required):
    ```
    sudo usermod -a -G dialout $USER
    sudo usermod -a -G plugdev $USER
    ```

3. Install udev rules to create stable symbolic links to the serial devices (Linux, optional):
    Create a file called `/etc/udev/rules.d/90-dobot-microbit.rules` with the following content:  
    ```
   # left Dobot
    SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60",ATTRS{serial}=="<replace-with-your-serial>",SYMLINK+="tty-dobot-left"
    # right Dobot
    SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60",ATTRS{serial}=="<replace-with-your-serial>",SYMLINK+="tty-dobot-right"
    SUBSYSTEM=="usb", ATTR{idVendor}=="0d28", MODE="0664", GROUP="plugdev"
    SUBSYSTEM=="tty", ATTRS{idVendor}=="0d28", MODE="0664", GROUP="plugdev",SYMLINK+="tty-microbit" 
   ```
    Replace the placeholders `<replace-with-your-serial>` with the serial number of the corresponding serial device. You can find the serial number for a given device, e.g. `/dev/ttyUSB1` with the following command: 
    ```
   udevadm info -a -n /dev/ttyUSB1 | grep '{serial}'
   ```
   Reload the udev rules to activate them: 
   ```
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```

## User Guide
Start the UI with default serial port settings as follows:  
`python ui.py`

Start the UI with custom port settings as follows:  
`python ui.py --microbit <port-microbit> --left <port-dobot-left> --right <port-dobot-right>`

Start the UI with a different language (default is `de`):
`python ui.py --microbit <port-microbit> --left <port-dobot-left> --right <port-dobot-right> --language en`

Supported languages: `de`, `en`, `fr`, `it`. Additional languages can be added in the translation file `languages/translations.json`.

## Known Issues:
* The UI has issues when running on Windows 10/11. This might be related to a change in the virtual serial port driver by Silicon Labs, see here: https://community.silabs.com/s/question/0D58Y00009WHoU6SAL/latest-driver-v1120-works-incorrectly-with-cp210x-cp2102gmr-on-windows-10-pro?language=de