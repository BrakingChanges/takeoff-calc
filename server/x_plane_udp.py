"""
Class to get dataref values from XPlane Flight Simulator via network.
License: GPLv3
"""

from dataclasses import dataclass
import socket
import struct
import binascii
from time import sleep
import platform


class XPlaneIpNotFound(Exception):
    """Raised when the X-Plane IP is not found"""

    def __init__(self, message="Could not find any running XPlane instance in network."):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"XPlaneIpNotFound: {self.message}"


class XPlaneTimeout(Exception):
    """Raised when there's a timeout to the X-Plane Connection"""

    def __init__(self, message="XPlane timeout."):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"XPlaneTimeout: {self.message}"


class XPlaneVersionNotSupported(Exception):
    """Raised when the X-Plane Version is not supported"""

    def __init__(self, message="XPlane version not supported."):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"XPlaneVersionNotSupported: {self.message}"


@dataclass
class XPlaneBeaconData:
    """Typed class for X-Plane Beacon Data"""
    ip: str
    port: int
    hostname: str
    x_plane_version: int
    role: int


class XPlaneUdp:
    """
    Get data from XPlane via network.
    Use a class to implement RAI Pattern for the UDP socket. 
    """

    # constants
    MCAST_GRP = "239.255.1.1"
    MCAST_PORT = 49707  # (MCAST_PORT was 49000 for XPlane10)

    def __init__(self):
        # Open a UDP Socket to receive on Port 49000
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(3.0)
        # list of requested datarefs with index number
        self.datarefidx = 0
        self.datarefs = {}  # key = idx, value = dataref
        # values from xplane
        self.beacon_data = XPlaneBeaconData("", 0, "", 0, 0)
        self.xplane_values = {}
        self.default_freq = 1

    def __del__(self):
        for _i in range(len(self.datarefs)):
            self.add_data_ref(next(iter(self.datarefs.values())), freq=0)
        self.socket.close()
    
    def execute_command(self, command: str):
        message = struct.pack('<4sx500s', b'CMND', command.encode())
        self.socket.sendto(
            message, (self.beacon_data.ip, self.beacon_data.port))

    def write_data_ref(self, dataref: str, value: float | int | bool):
        """
        Write Dataref to XPlane
        DREF0+(4byte byte value)+dref_path+0+spaces to complete the whole message to 509 bytes
        """
        cmd = b"DREF\x00"
        dataref = dataref+'\x00'
        string = dataref.ljust(500).encode()
        message = "".encode()
        if isinstance(value, float):
            message = struct.pack("<5sf500s", cmd, value, string)
        elif isinstance(value, int):
            message = struct.pack("<5si500s", cmd, value, string)
        elif isinstance(value, bool):
            message = struct.pack("<5sI500s", cmd, int(value), string)

        assert len(message) == 509
        self.socket.sendto(
            message, (self.beacon_data.ip, self.beacon_data.port))

    def add_data_ref(self, dataref, freq: int | None=None):
        '''
        Configure XPlane to send the dataref with a certain frequency.
        You can disable a dataref by setting freq to 0. 
        '''

        idx = -9999

        if freq is None:
            freq = self.default_freq

        if freq == 0:
            if dataref not in self.xplane_values:
                del self.datarefs[idx]
                del self.xplane_values[dataref]

            return

        if dataref not in self.datarefs.values():
            idx = self.datarefidx
            self.datarefs[self.datarefidx] = dataref
            self.datarefidx += 1
        else:
            idx = list(self.datarefs.keys())[
                list(self.datarefs.values()).index(dataref)]

        cmd = b"RREF\x00"
        string = dataref.encode()
        message = struct.pack("<5sii400s", cmd, freq, idx, string)
        assert len(message) == 413
        self.socket.sendto(
            message, (self.beacon_data.ip, self.beacon_data.port))
        if self.datarefidx % 100 == 0:
            sleep(0.2)

    def get_values(self):
        """Get values of a dataref"""
        try:
            # Receive packet
            # maximum bytes of an RREF answer X-Plane will send (Ethernet MTU - IP hdr - UDP hdr)
            data, _addr = self.socket.recvfrom(1472)
            # Decode Packet
            retvalues = {}
            # * Read the Header "RREFO".
            header = data[0:5]
            if header != b"RREF,":  # (was b"RREFO" for XPlane10)
                print("Unknown packet: ", binascii.hexlify(data))
            else:
                # * We get 8 bytes for every dataref sent:
                #   An integer for idx and the float value.
                values = data[5:]
                lenvalue = 8
                numvalues = int(len(values)/lenvalue)
                for i in range(0, numvalues):
                    singledata = data[(5+lenvalue*i):(5+lenvalue*(i+1))]
                    (idx, value) = struct.unpack("<if", singledata)
                    if idx in self.datarefs:
                        # convert -0.0 values to positive 0.0
                        if -0.001 < value < 0:
                            value = 0.0
                        retvalues[self.datarefs[idx]] = value
            self.xplane_values.update(retvalues)
        except Exception as exc:
            raise XPlaneTimeout from exc
        return self.xplane_values

    def find_ip(self):
        '''
        Find the IP of XPlane Host in Network.
        It takes the first one it can find. 
        '''

        self.beacon_data = XPlaneBeaconData("", 0, "", 0, 0)

        # open socket for multicast group.
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if platform.system() == "Windows":
            sock.bind(('', self.MCAST_PORT))
        else:
            sock.bind((self.MCAST_GRP, self.MCAST_PORT))
        mreq = struct.pack("=4sl", socket.inet_aton(
            self.MCAST_GRP), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.settimeout(3.0)

        # receive data
        try:
            packet, sender = sock.recvfrom(1472)
            print("XPlane Beacon: ", packet.hex())

            # decode data
            # * Header
            header = packet[0:5]
            if header != b"BECN\x00":
                print("Unknown packet from "+sender[0])
                print(str(len(packet)) + " bytes")
                print(packet)
                print(binascii.hexlify(packet))

            else:
                # * Data
                data = packet[5:21]
                # struct becn_struct
                # {
                # 	uchar beacon_major_version;		// 1 at the time of X-Plane 10.40
                # 	uchar beacon_minor_version;		// 1 at the time of X-Plane 10.40
                # 	xint application_host_id;			// 1 for X-Plane, 2 for PlaneMaker
                # 	xint version_number;			// 104014 for X-Plane 10.40b14
                # 	uint role;						// 1 for master, 2 for extern visual, 3 for IOS
                # 	ushort port;						// port number X-Plane is listening on
                # 	xchr	computer_name[strDIM];		// the hostname of the computer
                # };
                beacon_major_version = 0
                beacon_minor_version = 0
                application_host_id = 0
                xplane_version_number = 0
                role = 0
                port = 0
                (
                    beacon_major_version,  # 1 at the time of X-Plane 10.40
                    beacon_minor_version,  # 1 at the time of X-Plane 10.40
                    application_host_id,   # 1 for X-Plane, 2 for PlaneMaker
                    xplane_version_number,  # 104014 for X-Plane 10.40b14
                    role,                  # 1 for master, 2 for extern visual, 3 for IOS
                    port,                  # port number X-Plane is listening on
                ) = struct.unpack("<BBiiIH", data)
                hostname = packet[21:-1]  # the hostname of the computer
                hostname = hostname[0:hostname.find(0)]
                if beacon_major_version == 1 \
                        and beacon_minor_version <= 2 \
                        and application_host_id == 1:
                    self.beacon_data.ip = sender[0]
                    self.beacon_data.port = port
                    self.beacon_data.hostname = hostname.decode()
                    self.beacon_data.x_plane_version = xplane_version_number
                    self.beacon_data.role = role
                    print(
                        f"X-Plane Beacon Version: {beacon_major_version}.{
                          beacon_minor_version}.{application_host_id}"
                        )
                else:
                    print(
                        f"X-Plane Beacon Version not supported: {beacon_major_version}.{
                          beacon_minor_version}.{application_host_id}"
                        )
                    raise XPlaneVersionNotSupported()

        except socket.timeout as timeout:
            raise XPlaneIpNotFound() from timeout
        finally:
            sock.close()

        return self.beacon_data
