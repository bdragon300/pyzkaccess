__all__ = [
    'ControlOperation',
    'RelayGroup',
    'SensorType',
    'VerifyMode',
    'PassageDirection',
    'EVENT_TYPES',
    'PULL_SDK_ERRORS',
    'WSA_ERROR_CODES'
]
from enum import Enum
from .common import DocDict


class ControlOperation(Enum):
    """Device control operation. See `ControlOperation` SDK func docs"""
    output = 1
    cancel_alarm = 2
    restart = 3


class RelayGroup(Enum):
    """Device relay group.
    There are either lock relays (door output) or aux relays
    (aux output)
    """
    lock = 1
    aux = 2


class SensorType(Enum):
    """Sensor type of door. See DoorXSensorType parameter in SDK docs"""
    not_available = 0
    normal_open = 1
    normal_closed = 2


class VerifyMode(Enum):
    """Which methods are used to authenticate user.
    See `DoorXVerifyType` parameter in SDK docs
    """
    not_available = 0
    only_finger = 1
    only_password = 3
    only_card = 4
    card_or_finger = 6
    card_and_finger = 10
    card_and_password = 11
    others = 200


class PassageDirection(Enum):
    """Whether a user was entered or exited via door
    See event format description in SDK docs
    """
    entry = 0
    exit = 1
    none = 2


#: Type of event which is returned by GetRTLog function
#: See event format description in SDK docs
EVENT_TYPES = DocDict({
    0: 'Normal Punch Open',
    1: 'Punch during Normal Open Time Zone',
    2: 'First Card Normal Open (Punch Card)',
    3: 'Multi-Card Open (Punching Card)',
    4: 'Emergency Password Open',
    5: 'Open during Normal Open Time Zone',
    6: 'Linkage Event Triggered',
    7: 'Cancel Alarm',
    8: 'Remote Opening',
    9: 'Remote Closing',
    10: 'Disable Intraday Normal Open Time Zone',
    11: 'Enable Intraday Normal Open Time Zone',
    12: 'Open Auxiliary Output',
    13: 'Close Auxiliary Output',
    14: 'Press Fingerprint Open',
    15: 'Multi-Card Open (Press Fingerprint)',
    16: 'Press Fingerprint during Normal Open Time Zone',
    17: 'Card plus Fingerprint Open',
    18: 'First Card Normal Open (Press Fingerprint)',
    19: 'First Card Normal Open (Card plus Fingerprint)',
    20: 'Too Short Punch Interval',
    21: 'Door Inactive Time Zone (Punch Card)',
    22: 'Illegal Time Zone',
    23: 'Access Denied',
    24: 'Anti-Passback',
    25: 'Interlock',
    26: 'Multi-Card Authentication (Punching Card)',
    27: 'Unregistered Card',
    28: 'Opening Timeout',
    29: 'Card Expired',
    30: 'Password Error',
    31: 'Too Short Fingerprint Pressing Interval',
    32: 'Multi-Card Authentication (Press Fingerprint)',
    33: 'Fingerprint Expired',
    34: 'Unregistered Fingerprint',
    35: 'Door Inactive Time Zone (Press Fingerprint)',
    36: 'Door Inactive Time Zone (Exit Button)',
    37: 'Failed to Close during Normal Open Time Zone',
    101: 'Duress Password Open',
    102: 'Opened Accidentally',
    103: 'Duress Fingerprint Open',
    200: 'Door Opened Correctly',
    201: 'Door Closed Correctly',
    202: 'Exit button Open',
    203: 'Multi-Card Open (Card plus Fingerprint)',
    204: 'Normal Open Time Zone Over',
    205: 'Remote Normal Opening',
    220: 'Auxiliary Input Disconnected',
    221: 'Auxiliary Input Shorted',
    255: 'Actually that obtain door status and alarm status',
})


