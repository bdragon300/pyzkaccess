# Quick start

The quickest way is using [our portable executable](https://github.com/bdragon300/pyzkaccess/releases/latest/download/pyzkaccess.exe).

Download it, open up a terminal window and run it to setup the environment:

```console
pyzkaccess setup
```

It will make a quick compatibility check of your system and suggest you to install PULL SDK from the official ZKTeco site.

![pyzkaccess setup](docs/img/setup_screenshot.png)

All set! Now let's find out what ZKAccess devices are available on the local network:

```console
$ pyzkaccess search_devices
+---------------+-------------------+--------+---------------------+--------------------------+
| ip            | mac               | model  | serial_number       | version                  |
+---------------+-------------------+--------+---------------------+--------------------------+
| 192.168.1.201 | 00:17:61:C3:BA:55 | C3-400 | DGD9190010050345332 | AC Ver 4.3.4 Apr 28 2017 |
+---------------+-------------------+--------+---------------------+--------------------------+
```

Let's enumerate all users registered on a device:

```console
$ pyzkaccess connect 192.168.1.201 table User
+----------+------------+-------+----------+-----+------------+-----------------+
| card     | end_time   | group | password | pin | start_time | super_authorize |
+----------+------------+-------+----------+-----+------------+-----------------+
| 16268812 | 2020-12-01 | 2     | 123456   | 1   | 2020-06-01 | 1               |
| 16268813 |            | 3     | 123451   | 3   |            | 0               |
+----------+------------+-------+----------+-----+------------+-----------------+
```

For more usage examples, please see the [usage](#usage.md) section.
