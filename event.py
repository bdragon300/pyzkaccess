from datetime import datetime


class ZKRealtimeEvent:
    """
    Represents one realtime event occured on the device
    Since the device returns event as string we need to parse it to the structured view. This class does this.
    """
    __slots__ = (
        'time',
        'pin',
        'card',
        'door',
        'event_type',
        'entry_exit',
        'verify_mode'
    )

    def __init__(self, s=None):
        """
        :param s: Optional. Event string to be parsed.
        """
        if s: self.parse(s)

    def parse(self, s):
        """
        Parse one event string and fills out slots
        :param s: event string
        :raises ValueError: event string is invalid
        :return:
        """
        if s == '' or s == '\r\n':
            raise ValueError("Empty event string")

        items = s.split(',')
        if len(items) != 7:
            raise ValueError("Event string has not 7 comma-separated parts")

        items[0] = datetime.strptime(items[0], '%Y-%m-%d %H:%M:%S')
        for i in range(len(self.__slots__)):
            setattr(self, self.__slots__[i], items[i])