#: Errors which SDK functions may return. See errors description in SDK
PULL_SDK_ERRORS = DocDict({
    -1: 'The command is not sent successfully',
    -2: 'The command has no response',
    -3: 'The buffer is not enough',
    -4: 'The decompression fails',
    -5: 'The length of the read data is not correct',
    -6: 'The length of the decompressed data is not consistent with the expected length',
    -7: 'The command is repeated',
    -8: 'The connection is not authorized',
    -9: 'Data error: The CRC result is failure',
    -10: 'Data error: PullSDK cannot resolve the data',
    -11: 'Data parameter error',
    -12: 'The command is not executed correctly',
    -13: 'Command error: This command is not available',
    -14: 'The communication password is not correct',
    -15: 'Fail to write the file',
    -16: 'Fail to read the file',
    -17: 'The file does not exist',
    -99: 'Unknown error',
    -100: 'The table structure does not exist',
    -101: 'In the table structure, the Condition field does not exit',
    -102: 'The total number of fields is not consistent',
    -103: 'The sequence of fields is not consistent',
    -104: 'Real-time event data error',
    -105: 'Data errors occur during data resolution.',
    -106: 'Data overflow: The delivered data is more than 4 MB in length',
    -107: 'Fail to get the table structure',
    -108: 'Invalid options',
    -201: 'LoadLibrary failure',
    -202: 'Fail to invoke the interface',
    -203: 'Communication initialization fails',
    -206: 'Start of a serial interface agent program fails and the cause generally relies in '
          'inexistence or occupation of the serial interface.',
    -301: 'Requested TCP/IP version error',
    -302: 'Incorrect version number',
    -303: 'Fail to get the protocol type',
    -304: 'Invalid SOCKET',
    -305: 'SOCKET error',
    -306: 'HOST error',
    -307: 'Connection attempt failed',
})

