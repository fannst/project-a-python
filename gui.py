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

from discovery import DISCOVERY_PORT, Discovery, DISCOVERY_PACKET_COUNT
from control import CONTROL_PORT, Control, CONTROL_PACKET_STEPPER_INFO_FLAG_AUTOMATIC, CONTROL_PACKET_STEPPER_INFO_FLAG_ENABLED, CONTROL_PACKET_STEPPER_INFO_FLAG_MOVING
import gi
import os

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

####
## Classes
####

DISCOVERY_WINDOW_TITLE = "Project-A Device Explorer"
DISCOVERY_WINDOW_SIZE = (500, 400)
DISCOVERY_WINDOW_TIMEOUT = 0.5

class DiscoveryWindow (Gtk.Window):
    """
        Creates an new discovery window instance.
    """
    def __init__ (self):
        Gtk.Window.__init__ (self, title = DISCOVERY_WINDOW_TITLE)

        self.resize (DISCOVERY_WINDOW_SIZE[0], DISCOVERY_WINDOW_SIZE[1])

        self._main_box = Gtk.Box (orientation=Gtk.Orientation.VERTICAL)

        # Widgets for: self._main_box

        self._top_box = Gtk.Box (orientation=Gtk.Orientation.HORIZONTAL, margin = 5)
        self._scroll_box = Gtk.Box (orientation=Gtk.Orientation.VERTICAL)
        self._bottom_box = Gtk.Box (orientation=Gtk.Orientation.HORIZONTAL, margin = 10)

        self._main_box.add (self._top_box)
        self._main_box.add (Gtk.Separator (orientation = Gtk.Orientation.HORIZONTAL))
        self._main_box.add (self._scroll_box)
        self._main_box.pack_end (self._bottom_box, False, True, 0)
        self._main_box.pack_end (Gtk.Separator (orientation = Gtk.Orientation.HORIZONTAL), False, True, 0)

        # Widgets for: self._top_box

        self._top_box.add (Gtk.Label (label = "Packet count: ", margin_right = 10))

        self._top_box_pkt_cnt_adjustment = Gtk.Adjustment (upper = 40, lower = 1, step_increment = 1, page_increment = 10, value = DISCOVERY_PACKET_COUNT)
        self._top_box_pkt_cnt_spin_button = Gtk.SpinButton ()
        self._top_box_pkt_cnt_spin_button.set_adjustment (self._top_box_pkt_cnt_adjustment)
        self._top_box.add (self._top_box_pkt_cnt_spin_button)

        self._top_box.add (Gtk.Separator (orientation = Gtk.Orientation.VERTICAL, margin_left = 10, margin_right = 10))

        self._top_box.add (Gtk.Label (label = "Port: ", margin_right = 10))

        self._top_box_port_entry = Gtk.Entry ()
        self._top_box_port_entry.set_text (str (DISCOVERY_PORT))
        self._top_box.add (self._top_box_port_entry)

        self._top_box.add (Gtk.Separator (orientation = Gtk.Orientation.VERTICAL, margin_left = 10, margin_right = 10))

        self._top_box_refresh_button = Gtk.Button.new_with_label ("Perform Discovery")
        self._top_box_refresh_button.connect ("pressed", self._on_discovery_start_pressed)
        self._top_box.add (self._top_box_refresh_button)

        # Widgets for: self._scroll_box

        self._scroll_box_discovered_list_store = Gtk.ListStore (str, str, str)
        self._scroll_box_discovered_list_store.append ([ "Press Discover Button", "0.0.0.0", "0" ])

        self._scroll_box_discovered_tree_view = Gtk.TreeView (model = self._scroll_box_discovered_list_store)
        self._scroll_box_discovered_tree_view.connect ("row-activated", self._on_connect_press)
        self._scroll_box_discovered_tree_view.append_column (Gtk.TreeViewColumn ("Name", Gtk.CellRendererText (), text = 0))
        self._scroll_box_discovered_tree_view.append_column (Gtk.TreeViewColumn ("IP Address", Gtk.CellRendererText (), text = 1))
        self._scroll_box_discovered_tree_view.append_column (Gtk.TreeViewColumn ("Port", Gtk.CellRendererText (), text = 2))

        self._scroll_box.add (self._scroll_box_discovered_tree_view)

        # Widgets for: self._bottom_box

        self._bottom_box_spinner = Gtk.Spinner ()
        self._bottom_box.add (self._bottom_box_spinner)

        self._bottom_box.pack_end (Gtk.Label (label = "Project-A Python Driver by Luke A.C.A. Rieff"), True, True, 5);

        self.add (self._main_box)

        # Other shit

        self._active_discoverer = None
        self._active_discoverer_io_watcher = None

    """
        Starts the connect process to the specified device.
        \ widget: callee widget.
        \ row: the row clicked.
        \ col: the column clicked.
    """
    def _on_connect_press (self, widget, row, col):
        model = widget.get_model ()

        name = model[row][0]
        address = model[row][1]
        port = int (model[row][2])

        # Make sure the address we're trying to connect to is not the default once.
        if address == "0.0.0.0" and int (port) == 0:
            print ("Default one cannot be used for connecting.")
            return

        print (f"Performing connection attempt for {address}:{port} - {name}")

        # Creates the connecting window, and starts connecting it.
        connectWindow = ConnectWindow (address, port)
        connectWindow.set_modal (True)
        connectWindow.set_transient_for (self)
        connectWindow.set_position(Gtk.WindowPosition.CENTER)
        connectWindow.show_all ()

        # Checks if we're connected.
        if connectWindow.connect ():
            control = connectWindow._control

            # Destroys the connect window.
            connectWindow.destroy ()
            del connectWindow

            # Creates the new control window.
            controlWIndow = ControlWindow (control)
            controlWIndow.set_transient_for (self)
            controlWIndow.set_position(Gtk.WindowPosition.CENTER)
            controlWIndow.show_all ()

    """
        Starts the discovery for new devices.
        \ widget: the callee widget.
    """
    def _on_discovery_start_pressed (self, widget):
        assert (self._active_discoverer == None)
        assert (self._active_discoverer_io_watcher == None)

        widget.set_sensitive (False)

        print (f"Starting Discovery ...")
        
        self._bottom_box_spinner.start ()

        self._active_discoverer = Discovery (int (self._top_box_port_entry.get_text ()), DISCOVERY_WINDOW_TIMEOUT, int (self._top_box_pkt_cnt_spin_button.get_value ()), False)
        self._active_discoverer.start ()

        self._active_discoverer_io_watcher = GLib.io_add_watch (self._active_discoverer._socket.fileno (), GLib.IO_IN, lambda a, b : self._active_discoverer.poll ())
        GLib.timeout_add (DISCOVERY_WINDOW_TIMEOUT * 1000.0, self._on_discovery_likely_end)

    """
        Gets called at the end of the discovery process.
    """
    def _on_discovery_likely_end (self):
        assert (self._active_discoverer != None)
        assert (self._active_discoverer_io_watcher != None)

        # Since we're not entirely sure if this is done properly, end in infinite loop
        #  until poll returns False, which indicates the scan is done.
        while self._active_discoverer.poll () == True:
            pass

        # Processes the devices, and adds them to our result list.
        self._scroll_box_discovered_list_store.clear ()
        for device in self._active_discoverer._devices:
            self._scroll_box_discovered_list_store.append ([ device[0], device[1], str (device[2]) ])

        # Sets the button to be used again, and stops the spinner.
        self._top_box_refresh_button.set_sensitive (True)
        self._bottom_box_spinner.stop ()

        # Since we're done processing, restore reset everything.
        self._active_discoverer_io_watcher = None
        self._active_discoverer = None

        # Removes the IO watch
        if (self._active_discoverer_io_watcher != None):
            GLib.source_remove (self._active_discoverer_io_watcher)

        return False

