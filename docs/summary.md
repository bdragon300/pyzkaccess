# PyZKAccess

**PyZKAccess** is a library for working with ZKTeco ZKAccess C3-100/200/400 access controllers.

The ZKTeco PULL SDK is used as machinery. Therefore the code is executed in Windows 
environment. *nix are also supported using Wine.

## Features

* Relays switching
* Reading events of whole device or separately for certain reader, aux input or even door
* Getting/setting the device parameters such as datetime, network settings, entry modes, backup 
  time, etc.
* Getting/setting a door parameters such as smart card modes, intervals, entry modes, etc.
* Scanning the local network in searching for active C3 devices
* Restarting a device

Here are the controllers we're taking about:

C3-100 | C3-200 | C3-400
------ | ------ | ------
![alt text](img/c3-100.png "C3-100 controller") | ![alt text](img/c3-200.png "C3-200 controller") | ![alt text](img/c3-400.png "C3-400 controller")


### To be implemented

* Pulling data from a device with filtering support (cards, ACL, holidays and timezone info,
  access history, i/o table)
* Uploading data to a device (the same)
* CLI interface
* Downloading/uploading files from PC to/from a device
* Restoring from SD card backup
* Cancelling alarm function
* Emergency resetting network settings

**NOTE**: the version `pyzkaccess>=0.2` is incompatible with `pyzkaccess==0.1`

## Author

Igor Derkach, <gosha753951@gmail.com>
