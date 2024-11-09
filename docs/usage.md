# Library usage

Let's look how to use this package in your code.

## Quick start

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

## Working with library

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

#### Using a certain device model

*Default device model is `ZK400` (C3-400).*

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

#### Change IP settings

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

Relays can be addressed in different ways:

```python
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
the board. Readers can be addressed in different ways:

```python
zk.readers.events.refresh()  # All readers
zk.readers[0].events.refresh()  # By index
zk.readers[1:3].events.refresh()  # By range
zk.readers[1:3].events.poll()  # Await events for readers 2 and 3
zk.doors[0].reader.events.refresh()  # By number of door which it belongs to
```

## Aux inputs

The main operation for aux input is to read events. The number of aux input
is also denoted on the board. Aux inputs can be addressed in different ways:

```python
zk.aux_inputs.events.refresh()  # All aux inputs
zk.aux_inputs[0].events.refresh()  # By index
zk.aux_inputs[1:3].events.refresh()  # By range
zk.aux_inputs[1:3].events.poll()  # Await events for aux inputs 2 and 3
zk.doors[0].aux_input.events.refresh()  # By number of door which it belongs to
```

## Events

Events are the way to monitor the device in real time. It stores an events log in its RAM, keeping only the
last 30 records. Events start to register just after making a connection to a device.

To get events without losses, you better to call the `EventLog.refresh()` method periodically depending on the pace
the new events are expected to occur. It requests a device for unread events and stores them in the EventLog object.
There is also a convenience method `EventLog.poll()` that peridically calls `refresh()` and returns new events if any
(or if timeout is reached).

You can make a query to events related to a certain object (reader, door, aux input) or to all events on a device.
Under the hood it just applies a filter to the event log.

```python
zk.events  # Access to event log
zk.events.refresh()  # Get the unread events from a device
zk.events.poll()  # Wait until any event will occur (or timeout will be reached)
zk.door.events  # Event log for all doors (exluding auto open door by time, for instance)
zk.aux_inputs.events  # Event log related to aux inputs only
zk.readers.events  # Event log related to readers only

#
# More complex examples
#
# Wait until a some event will occur on Door 1 reader
zk.door[0].reader.events.poll()
# Wait until unregistered card (event_type==27) with given number will appear on Door 1 reader. Or exit by timeout.
zk.door[0].reader.events.only(card='123456', event_type=27).poll()
# Take all records from log with given card which was occur after 2010-10-11 14:28:04
zk.events.only(card='123456').after_time(datetime(2010, 10, 11, 14, 28, 4))
```

# Parameters

Device parameters are the way to manipulate the device settings. There are two groups of parameters on the device.

The first group is device parameters, which are related to the device itself. They are:

| Name                       | Type                      | Flags      |
|----------------------------|---------------------------|------------|
| serial_number              | str                       | read-only  |
| lock_count                 | int                       | read-only  |
| reader_count               | int                       | read-only  |
| aux_in_count               | int                       | read-only  |
| aux_out_count              | int                       | read-only  |
| communication_password     | str                       |            |
| ip_address                 | str                       |            |
| netmask                    | str                       |            |
| gateway_ip_address         | str                       |            |
| rs232_baud_rate            | int                       |            |
| watchdog_enabled           | bool                      |            |
| door4_to_door2             | bool                      |            |
| backup_hour                | int                       |            |
| reboot                     | bool                      | write-only |
| reader_direction           | str                       |            |
| display_daylight_saving    | bool                      |            |
| enable_daylight_saving     | bool                      |            |
| daylight_saving_mode       | int                       |            |
| fingerprint_version        | int                       | read-only  |
| anti_passback_rule         | int                       |            |
| interlock                  | int                       |            |
| spring_daylight_time_mode1 | DaylightSavingMomentMode1 |            |
| fall_daylight_time_mode1   | DaylightSavingMomentMode1 |            |
| spring_daylight_time_mode2 | DaylightSavingMomentMode2 |            |
| fall_daylight_time_mode2   | DaylightSavingMomentMode2 |            |
| datetime                   | datetime                  |            |

The following code show how to get or set a parameter value, and how to get a description about each one:

```python
from pyzkaccess import ZKAccess

connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
zk = ZKAccess(connstr=connstr)
print(zk.parameters.ip_address)  # Get a value
zk.parameters.ip_address = "192.168.1.2" # Set a value
print(zk.parameters.ip_address.__doc__)  # Get description
```

The second group is door parameters, which are related to the door settings. They are:

| Name                  | Type       | Flags |
|-----------------------|------------|-------|
| duress_password       | str        |       |
| emergency_password    | str        |       |
| lock_on_close         | bool       |       |
| sensor_type           | SensorType |       |
| lock_driver_time      | int        |       |
| magnet_alarm_duration | int        |       |
| verify_mode           | VerifyMode |       |
| multi_card_open       | bool       |       |
| first_card_open       | bool       |       |
| active_time_tz        | int        |       |
| open_time_tz          | int        |       |
| punch_interval        | int        |       |
| cancel_open_day       | int        |       |

The following code show how to get or set a door parameter value, and how to get a description about each one:

```python
from pyzkaccess import ZKAccess

connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
zk = ZKAccess(connstr=connstr)
print(zk.doors[0].parameters.verify_mode)  # Get a parameter value of the first door
zk.doors[0].parameters.verify_mode = 1  # Set a parameter value of the first door
print(zk.doors[0].parameters.verify_mode.__doc__)  # Get a parameter description
```
