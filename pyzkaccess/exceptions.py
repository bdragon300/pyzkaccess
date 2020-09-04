from .enum import PULL_SDK_ERRORS, WSA_ERROR_CODES


class ZKSDKError(Exception):
    def __init__(self, msg: str, err: int, *args):
        super().__init__((msg, *args))
        self.err = int(err)
        self.msg = msg

    def __str__(self):
        if self.err in PULL_SDK_ERRORS:
            descr = 'SDK error {}: {}'.format(self.err, PULL_SDK_ERRORS[self.err].__doc__)
        elif self.err in WSA_ERROR_CODES:
            descr = 'WINSOCK error {}: {}'.format(self.err, WSA_ERROR_CODES[self.err].__doc__)
        else:
            descr = 'Unknown error {}'.format(self.err)

        return '{}: {}'.format(self.msg, descr)