class ConnectWindow (Gtk.Window):
    """
        Creates an new connect window instance.
    """
    def __init__ (self, host, port):
        Gtk.Window.__init__ (self, title = f"Attempting connecting to {host}:{port}")

        self._host = host
        self._port = port

        self._main_box = Gtk.Box (orientation = Gtk.Orientation.VERTICAL, margin = 20)

        # Widgets for: self._main_box

        self._main_box_progress_bar = Gtk.ProgressBar (margin_bottom = 10)
        self._main_box_progress_bar.set_text ("Preparing ...")
        self._main_box_progress_bar.set_show_text (True)
        self._main_box.add (self._main_box_progress_bar)

        self._main_box.add (Gtk.Label (label = f"Host: {self._host}"))
        self._main_box.add (Gtk.Label (label = f"Port: {self._port}"))

        self.add (self._main_box)

    def connect (self):
        # Creates the TCP socket.
        self._control = Control (self._host, self._port, False)
        
        # Tells that we're connecting.
        self._main_box_progress_bar.set_fraction (0.3)
        self._main_box_progress_bar.set_text ("Connecting ...")

        # Since we're blocking, trigger update.
        while Gtk.events_pending ():
            Gtk.main_iteration ()

        # Attempts to connect the TCP socket.
        try:
            self._control.tcp_connect ()    
        except Exception as e:
            self._control = None
            self._main_box_progress_bar.set_text (f"Connection failed: {e}")
            return False

        # Since we're blocking, trigger update.
        while Gtk.events_pending ():
            Gtk.main_iteration ()

        # Performs the connection attempt.
        try:
            if self._control.proto_connect () == False:
                self._main_box_progress_bar.set_text ("Connection rejected!")
                self._main_box_progress_bar.set_fraction (1.0)
                return False
        except Exception as e:
            self._control = None
            self._main_box_progress_bar.set_text (f"Connection failed: {e}")
            return False

        # Sets the text to indicate we're connected.
        self._main_box_progress_bar.set_text ("Connection approved.")
        self._main_box_progress_bar.set_fraction (1.0)

        # Returns true, since we're connected.
        return True


