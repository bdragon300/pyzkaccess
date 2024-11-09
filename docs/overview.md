# Overview

This package allows you to work with ZKTeco ZKAccess C3-100/200/400 access controllers.

This library is Windows-only, but it can be used on *nix systems with Wine. It built on top of the ZKTeco PULL SDK.

This package, once installed, may be used as library or command-line interface. It's also distributed as
a portable Windows executable, created by [PyInstaller](https://pyinstaller.org/en/stable/) with built-in 32-bit Python
interpreter.

Here are the controllers we work with:

C3-100 | C3-200 | C3-400
------ | ------ | ------
![alt text](img/c3-100.png "C3-100 controller") | ![alt text](img/c3-200.png "C3-200 controller") | ![alt text](img/c3-400.png "C3-400 controller")

NOTE: the default factory IP address of C3 devices is `192.168.1.201`.

## Features

- Can be used as a code library or a command-line tool
- Reading and writing the device data tables
- Making queries to device data tables
- CSV format support
- On-board relays control
- Read the realtime events of a particular reader, aux input, door or the whole device
- Manipulation the device parameters such as datetime, network settings, entry modes, backup time, etc.
- Manipulation the door parameters such as smart card modes, intervals, entry modes, etc.
- Restart a device
- Scan the local network for active C3 devices
- Download/upload files from PC to/from a device
- Cancel alarm function
- Reset the device IP address by its MAC address
