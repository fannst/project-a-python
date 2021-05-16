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

import socket
import enum
import time
import struct

####
## Global Constants
####

CONTROL_PORT = 8085
CONTROL_STATUS_INTERVAL = 0.5

CONTROL_PACKET_CONNECT_REQUEST_SIZE = 4 # uint16_t + uint16_t
CONTROL_PACKET_MOTOR_MOVE_TO_SIZE = 10 # uint16_t (2) + uint16_t (2) + uint8_t (1) + uint32_t (4) + bool (1) = 10
CONTROL_PACKET_MOTOR_ENABLE_DISABLE_SIZE = 7 # uint16_t (2) + uint16_t (2) + uint8_t (1) + bool (1) + bool (1) = 6

CONTROL_PACKET_STEPPER_INFO_FLAG_ENABLED = (1 << 0)
CONTROL_PACKET_STEPPER_INFO_FLAG_AUTOMATIC = (1 << 1)
CONTROL_PACKET_STEPPER_INFO_FLAG_MOVING = (1 << 2)

####
## Enums
####

class ControlPkt_OP (enum.Enum):
    ConnectionRequest = 0
    ConnectionRequestApproved = 1
    ConnectionRequestRejected = 2
    StepperInfoRequest = 4
    StepperMoveTo = 5
    StepperEnableDisable = 6
    StepperInfoResponse = 7

####
## Classes
####

class Control:
    """
        Creates new Control class instance.
        \ host: the IPv4 address of the device.
        \ port: the port of the device.
    """
    def __init__ (self, host, port = CONTROL_PORT, silent = True):
        self._host = host
        self._port = port
        self._silent = silent
        
        self._socket = socket.socket (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self._connected = False

        if not self._silent:
            print (f"Socket created for {self._host}:{self._port}")
    
    """
        Attempts to connect the TCP socket
    """
    def tcp_connect (self):
        self._socket.connect ((self._host, self._port))
        self._connected = True

        if not self._silent:
            print (f"Socket connected to {self._host}:{self._port}")
    
    """
        Performs the protocol-layer connection.
    """
    def proto_connect (self):
        self._connect_request ()
        return self._connect_request_res ()

    """
        Gets the connect request response, and either returns true or false.
    """
    def _connect_request_res (self):
        data = self._socket.recv (128);
        length, op = struct.unpack ("<HH", data[:4])

        # Checks the response
        if length != CONTROL_PACKET_CONNECT_REQUEST_SIZE:
            self._reset ()

            if not self._silent:
                print (f"Size must be 4 for {self._host}:{self._port}")

            return False
        elif op == ControlPkt_OP.ConnectionRequestApproved.value:
            if not self._silent:
                print (f"Connection approved for {self._host}:{self._port}")
            
            return True
        elif op == ControlPkt_OP.ConnectionRequestRejected.value:
            self._reset ()

            if not self._silent:
                print (f"Connection rejected for {self._host}:{self._port}")

            return False
        else:
            self._reset ()

            if not self._silent:
                print (f"Invalid opcode {op} for {self._host}:{self._port}")

            return False
    
    """
        Sends the protocol layer connect request.
    """
    def _connect_request (self):
        assert (self._socket != None)
        assert (self._connected == True)
        self._socket.send (struct.pack ("<HH", CONTROL_PACKET_CONNECT_REQUEST_SIZE, ControlPkt_OP.ConnectionRequest.value))
    
    """
        Moves the stepper to the specified position.
    """
    def send_stepper_move_to (self, stepper, pos):
        assert (self._socket != None)
        assert (self._connected == True)
        self._socket.send(struct.pack ("<HHBi?", CONTROL_PACKET_MOTOR_MOVE_TO_SIZE, ControlPkt_OP.StepperMoveTo.value, stepper, pos, False))

    """
        Enables / Disables specified stepper.
    """
    def stepper_enable_disable (self, stepper, enabled):
        assert (self._socket != None)
        assert (self._connected == True)
        self._socket.send(struct.pack ("<HHB??", CONTROL_PACKET_MOTOR_ENABLE_DISABLE_SIZE, ControlPkt_OP.StepperEnableDisable.value, stepper, enabled, False))

    def get_stepper_info (self):
        assert (self._socket != None)
        assert (self._connected == True)
        self._socket.send (struct.pack ("<HH", CONTROL_PACKET_CONNECT_REQUEST_SIZE, ControlPkt_OP.StepperInfoRequest.value))

        # Reads the data and unpacks it.
        data = self._socket.recv (1024)
        _, op = struct.unpack ("<HH", data[:4])

        # Makes sure that it's an stepper info response.
        if op != ControlPkt_OP.StepperInfoResponse.value:
            return None
        
        # Starts unpacking the motor data
        result = []
        start = 4
        while True:
            motor, flags, target_pos, current_pos, min_speed, current_speed, target_speed, has_next = struct.unpack("<BBiiHHH?", data[start:start + 17])

            result.append ({
                "motor": motor,
                "flags": flags,
                "target_pos": target_pos,
                "current_pos": current_pos,
                "min_speed": min_speed,
                "current_speed": current_speed,
                "max_speed": target_speed
            })

            if not has_next:
                break
            else:
                start = start + 17

        # Returns the result.
        return result


    """
        Resets the control class, by disconnecting the socket.
    """
    def _reset (self):
        assert (self._socket != None)
        assert (self._connected == True)
        
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close ()
        self._socket = None
        self._connected = False

    """
        Makes sure the fd gets closed.
    """
    def __del__ (self):
        if self._socket != None:
            self._socket.close ()