#: SDK functions can also return WINSOCK errors using `PullLastError`
#: function. See SDK docs and MSDN
WSA_ERROR_CODES = DocDict({
    6: "WSA_INVALID_HANDLE (Specified event object handle is invalid. An application attempts to "
       "use an event object, but the specified handle is not valid)",
    8: "WSA_NOT_ENOUGH_MEMORY (Insufficient memory available. An application used a Windows "
       "Sockets function that directly maps to a Windows function. The Windows function is "
       "indicating a lack of required memory resources)",
    87: "WSA_INVALID_PARAMETER (One or more parameters are invalid. An application used a Windows "
        "Sockets function which directly maps to a Windows function. The Windows function is "
        "indicating a problem with one or more parameters)",
    995: "WSA_OPERATION_ABORTED (Overlapped operation aborted. An overlapped operation was "
         "canceled due to the closure of the socket, or the execution of the SIO_FLUSH command "
         "in WSAIoctl)",
    996: "WSA_IO_INCOMPLETE (Overlapped I/O event object not in signaled state. The application "
         "has tried to determine the status of an overlapped operation which is not yet completed. "
         "Applications that use WSAGetOverlappedResult (with the fWait flag set to FALSE) in a "
         "polling mode to determine when an overlapped operation has completed, get this error "
         "code until the operation is complete)",
    997: "WSA_IO_PENDING (Overlapped operations will complete later.  The application has "
         "initiated an overlapped operation that cannot be completed immediately. A completion "
         "indication will be given later when the operation has been completed)",
    10004: "WSAEINTR (Interrupted function call. A blocking operation was interrupted by a call "
           "to WSACancelBlockingCall)",
    10009: "WSAEBADF (File handle is not valid. The file handle supplied is not valid)",
    10013: "WSAEACCES (Permission denied. An attempt was made to access a socket in a way "
           "forbidden by its access permissions. An example is using a broadcast address for "
           "sendto without broadcast permission being set using setsockopt(SO_BROADCAST). "
           "Another possible reason for the WSAEACCES error is that when the bind function "
           "is called (on Windows NT 4.0 with SP4 and later), another application, service, "
           "or kernel mode driver is bound to the same address with exclusive access. Such "
           "exclusive access is a new feature of Windows NT 4.0 with SP4 and later, and is "
           "implemented by using the SO_EXCLUSIVEADDRUSE option)",
    10014: "WSAEFAULT (Bad address. The system detected an invalid pointer address in "
           "attempting to use a pointer argument of a call. This error occurs if an application "
           "passes an invalid pointer value, or if the length of the buffer is too small. "
           "For instance, if the length of an argument, which is a sockaddr structure, is "
           "smaller than the sizeof(sockaddr))",
    10022: "WSAEINVAL (Invalid argument. Some invalid argument was supplied (for example, "
           "specifying an invalid level to the setsockopt function). In some instances, it "
           "also refers to the current state of the socket—for instance, calling accept on "
           "a socket that is not listening)",
    10024: "WSAEMFILE (Too many open files. Too many open sockets. Each implementation may "
           "have a maximum number of socket handles available, either globally, per process, "
           "or per thread)",
    10035: "WSAEWOULDBLOCK (Resource temporarily unavailable. This error is returned from "
           "operations on nonblocking sockets that cannot be completed immediately, for "
           "example recv when no data is queued to be read from the socket. It is a nonfatal "
           "error, and the operation should be retried later. It is normal for WSAEWOULDBLOCK "
           "to be reported as the result from calling connect on a nonblocking SOCK_STREAM "
           "socket, since some time must elapse for the connection to be established)",
    10036: "WSAEINPROGRESS (Operation now in progress. A blocking operation is currently "
           "executing. Windows Sockets only allows a single blocking operation—per- task or "
           "thread—to be outstanding, and if any other function call is made (whether or "
           "not it references that or any other socket) the function fails with the "
           "WSAEINPROGRESS error)",
    10037: "WSAEALREADY (Operation already in progress. An operation was attempted on a "
           "nonblocking socket with an operation already in progress—that is, calling connect "
           "a second time on a nonblocking socket that is already connecting, or canceling "
           "an asynchronous request (WSAAsyncGetXbyY) that has already been canceled or "
           "completed)",
    10038: "WSAENOTSOCK (Socket operation on nonsocket. An operation was attempted on "
           "something that is not a socket. Either the socket handle parameter did not "
           "reference a valid socket, or for select, a member of an fd_set was not valid)",
    10039: "WSAEDESTADDRREQ (Destination address required. A required address was omitted "
           "from an operation on a socket. For example, this error is returned if sendto "
           "is called with the remote address of ADDR_ANY)",
    10040: "WSAEMSGSIZE (Message too long. A message sent on a datagram socket was larger "
           "than the internal message buffer or some other network limit, or the buffer used "
           "to receive a datagram was smaller than the datagram itself)",
    10041: "WSAEPROTOTYPE (Protocol wrong type for socket. A protocol was specified in the "
           "socket function call that does not support the semantics of the socket type "
           "requested. For example, the ARPA Internet UDP protocol cannot be specified with "
           "a socket type of SOCK_STREAM)",
    10042: "WSAENOPROTOOPT (Bad protocol option. An unknown, invalid or unsupported option "
           "or level was specified in a getsockopt or setsockopt call)",
    10043: "WSAEPROTONOSUPPORT (Protocol not supported. The requested protocol has not been "
           "configured into the system, or no implementation for it exists. For example, a "
           "socket call requests a SOCK_DGRAM socket, but specifies a stream protocol)",
    10044: "WSAESOCKTNOSUPPORT (Socket type not supported. The support for the specified "
           "socket type does not exist in this address family. For example, the optional "
           "type SOCK_RAW might be selected in a socket call, and the implementation does "
           "not support SOCK_RAW sockets at all)",
    10045: "WSAEOPNOTSUPP (Operation not supported. The attempted operation is not supported "
           "for the type of object referenced. Usually this occurs when a socket descriptor "
           "to a socket that cannot support this operation is trying to accept a connection "
           "on a datagram socket)",
    10046: "WSAEPFNOSUPPORT (Protocol family not supported. The protocol family has not been "
           "configured into the system or no implementation for it exists. This message has "
           "a slightly different meaning from WSAEAFNOSUPPORT. However, it is interchangeable "
           "in most cases, and all Windows Sockets functions that return one of these messages "
           "also specify WSAEAFNOSUPPORT)",
    10047: "WSAEAFNOSUPPORT (Address family not supported by protocol family. An address "
           "incompatible with the requested protocol was used. All sockets are created with "
           "an associated address family (that is, AF_INET for Internet Protocols) and a "
           "generic protocol type (that is, SOCK_STREAM). This error is returned if an "
           "incorrect protocol is explicitly requested in the socket call, or if an address "
           "of the wrong family is used for a socket, for example, in sendto)",
    10048: "WSAEADDRINUSE (Address already in use. Typically, only one usage of each socket "
           "address (protocol/IP address/port) is permitted. This error occurs if an "
           "application attempts to bind a socket to an IP address/port that has already "
           "been used for an existing socket, or a socket that was not closed properly, or "
           "one that is still in the process of closing. For server applications that need "
           "to bind multiple sockets to the same port number, consider using setsockopt "
           "(SO_REUSEADDR). Client applications usually need not call bind at all—connect "
           "chooses an unused port automatically. When bind is called with a wildcard address "
           "(involving ADDR_ANY), a WSAEADDRINUSE error could be delayed until the specific "
           "address is committed. This could happen with a call to another function later, "
           "including connect, listen, WSAConnect, or WSAJoinLeaf)",
    10049: "WSAEADDRNOTAVAIL (Cannot assign requested address. The requested address is not "
           "valid in its context. This normally results from an attempt to bind to an address "
           "that is not valid for the local computer. This can also result from connect, "
           "sendto, WSAConnect, WSAJoinLeaf, or WSASendTo when the remote address or port "
           "is not valid for a remote computer (for example, address or port 0))",
    10050: "WSAENETDOWN (Network is down. A socket operation encountered a dead network. "
           "This could indicate a serious failure of the network system (that is, the "
           "protocol stack that the Windows Sockets DLL runs over), the network interface, "
           "or the local network itself)",
    10051: "WSAENETUNREACH (Network is unreachable. A socket operation was attempted to "
           "an unreachable network. This usually means the local software knows no route "
           "to reach the remote host)",
    10052: "WSAENETRESET (Network dropped connection on reset. The connection has been "
           "broken due to keep-alive activity detecting a failure while the operation was "
           "in progress. It can also be returned by setsockopt if an attempt is made to set "
           "SO_KEEPALIVE on a connection that has already failed)",
    10053: "WSAECONNABORTED (Software caused connection abort. An established connection was "
           "aborted by the software in your host computer, possibly due to a data transmission "
           "time-out or protocol error)",
    10054: "WSAECONNRESET (Connection reset by peer. An existing connection was forcibly "
           "closed by the remote host. This normally results if the peer application on the "
           "remote host is suddenly stopped, the host is rebooted, the host or remote network "
           "interface is disabled, or the remote host uses a hard close (see setsockopt for "
           "more information on the SO_LINGER option on the remote socket). This error may "
           "also result if a connection was broken due to keep-alive activity detecting a "
           "failure while one or more operations are in progress. Operations that were in "
           "progress fail with WSAENETRESET. Subsequent operations fail with WSAECONNRESET)",
    10055: "WSAENOBUFS (No buffer space available. An operation on a socket could not be "
           "performed because the system lacked sufficient buffer space or because a queue "
           "was full)",
    10056: "WSAEISCONN (Socket is already connected. A connect request was made on an "
           "already-connected socket. Some implementations also return this error if "
           "sendto is called on a connected SOCK_DGRAM socket (for SOCK_STREAM sockets, the "
           "to parameter in sendto is ignored) although other implementations treat this as "
           "a legal occurrence)",
    10057: "WSAENOTCONN (Socket is not connected. A request to send or receive data was "
           "disallowed because the socket is not connected and (when sending on a datagram "
           "socket using sendto) no address was supplied. Any other type of operation might "
           "also return this error—for example, setsockopt setting SO_KEEPALIVE if the "
           "connection has been reset)",
    10058: "WSAESHUTDOWN (Cannot send after socket shutdown. A request to send or receive "
           "data was disallowed because the socket had already been shut down in that "
           "direction with a previous shutdown call. By calling shutdown a partial close "
           "of a socket is requested, which is a signal that sending or receiving, or both "
           "have been discontinued)",
    10059: "WSAETOOMANYREFS (Too many references. Too many references to some kernel object)",
    10060: "WSAETIMEDOUT (Connection timed out. A connection attempt failed because the "
           "connected party did not properly respond after a period of time, or the "
           "established connection failed because the connected host has failed to respond)",
    10061: "WSAECONNREFUSED (Connection refused. No connection could be made because the "
           "target computer actively refused it. This usually results from trying to "
           "connect to a service that is inactive on the foreign host—that is, one with "
           "no server application running)",
    10062: "WSAELOOP (Cannot translate name. Cannot translate a name)",
    10063: "WSAENAMETOOLONG (Name too long. A name component or a name was too long)",
    10064: "WSAEHOSTDOWN (Host is down. A socket operation failed because the destination "
           "host is down. A socket operation encountered a dead host. Networking activity "
           "on the local host has not been initiated. These conditions are more likely to be "
           "indicated by the error WSAETIMEDOUT)",
    10065: "WSAEHOSTUNREACH (No route to host. A socket operation was attempted to an "
           "unreachable host. See WSAENETUNREACH)",
    10066: "WSAENOTEMPTY (Directory not empty. Cannot remove a directory that is not empty)",
    10067: "WSAEPROCLIM (Too many processes. A Windows Sockets implementation may have a "
           "limit on the number of applications that can use it simultaneously. WSAStartup "
           "may fail with this error if the limit has been reached)",
    10068: "WSAEUSERS (User quota exceeded. Ran out of user quota)",
    10069: "WSAEDQUOT (Disk quota exceeded. Ran out of disk quota)",
    10070: "WSAESTALE (Stale file handle reference. The file handle reference is no longer "
           "available)",
    10071: "WSAEREMOTE (Item is remote. The item is not available locally)",
    10091: "WSASYSNOTREADY (Network subsystem is unavailable. This error is returned by "
           "WSAStartup if the Windows Sockets implementation cannot function at this time "
           "because the underlying system it uses to provide network services is currently "
           "unavailable. Users should check: That the appropriate Windows Sockets DLL file "
           "is in the current path. That they are not trying to use more than one Windows "
           "Sockets implementation simultaneously. If there is more than one Winsock DLL on "
           "your system, be sure the first one in the path is appropriate for the network "
           "subsystem currently loaded. The Windows Sockets implementation documentation to "
           "be sure all necessary components are currently installed and configured correctly)",
    10092: "WSAVERNOTSUPPORTED (Winsock.dll version out of range. The current Windows Sockets "
           "implementation does not support the Windows Sockets specification version "
           "requested by the application. Check that no old Windows Sockets DLL files are "
           "being accessed)",
    10093: "WSANOTINITIALISED (Successful WSAStartup not yet performed. Either the application "
           "has not called WSAStartup or WSAStartup failed. The application may be accessing "
           "a socket that the current active task does not own (that is, trying to share a "
           "socket between tasks), or WSACleanup has been called too many times)",
    10101: "WSAEDISCON (Graceful shutdown in progress. Returned by WSARecv and WSARecvFrom "
           "to indicate that the remote party has initiated a graceful shutdown sequence)",
    10102: "WSAENOMORE (No more results. No more results can be returned by the "
           "WSALookupServiceNext function)",
    10103: "WSAECANCELLED (Call has been canceled. A call to the WSALookupServiceEnd function "
           "was made while this call was still processing. The call has been canceled)",
    10104: "WSAEINVALIDPROCTABLE (Procedure call table is invalid. The service provider "
           "procedure call table is invalid. A service provider returned a bogus procedure "
           "table to Ws2_32.dll. This is usually caused by one or more of the function "
           "pointers being NULL)",
    10105: "WSAEINVALIDPROVIDER (Service provider is invalid. The requested service provider "
           "is invalid. This error is returned by the WSCGetProviderInfo and "
           "WSCGetProviderInfo32 functions if the protocol entry specified could not be found. "
           "This error is also returned if the service provider returned a version number "
           "other than 2.0)",
    10106: "WSAEPROVIDERFAILEDINIT (Service provider failed to initialize. The requested "
           "service provider could not be loaded or initialized. This error is returned if "
           "either a service provider's DLL could not be loaded (LoadLibrary failed) or the "
           "provider's WSPStartup or NSPStartup function failed)",
    10107: "WSASYSCALLFAILURE (System call failure. A system call that should never fail has "
           "failed. This is a generic error code, returned under various conditions. Returned "
           "when a system call that should never fail does fail. For example, if a call to "
           "WaitForMultipleEvents fails or one of the registry functions fails trying to "
           "manipulate the protocol/namespace catalogs. Returned when a provider does not "
           "return SUCCESS and does not provide an extended error code. Can indicate a "
           "service provider implementation error)",
    10108: "WSASERVICE_NOT_FOUND (Service not found. No such service is known. The service "
           "cannot be found in the specified name space)",
    10109: "WSATYPE_NOT_FOUND (Class type not found. The specified class was not found)",
    10110: "WSA_E_NO_MORE (No more results. No more results can be returned by the "
           "WSALookupServiceNext function)",
    10111: "WSA_E_CANCELLED (Call was canceled. A call to the WSALookupServiceEnd function "
           "was made while this call was still processing. The call has been canceled)",
    10112: "WSAEREFUSED (Database query was refused. A database query failed because it "
           "was actively refused)",
    11001: "WSAHOST_NOT_FOUND (Host not found. No such host is known. The name is not an "
           "official host name or alias, or it cannot be found in the database(s) being "
           "queried. This error may also be returned for protocol and service queries, and "
           "means that the specified name could not be found in the relevant database)",
    11002: "WSATRY_AGAIN (Nonauthoritative host not found. This is usually a temporary error "
           "during host name resolution and means that the local server did not receive a "
           "response from an authoritative server. A retry at some time later may be successful)",
    11003: "WSANO_RECOVERY (This is a nonrecoverable error. This indicates that some sort "
           "of nonrecoverable error occurred during a database lookup. This may be because "
           "the database files (for example, BSD-compatible HOSTS, SERVICES, or PROTOCOLS "
           "files) could not be found, or a DNS request was returned by the server with a "
           "severe error)",
    11004: "WSANO_DATA (Valid name, no data record of requested type. The requested name is "
           "valid and was found in the database, but it does not have the correct associated "
           "data being resolved for. The usual example for this is a host name-to-address "
           "translation attempt (using gethostbyname or WSAAsyncGetHostByName) which uses "
           "the DNS (Domain Name Server). An MX record is returned but no A record—indicating "
           "the host itself exists, but is not directly reachable)",
    11005: "WSA_QOS_RECEIVERS (QoS receivers. At least one QoS reserve has arrived)",
    11006: "WSA_QOS_SENDERS (QoS senders. At least one QoS send path has arrived)",
    11007: "WSA_QOS_NO_SENDERS (No QoS senders. There are no QoS senders)",
    11008: "WSA_QOS_NO_RECEIVERS (QoS no receivers. There are no QoS receivers)",
    11009: "WSA_QOS_REQUEST_CONFIRMED (QoS request confirmed. The QoS reserve request has "
           "been confirmed)",
    11010: "WSA_QOS_ADMISSION_FAILURE (QoS admission error. A QoS error occurred due to lack "
           "of resources)",
    11011: "WSA_QOS_POLICY_FAILURE (QoS policy failure. The QoS request was rejected because "
           "the policy system couldn't allocate the requested resource within the existing "
           "policy)",
    11012: "WSA_QOS_BAD_STYLE (QoS bad style. An unknown or conflicting QoS style was "
           "encountered)",
    11013: "WSA_QOS_BAD_OBJECT (QoS bad object. A problem was encountered with some part "
           "of the filterspec or the provider-specific buffer in general)",
    11014: "WSA_QOS_TRAFFIC_CTRL_ERROR (QoS traffic control error. An error with the "
           "underlying traffic control (TC) API as the generic QoS request was converted "
           "for local enforcement by the TC API. This could be due to an out of memory "
           "error or to an internal QoS provider error)",
    11015: "WSA_QOS_GENERIC_ERROR (QoS generic error. A general QoS error)",
    11016: "WSA_QOS_ESERVICETYPE (QoS service type error. An invalid or unrecognized service "
           "type was found in the QoS flowspec)",
    11017: "WSA_QOS_EFLOWSPEC (QoS flowspec error. An invalid or inconsistent flowspec was "
           "found in the QOS structure)",
    11018: "WSA_QOS_EPROVSPECBUF (Invalid QoS provider buffer. An invalid QoS provider-specific "
           "buffer)",
    11019: "WSA_QOS_EFILTERSTYLE (Invalid QoS filter style. An invalid QoS filter style was used)",
    11020: "WSA_QOS_EFILTERTYPE (Invalid QoS filter type. An invalid QoS filter type was used)",
    11021: "WSA_QOS_EFILTERCOUNT (Incorrect QoS filter count. An incorrect number of QoS "
           "FILTERSPECs were specified in the FLOWDESCRIPTOR)",
    11022: "WSA_QOS_EOBJLENGTH (Invalid QoS object length. An object with an invalid "
           "ObjectLength field was specified in the QoS provider-specific buffer)",
    11023: "WSA_QOS_EFLOWCOUNT (Incorrect QoS flow count. An incorrect number of flow "
           "descriptors was specified in the QoS structure)",
    11024: "WSA_QOS_EUNKOWNPSOBJ (Unrecognized QoS object. An unrecognized object was found "
           "in the QoS provider-specific buffer)",
    11025: "WSA_QOS_EPOLICYOBJ (Invalid QoS policy object. An invalid policy object was found "
           "in the QoS provider-specific buffer)",
    11026: "WSA_QOS_EFLOWDESC (Invalid QoS flow descriptor. An invalid QoS flow descriptor was "
           "found in the flow descriptor list)",
    11027: "WSA_QOS_EPSFLOWSPEC (Invalid QoS provider-specific flowspec. An invalid or "
           "inconsistent flowspec was found in the QoS provider-specific buffer)",
    11028: "WSA_QOS_EPSFILTERSPEC (Invalid QoS provider-specific filterspec. An invalid "
           "FILTERSPEC was found in the QoS provider-specific buffer)",
    11029: "WSA_QOS_ESDMODEOBJ (Invalid QoS shape discard mode object. An invalid shape discard "
           "mode object was found in the QoS provider-specific buffer)",
    11030: "WSA_QOS_ESHAPERATEOBJ (Invalid QoS shaping rate object. An invalid shaping rate "
           "object was found in the QoS provider-specific buffer)",
    11031: "WSA_QOS_RESERVED_PETYPE (Reserved policy QoS element type. A reserved policy "
           "element was found in the QoS provider-specific buffer)",
})
