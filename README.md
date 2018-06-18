# pyzkaccess

**pyzkaccess** is small library for low-level operating the ZKTeco ZKAccess C3 family access control panels. Python 3 is used.

Now implemented:

* Relay switching
* Device inputs state read and events retrieving

The ZKTeco's PULL SDK (plcommpro.dll) is used as machinery. Therefore the code must execute in Windows environment or Wine. Tested on C3-400.

# Installing

`pip3 install -r requirements.txt`

# SDK installing

First, download current version of PULL SDK: [ZKTeco software downloads](https://www.zkteco.eu/index.php/downloads/software-downloads).

Extract archive and place all pl*.dll files to the system directory, usually *windows/system32*.

On *nix systems you can use Wine.

# Usage

Turn on the relay:
```
from pyzkaccess import ZKAccess, RelayGroup

connstr = 'protocol=TCP,ipaddress=172.16.1.1,port=4370,timeout=4000,passwd='
with ZKAccess('plcommpro.dll', connstr) as zk:
    zk.enable_relay(RelayGroup.lock, 1, 16)  # Turn on the first relay in 'lock' group for 16 seconds
```

Read aux input state:
```
import time
from pyzkaccess import ZKAccess

connstr = 'protocol=TCP,ipaddress=172.16.1.1,port=4370,timeout=4000,passwd='
with ZKAccess('plcommpro.dll', connstr) as zk:
    while (1):
        events = zk.read_events()
        for e in events:
            if e.event_type == '221' and e.door == '1':
                print("Auxiliary input on door {} shorted at {}".format(e.door, e.time))
            elif e.event_type == '220' and e.door == '1':
                print("Auxiliary input on door {} released at {}".format(e.door, e.time))

        time.sleep(1)
```

# Author

Igor Derkach, <gosha753951@gmail.com>


# Bugs

Please report any bugs or feature requests to the author.