class ControlWindow (Gtk.Window):
    """
        Creates an new control window instance.
    """
    def __init__ (self, control):
        self._control = control

        Gtk.Window.__init__ (self, title = f"{self._control._host}:{self._control._port}")
        self.connect ("destroy", self._on_destroy)

        self._main_box = Gtk.Box (orientation=Gtk.Orientation.VERTICAL)

        # Widgets for: self._main_box

        self._top_box = Gtk.Box (orientation=Gtk.Orientation.HORIZONTAL, margin = 5)
        self._scroll_box = Gtk.Box (orientation=Gtk.Orientation.VERTICAL)
        self._bottom_box = Gtk.Box (orientation=Gtk.Orientation.HORIZONTAL, margin = 10)

        self._main_box.add (self._top_box)
        self._main_box.add (Gtk.Separator (orientation = Gtk.Orientation.HORIZONTAL))
        self._main_box.add (self._scroll_box)
        self._main_box.pack_end (self._bottom_box, False, True, 0)
        self._main_box.pack_end (Gtk.Separator (orientation = Gtk.Orientation.HORIZONTAL), False, True, 0)

        # Widgets for: self._top_box

        self._top_box.add (Gtk.Label (label = "Update Interval (ms): ", margin_right = 10))

        self._top_box_update_interval_spin_button =  Gtk.SpinButton ()
        self._top_box_update_interval_spin_button.set_adjustment (Gtk.Adjustment (upper = 1000, lower = 50, step_increment = 5, page_increment = 5, value = 200))
        self._top_box_update_interval_spin_button.connect ("value-changed", self._on_info_interval_change)
        self._top_box.add (self._top_box_update_interval_spin_button)

        self._top_box.add (Gtk.Separator (orientation = Gtk.Orientation.VERTICAL, margin_left = 10, margin_right = 10))
        self._top_box_close_connection_button = Gtk.Button.new_with_label ("Close Connection")
        self._top_box_close_connection_button.connect ("pressed", self._on_close_connection_pressed)
        self._top_box.add (self._top_box_close_connection_button)


        # Widgets for: self._scroll_box

        self._scroll_box_motors = []
        for i in range (0, 6):
            motor_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, margin = 10)

            motor_box_control = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_left = 20)
            motor_box_control_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            motor_box_control_bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            motor_box_control.add (motor_box_control_top)
            motor_box_control.add (Gtk.Separator (orientation = Gtk.Orientation.HORIZONTAL, margin_top = 10, margin_bottom = 10))
            motor_box_control.add (motor_box_control_bottom)

            motor_box_control_top.add (Gtk.Label (label = f"Stepper {i}"))
            motor_box_control_top.add (Gtk.Separator (orientation = Gtk.Orientation.VERTICAL, margin_left = 10, margin_right = 10))

            motor_box_control_top_enable_disable_button = Gtk.Switch ()
            motor_box_control_top_enable_disable_button.set_active (False)
            motor_box_control_top_enable_disable_button.connect ("notify::active", self._on_stepper_enable_disable_toggle, i)
            motor_box_control_top.add (motor_box_control_top_enable_disable_button)
            motor_box_control_top.add (Gtk.Separator (orientation = Gtk.Orientation.VERTICAL, margin_left = 10, margin_right = 10))

            motor_box_control_top_status_label = Gtk.Label (label = "Pos: */*, Speed: */*/*, NA | NA | NA")
            motor_box_control_top.add (motor_box_control_top_status_label)

            motor_box_control_bottom_new_pos_spin_button = Gtk.SpinButton ()
            motor_box_control_bottom_new_pos_spin_button.set_adjustment (Gtk.Adjustment (upper = 2_147_483_647, lower = -2_147_483_647, step_increment = 2, page_increment = 10, value = 0))
            motor_box_control_bottom.add (motor_box_control_bottom_new_pos_spin_button)

            motor_box_control_bottom_trigger_movement_button = Gtk.Button (label = "Trigger Movement", margin_left = 10)
            motor_box_control_bottom_trigger_movement_button.connect ("pressed", self._on_trigger_movement_pressed, i)
            motor_box_control_bottom.add (motor_box_control_bottom_trigger_movement_button)

            motor_box.add (Gtk.Image.new_from_file (os.path.dirname(os.path.realpath(__file__)) + '/assets/stepper.png'))
            motor_box.add (motor_box_control)

            self._scroll_box.add (motor_box)

            self._scroll_box_motors.append ((
                motor_box,
                motor_box_control_top_enable_disable_button,
                motor_box_control_bottom_new_pos_spin_button,
                motor_box_control_top_status_label
            ))

        # Widgets for: self._bottom_box

        self._bottom_box_spinner = Gtk.Spinner ()
        self._bottom_box.add (self._bottom_box_spinner)

        self._bottom_box.pack_end (Gtk.Label (label = f"Connected to {self._control._host}:{self._control._port}"), True, True, 5)

        self.add (self._main_box)

        # Widgets for: self._top_box

        self.add (self._main_box)

        # Sets the interval with default
        self._info_change_timeout = GLib.timeout_add (200.0, self._on_info_request_interval)

    def _on_info_interval_change (self, widget):
        GLib.source_remove (self._info_change_timeout)
        self._info_change_timeout = GLib.timeout_add (float (widget.get_value ()), self._on_info_request_interval)

    def _on_info_request_interval (self):
        steppers = self._control.get_stepper_info ()

        for i, stepper in enumerate (steppers, start = 0):
            gtk_stepper = self._scroll_box_motors[i]
            gtk_stepper[3].set_text (f"Pos: {stepper.get('current_pos')}/{stepper.get('target_pos')}, Speed: {stepper.get('current_speed')}/{stepper.get('min_speed')}/{stepper.get('max_speed')}, {'IM' if stepper.get('flags') & CONTROL_PACKET_STEPPER_INFO_FLAG_MOVING else 'NM'} | {'EN' if stepper.get('flags') & CONTROL_PACKET_STEPPER_INFO_FLAG_ENABLED else 'NE'} | {'AT' if stepper.get('flags') & CONTROL_PACKET_STEPPER_INFO_FLAG_AUTOMATIC else 'MA'}")
        
        return True

    def _on_stepper_enable_disable_toggle(self, widget, gparam, stepper_n):
        self._control.stepper_enable_disable (stepper_n, widget.get_active ())

    def _on_trigger_movement_pressed (self, widget, stepper_n):
        gtk_motor = self._scroll_box_motors[stepper_n]
        new_pos = int (gtk_motor[2].get_value ())
        self._control.send_stepper_move_to (stepper_n, new_pos)

    def _on_close_connection_pressed (self, widget):
        self.destroy ()

    def _on_destroy (self, widget):
        GLib.source_remove (self._info_change_timeout)
        self._control._reset ()



####
## Main Code
####

if __name__ == "__main__":
    discoveryWindow = DiscoveryWindow ()
    discoveryWindow.show_all ()
    discoveryWindow.connect ("destroy", Gtk.main_quit)

    Gtk.main ()
