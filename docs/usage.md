# Usage

## Quick start

The default factory ip of C3 devices is `192.168.1.201`.

```python
from pyzkaccess import ZKAccess

connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
zk = ZKAccess(connstr=connstr)
print('Device SN:', zk.parameters.serial_number, 'IP:', zk.parameters.ip_address)

# Turn on relays in "lock" group for 5 seconds
zk.relays.lock.switch_on(5)

# Wait for any card will appear on reader of Door 1
card = None
while not card:
    for door1_event in zk.doors[0].events.poll(timeout=60):
        print(door1_event)
        if door1_event.card and door1_event.card != '0':
            print('Got card #', door1_event.card)
            card = door1_event.card

# Switch on both relays on door 1
zk.doors[0].relays.switch_on(5)

# After that restart a device
zk.restart()
zk.disconnect()
```

## Working with a device

#### Use as context manager

```python
from pyzkaccess import ZKAccess

connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
with ZKAccess(connstr=connstr) as zk:
    print(zk.parameters.ip_address)
```

#### Find a device in a local network and connect to it

```python
from pyzkaccess import ZKAccess

found = ZKAccess.search_devices('192.168.1.255')
print(len(found), 'devices found')
if found:
    # Pick the first device
    device = found[0]

    with ZKAccess(device=device) as zk:
        print(zk.parameters.ip_address)
```

#### Default model is C3-400. Here is how to use another device model
```python
from pyzkaccess import ZKAccess, ZK200

connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
with ZKAccess(connstr=connstr, device_model=ZK200) as zk:
    print(zk.parameters.ip_address)
```

#### Set current datetime
```python
from pyzkaccess import ZKAccess
from datetime import datetime

connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
with ZKAccess(connstr=connstr) as zk:
    zk.parameters.datetime = datetime.now()
```

#### Change ip settings
```python
from pyzkaccess import ZKAccess

connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
with ZKAccess(connstr=connstr) as zk:
    zk.parameters.gateway_ip_address = '172.31.255.254'
    zk.parameters.netmask = '255.240.0.0'
    zk.parameters.ip_address = '172.17.10.2'
```

## Relays

The main operation we can do with a relay is to switch on it for a given count of seconds (0..255).
Relay number corresponds to its number on board starting from aux relay group.
A relay can be accessed by different ways:

```
zk.relays.switch_on(5)  # All relays
zk.relays[0].switch_on(5)  # By index
zk.relays[1:3].switch_on(5)  # By range
zk.doors[0].relays[0].switch_on(5)  # By number of door which it belongs to
zk.relays.aux.switch_on(5)  # By group
zk.relays.aux[1].switch_on(5)  # By index in group
zk.relays.by_mask([1, 0, 1, 0, 0, 0, 0, 0]).switch_on(5)  # By mask
```

## Readers

The main operation we can do with a reader is to read its events. Number of reader is denoted on
board. Readers can be accessed by different ways:

```
zk.readers.events.refresh()  # All readers
zk.readers[0].events.refresh()  # By index
zk.readers[1:3].events.refresh()  # By range
zk.readers[1:3].events.poll()  # Await events for readers 2 and 3
zk.doors[0].reader.events.refresh()  # By number of door which it belongs to
``` 

## Aux inputs

Like for a reader, the main operation for aux input is to read events. The number of aux input
is also denoted on board. Aux inputs can be accessed by different ways:

```
zk.aux_inputs.events.refresh()  # All aux inputs
zk.aux_inputs[0].events.refresh()  # By index
zk.aux_inputs[1:3].events.refresh()  # By range
zk.aux_inputs[1:3].events.poll()  # Await events for aux inputs 2 and 3
zk.doors[0].aux_input.events.refresh()  # By number of door which it belongs to
``` 

## Events

Events are accessible through `.events` property. C3 controller keeps
maximum 30 last unread events. Events start to register just after making connection to a device.

Event log should be refreshed manually using `refresh()` method. Due to restriction of 
maximum 30 entries described above, you should call `refresh()` periodically in order to avoid
losing new events.

Another way to obtain events is `poll()` method which awaits new log entries by doing
periodical refresh and returns new events if any.

Event log is available in several places. For `ZKAccess` object it keeps all events occured on
a device. Readers, doors, aut inputs also give access to events which are related to this reader.
Under the hood these properties use the same event list which keeps all device events, but
each one apply its own filter to this list.

```
zk.events  # Event log with all events occured on a device
zk.events.refresh()  # Get unread events from device
zk.events.poll()  # Wait until any event will occur
zk.door.events  # Event log for all doors (exluding auto open door by time for instance)
zk.aux_inputs.events  # Event log related to aux inputs only
zk.readers.events  # Event log related to readers only

#
# More complex examples
#
# Wait until an some event will occur on Door 1 reader
zk.door[0].reader.events.poll()
# Wait until unregistered card (event_type 27) with given number will appear on Door 1 reader 
zk.door[0].reader.events.only(card='123456', event_type=27).poll()
# Take all records from log with given card which was occur after 2010-10-11 14:28:04
zk.events.only(card='123456').after_time(datetime(2010, 10, 11, 14, 28, 4))
```
