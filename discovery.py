#!/bin/python3

"""
Copyright 2021 Luke A.C.A. Rieff

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import enum
import socket
import struct
import time
import select

####
## Global Constants
####

DISCOVERY_PORT = 8084
DISCOVERY_TIMEOUT = 0.5
DISCOVERY_PACKET_COUNT = 2

DISCOVERY_PKT_FLAG_REQUEST = (1 << 0)
DISCOVERY_PKT_FLAG_RESPONSE = (1 << 1)

####
## Enums
####

class DiscoveryPacketDevID (enum.Enum):
    ProjectA = 0x7132

####
## Classes
####

class Discovery:
    """
        Creates new discovery class instance.
        / port: the port to discover on.
        / timeout: how long should we wait for responses?
        / packet_count: number of discover packets.
        / silent: show debug info?
    """
    def __init__ (self, port = DISCOVERY_PORT, timeout = DISCOVERY_TIMEOUT, packet_count = DISCOVERY_PACKET_COUNT, silent = True):
        self._port = port
        self._timeout = timeout
        self._packet_count = packet_count
        self._active = False
        self._silent = silent

        self._socket = None
        self._start = None
        
        self._devices = None

    """
        Sends a discovery packet.
    """
    def _send_discover (self):
        assert (self._active == True)
        assert (self._socket != None)

        # HB: uint16_t, uint8_t
        self._socket.sendto (struct.pack ("HB", DiscoveryPacketDevID.ProjectA.value, DISCOVERY_PKT_FLAG_REQUEST),
            ("<broadcast>", self._port))

    """
        Starts the UDP discovery.
    """
    def start (self):
        assert (self._active == False)
        assert (self._socket == None)

        # Sets active to true to indicate ongoing discovery.
        self._active = True

        # Creates the broadcast socket.
        self._socket = socket.socket (socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt (socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self._socket.setsockopt (socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Tells that we're starting the discovery.
        if not self._silent:
            print (f"Starting UDP discovery on port {self._port} with timeout {self._timeout}")

        # Sends N discovery packets.
        for i in range (0, self._packet_count):
            self._send_discover ()
            if not self._silent:
                print (f"UDP Discovery Packet {i + 1} of {self._packet_count} sent.")

        # Sets the start timestamp.
        self._start = time.time ()
        self._devices = list ()

    """
        Handles the reception of a possible data packet.
        / data: the bytes.
        / addr: the address which sent the data.
    """
    def _on_packet (self, data, addr):
        # HBH: uint16_t, uint8_t, uint16_t
        device_id, flags, port, name_len = struct.unpack ("<HBHH", data[0:7])

        # Makes sure that it's a ProjectA instance, and that we're dealing with an response.
        if device_id != DiscoveryPacketDevID.ProjectA.value:
            return False
        elif not (flags & DISCOVERY_PKT_FLAG_RESPONSE):
            return False

        # Makes sure that we haven't discovered the specified address already.
        for device in self._devices:
            if device[1] == addr[0]:
                return False

        # Reads the device name.
        name = struct.unpack (f"{name_len - 1}s", data[7:(8 + name_len - 2)])
        self._devices.append ((
            name[0].decode ('utf8'), addr[0], port
        ))

        return True

    """
        Performs packet polling, this is so the user can run code while ongoing discovery.
    """
    def poll (self):
        assert (self._active == True)
        assert (self._socket != None)
        assert (self._start != None)

        # Polls if there is new data available from the UDP broadcast socket, if so
        #  we will read it, and attempt to parse the packet.
        read_sockets, _, _ = select.select ([ self._socket ], [], [], 0.01)
        if len (read_sockets) == 1:
            data, addr = read_sockets[0].recvfrom(1024)
            if self._on_packet (data, addr) == True and not self._silent:
                print (f"Discovered ProjectA instance on {addr[0]}")

        # Check if we need to poll another time, if not set the session to non-active.
        if time.time () > self._start + self._timeout:
            if not self._silent:
                print (f"Discovery finished, found {len (self._devices)} devices.")

            self._socket.close ()

            self._socket = None
            self._start = None
            self._active = False

            return False

        return True

    def __del__ (self):
        if self._socket != None:
            self._socket.close ()

####
## Testing Code
####

if __name__ == "__main__":
    discovery = Discovery (DISCOVERY_PORT, DISCOVERY_TIMEOUT, DISCOVERY_PACKET_COUNT, False)
    discovery.start ()

    while discovery.poll ():
        pass

    for device in discovery._devices:
        print (device)
