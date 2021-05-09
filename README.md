# PyZKAccess

[![version](https://img.shields.io/pypi/v/pyzkaccess)](https://pypi.org/project/pyzkaccess/)
[![pyversions](https://img.shields.io/pypi/pyversions/pyzkaccess)](https://pypi.org/project/pyzkaccess/)
[![travis](https://img.shields.io/travis/com/bdragon300/pyzkaccess/master)](https://travis-ci.com/github/bdragon300/pyzkaccess)
[![codecov](https://codecov.io/gh/bdragon300/pyzkaccess/branch/master/graph/badge.svg)](https://codecov.io/gh/bdragon300/pyzkaccess)
[![license](https://img.shields.io/github/license/bdragon300/pyzkaccess)](https://github.com/bdragon300/pyzkaccess/blob/master/LICENSE)

**PyZKAccess** is a library and command-line interface for working with ZKTeco ZKAccess 
C3-100/200/400 access controllers.

[Read documentation](https://bdragon300.github.io/pyzkaccess)

# Quick start

First, you need to install ZKTeco PULL SDK. See documentation for more info.

In order to make requests to your C3 device, you need to know its IP address. Let's scan a 
local network and find a device:

```console
$ pyzkaccess search_devices
+---------------+-------------------+--------+---------------------+--------------------------+
| ip            | mac               | model  | serial_number       | version                  |
+---------------+-------------------+--------+---------------------+--------------------------+
| 192.168.1.201 | 00:17:61:C3:BA:55 | C3-400 | DGD9190010050345332 | AC Ver 4.3.4 Apr 28 2017 |
+---------------+-------------------+--------+---------------------+--------------------------+
```

Now you can connect to a device using its IP and, for example, print list of all Users:

```console
$ pyzkaccess connect 192.168.1.201 table User
+----------+------------+-------+----------+-----+------------+-----------------+
| card     | end_time   | group | password | pin | start_time | super_authorize |
+----------+------------+-------+----------+-----+------------+-----------------+
| 16268812 | 2020-12-01 | 2     | 123456   | 1   | 2020-06-01 | 1               |
| 16268813 |            | 3     | 123451   | 3   |            | 0               |
+----------+------------+-------+----------+-----+------------+-----------------+
```

Or select only needed records:

```console
$ pyzkaccess connect 192.168.1.201 table User where --card=16268812
+----------+------------+-------+----------+-----+------------+-----------------+
| card     | end_time   | group | password | pin | start_time | super_authorize |
+----------+------------+-------+----------+-----+------------+-----------------+
| 16268812 | 2020-12-01 | 2     | 123456   | 1   | 2020-06-01 | 1               |
+----------+------------+-------+----------+-----+------------+-----------------+
```

Also, you can update or delete records from csv file. Or even delete all records from a query:

```console
$ cat users1.csv | pyzkaccess --format=csv connect 192.168.1.201 table User upsert
$ cat users2.csv | pyzkaccess --format=csv connect 192.168.1.201 table User delete
$ pyzkaccess connect 192.168.1.201 table User --card=16268812 delete_all
```

Switching relays and awaiting device events:

```console
$ pyzkaccess connect 192.168.1.201 relays switch_on
$ pyzkaccess connect 192.168.1.201 events --event_type=23 poll
           card door     entry_exit     event_type  pin                     time    verify_mode
       16268813    1              0             23    3      2020-05-09 22:35:55              0
```

Getting and setting parameters:

```console
$ pyzkaccess connect 192.168.1.201 parameters --names=ip_address,serial_number,datetime
+---------------------+---------------+---------------------+
| datetime            | ip_address    | serial_number       |
+---------------------+---------------+---------------------+
| 2020-05-09 22:42:31 | 192.168.1.201 | DGD9190010050345332 |
+---------------------+---------------+---------------------+
$ pyzkaccess connect 192.168.1.201 parameters set --datetime='2020-05-09 22:42:31' --rs232_baud_rate=57600
```
