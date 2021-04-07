# Installing

Requirements:

* python >= 3.5
* wrapt

## PULL SDK

Download a current version of PULL SDK and extract the archive: 
[ZKTeco software downloads](https://www.zkteco.eu/index.php/downloads/software-downloads).

A downloaded archive contains `pl*.dll` DLL files and documentation.


## *nix

First, you will need to set up Wine (32-bit) environment (commands below are for Debian/Ubuntu):

`apt-get install wine`

Next, install the last [Python version for Windows](https://www.python.org/downloads/windows/):

`wine python-3.8.5.exe`

*Make sure you checked the box "Add executable to PATH variable"*. Next, install the library:

`wine pip install pyzkaccess`

Finally, copy `pl*.dll` files from SDK archive to Wine `system32` directory, usually it is 
`/home/user/.wine/drive_c/windows/system32` (executing the `regsvr32` is not needed).

*(Sometimes Wine doesn't see dll files even if you have copied them right. In this case you may
run `wine explorer.exe` and move these files using it)*

## Windows

Install the last [Python version for Windows](https://www.python.org/downloads/windows/). Next,
open command window and install library from pip:

`pip install pyzkaccess`

Finally, copy `pl*.dll` files from SDK archive to system32 directory, usually it is 
`C:\Windows\System32` (executing the `regsvr32` is not needed).
