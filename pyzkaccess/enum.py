from enum import Enum


class ControlOperation(Enum):
    """
    Type of device control operation. See PULL SDK docs
    """
    output = 1
    cancel_alarm = 2
    restart = 3


class RelayGroup(Enum):
    """
    Device relay group. See PULL SDK docs
    """
    lock = 1
    aux = 2


VERIFY_MODES = {
    '1':   'Only finger',
    '3':   'Only password',
    '4':   'Only card',
    '11':  'Card and password',
    '200': 'Others'
}

EVENT_TYPES = {
    '0':   'Normal Punch Open',
    '1':   'Punch during Normal Open Time Zone',
    '2':   'First Card Normal Open (Punch Card)',
    '3':   'Multi-Card Open (Punching Card)',
    '4':   'Emergency Password Open',
    '5':   'Open during Normal Open Time Zone',
    '6':   'Linkage Event Triggered',
    '7':   'Cancel Alarm',
    '8':   'Remote Opening',
    '9':   'Remote Closing',
    '10':  'Disable Intraday Normal Open Time Zone',
    '11':  'Enable Intraday Normal Open Time Zone',
    '12':  'Open Auxiliary Output',
    '13':  'Close Auxiliary Output',
    '14':  'Press Fingerprint Open',
    '15':  'Multi-Card Open (Press Fingerprint)',
    '16':  'Press Fingerprint during Normal Open Time Zone',
    '17':  'Card plus Fingerprint Open',
    '18':  'First Card Normal Open (Press Fingerprint)',
    '19':  'First Card Normal Open (Card plus Fingerprint)',
    '20':  'Too Short Punch Interval',
    '21':  'Door Inactive Time Zone (Punch Card)',
    '22':  'Illegal Time Zone',
    '23':  'Access Denied',
    '24':  'Anti-Passback',
    '25':  'Interlock',
    '26':  'Multi-Card Authentication (Punching Card)',
    '27':  'Unregistered Card',
    '28':  'Opening Timeout',
    '29':  'Card Expired',
    '30':  'Password Error',
    '31':  'Too Short Fingerprint Pressing Interval',
    '32':  'Multi-Card Authentication (Press Fingerprint)',
    '33':  'Fingerprint Expired',
    '34':  'Unregistered Fingerprint',
    '35':  'Door Inactive Time Zone (Press Fingerprint)',
    '36':  'Door Inactive Time Zone (Exit Button)',
    '37':  'Failed to Close during Normal Open Time Zone',
    '101': 'Duress Password Open',
    '102': 'Opened Accidentally',
    '103': 'Duress Fingerprint Open',
    '200': 'Door Opened Correctly',
    '201': 'Door Closed Correctly',
    '202': 'Exit button Open',
    '203': 'Multi-Card Open (Card plus Fingerprint)',
    '204': 'Normal Open Time Zone Over',
    '205': 'Remote Normal Opening',
    '220': 'Auxiliary Input Disconnected',
    '221': 'Auxiliary Input Shorted',
    '255': 'Actually that obtain door status and alarm status',
}

ENTRY_EXIT_TYPES = {
    '0': 'Entry',
    '1': 'Exit',
    '2': 'None'
}
