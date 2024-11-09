# Installation

## Windows

### Portable executable

The quickest way is to use [portable pyzkaccess.exe](https://github.com/bdragon300/pyzkaccess/releases/latest).
It contains the full `pyzkaccess` package with built-in Python and necessary libraries.
Download it and run the `pyzkaccess.exe setup` to install PULL SDK.

Finally, check the installation by running the `pyzkaccess.exe search_devices` command.

### Manual installation

`pyzkaccess` requires the **32-bit** [Python version for Windows](https://www.python.org/downloads/windows/).
*Make sure you ticked the checkbox "Add executable to PATH variable" in Python installer.*

Open up the command window and install this library from pip:

```
pip install pyzkaccess
```

Next, install a current version of PULL SDK -- just run the `pyzkaccess setup` command and follow the instructions

> As alternative, you can install the SDK manually:
>
> * download the PULL SDK from [ZKTeco software downloads](https://zkteco.eu/downloads)
> * extract the archive
> * copy `pl*.dll` files to the **32-bit** system directory. Usually it's `C:\Windows\SysWOW64`
>   (or `C:\Windows\System32` on older 32-bit Windows versions).

Finally, check the installation by running the `pyzkaccess search_devices` command.

## *nix

### Prerequisites

First, you will need to set up **32-bit** Wine environment (commands below are relevant for Debian/Ubuntu):

```
apt-get install wine wine32
```

### Portable executable

The quickest way is to use [portable pyzkaccess.exe](https://github.com/bdragon300/pyzkaccess/releases/latest/download/pyzkaccess.exe).
It contains the full `pyzkaccess` package with built-in Python and necessary libraries.
Download it and run the `wine pyzkaccess.exe setup` to install PULL SDK.

Finally, check the installation by running the `wine pyzkaccess.exe search_devices` command.

### Manual installation

This package requires the **32-bit** [Python version for Windows](https://www.python.org/downloads/windows/).

Open up the terminal and install Python:

```
wine python-3.8.5.exe`
```

*Make sure you ticked the checkbox "Add executable to PATH variable in Python installer."*

Next, install this library from pip:

```
pip install pyzkaccess
```

Next, install a current version of PULL SDK -- just run the `pyzkaccess setup` command and follow the instructions

> As alternative, you can install the SDK manually:
>
> * download the PULL SDK manually from [ZKTeco software downloads](https://zkteco.eu/downloads)
> * extract the archive
> * copy `pl*.dll` files to the **32-bit** system directory. Usually it's `/home/user/.wine/drive_c/windows/SysWOW64`
>   (or `/home/user/.wine/drive_c/windows/system32` if the 32-bit Windows version selected in config).
>
> *Sometimes Wine doesn't see SDK \*.dll files has been copied. In this case you may
> run `wine explorer.exe` and copy them in its window*
