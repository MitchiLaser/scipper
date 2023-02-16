"""

Library to communicate to a PeakTech 4115 Arbitrary Waveform Generator

----------------------------------------------------------------------
Current To-Do List:

- Sources
- Trigger
- Burst


Future tasks:
- Analysis of the device error queue

Done:
- SYSTem Commands


Notes:
- Reading Data from the device is currently pain in the a** because it isn't sending any kind of line terminator in its response.
"""


from __future__ import print_function, division

import os                           # OS interface
import numpy as np                  # Numpy: Data storage
import pyvisa as visa               # serial interface to oscilloscope
from typing import Final, Union     # define constants
import logging as log               # error and debugging logging
import time                         # as long as the communication with the device is crappy as hell: wait until the device has send a reasonable answer


# set logging level
log.basicConfig(level=log.ERROR)


# ----------------
# Prefix-Interface
# ----------------

class prefix_interface:  # provide write(), read(), read_raw(), ask() and ask_raw() function for every class with separate prefix
    # p.ex. you want to control a channel. So you initialise a _interface instance of this class in the channel class
    # and set one default prefix for all channel commands, in this case ":CHAN%i"%(id_channel).
    # Then yon don't have to send the full command every single time.

    _prefix = None  # the string prefix
    _device = None  # the interface to which all the commands will be send

    def __init__(self, device, prefix) -> None:
        self._device = device
        self._prefix = prefix

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        return "Prefix Interface for device %s with Prefix: \"%s\"" % (self._device, self._prefix)

    def write(self, command) -> None:
        # print("Prefix-Interface Write: " + "%s%s"%(self._prefix, command))    # Sometimes usefull for debugging therefore still existing in this code.
        self._device.write("%s%s" % (self._prefix, command))

    def read(self) -> str:  # read the result from a command send to the scope
        return self.read_raw().decode()

    def read_raw(self) -> str:  # read the result from a command send to the scope
        return self._device.read_bytes( self._device.bytes_in_buffer )

    def ask(self, command) -> str:  # send a command with channel Number to the scope and get the answer
        return self.ask_raw(command).decode()

    def flush_buffer(self) -> None: # flush buffer, this is necessary to prevent from errors because the last SCPI command took to long to be received
        self._device.flush(visa.constants.VI_READ_BUF)

    # send a command with channel Number to the scope and get the answer (raw)

    def ask_raw(self, command) -> str:
        self.flush_buffer()
        self.write(command)
        time.sleep(0.2) # this is needed for the device to process the SCPI command
        return self.read_raw()

    def boolean_property(
        self,
        scpi_cmd: str,                  # command name of scpi option
        err_description_class: str,     # generate usefull error messages
        err_description_option: str,    # \_ needs to know in which class and for which scpi parameter the error ocurred
        value: Union[bool, None] = None # True or False -> set scpi option to value, None -> get current value of scpi option
    ) -> Union[bool, None]:

        # if parameter value is None -> get current state from scpi option
        if value == None:
            return {
                "ON": True,
                "1": True,
                "OFF": False,
                "0": False
            }[str(
                self.ask("%s?" % (scpi_cmd.upper()))
            ).upper()]   # uppercase conversion is used to prevent issues with lowercase / uppercase letters

        # check wether the parameter is a boolean
        if not type(value) == bool:
            return log.error("%s, %s: Cannot assign \"%s\" for %s, must be bool(True) or bool(False)" % (self._device, err_description_class, value, err_description_option))

        # write the scpi command
        self.write("%s %s" % (
            scpi_cmd,
            {
                True: "ON",
                False: "OFF"
            }[value]
        ))
    

    def set_boolean(
        self,
        scpi_cmd: str,                  # command name of scpi option
        err_description_class: str,     # generate usefull error messages
        err_description_option: str,    # \_ needs to know in which class and for which scpi parameter the error ocurred
        value: Union[bool, None] = None # True or False -> set scpi option to value, None -> get current value of scpi option
    ) -> Union[bool, None]:

        # check wether the parameter is existing
        if value == None:
            return log.error("%s, %s: Cannot assign empty value for %s, must be bool(True) or bool(False)" % (self._device, err_description_class, err_description_option))

        self.boolean_property(  # checked wether there is a value -> call the function that was made for this job
            scpi_cmd,
            err_description_class,
            err_description_option,
            value
        )


# --------
# channels
# --------

class channel:

    _Num_channel = None    # channel number
    _interface_sour = None  # interface for all SOURce Commands
    _interface_out = None   # interface for all OUTput Commands

    def __init__(self, num_channel : int, device : object) -> None:
        self._Num_channel = num_channel
        self._interface_sour = prefix_interface(device, ":SOUR%i" % num_channel)  # Not sweet, SOUR!
        self._interface_out = prefix_interface(device, ":OUTP%i" % num_channel)
    
    def inversion(self, state: Union[bool, None] = None) -> Union[bool, None]:
        """
        Change the polarity of a channel.
        
        The inversion can be either set to `False` (not inverted) or `True` (inverted). Inversion means that the voltage is multiplied by a value of (-1) to mirror it at the time-axis

        Parameters
        ----------
        state: Boolean or None
            If this parameter is not set or set to None (the default value) this function only returns the current setting for the inversion and changes nothing. 
            If this parameter is `True`, the inversion is activated. If if is `False` the inversion will be deactivated. In bot cases the function returns nothing.

        Returns
        -------
        machine_setting: Boolean or None
            The function only returns a value if the argument *state* was not used or set to `None`. Otherwise it will return nothing. The return value will be a boolean, indicating wether the inversion is turned on (`True`) or deactivated (`False`)
            
        """
        
        if state == None:   # No parameter specified: get the current device setting
            return {
                "NORM" : False,
                "INV" : True
            }[ str( self._interface_out.ask(":POL?") ).upper() ]
        
        if not type(state) == bool: # parameter is not a boolean value
            return log.error("Channel %i, inversion: Cannot assign with value \"%s\", must be a boolean"%(self._Num_channel, state))
        
        self._interface_out.write( ":POL %s"%(
            {
                True    :   "INV",
                False   :   "NORM"
            }[ state ]
        ) )


# ---------------------
# generic awg construct
# ---------------------

class awg_generic:

    _device = None
    Interface = None
    Channels = None

    def __init__(self, num_channels: int, USB_DEVICE: str = '', baud_rate : int = 9600) -> None:

        rm = visa.ResourceManager('@py')    # get the list of USB devices
        # The '@py' string tells the resource manager to look for the pyvisa library.
        # this works better than the ni-visa library
        # without this parameter it might use the ni-visa library as default
        devices = rm.list_resources()       # try to find the instrument

        device_init_done = False

        # now we start looking for our awg in the list of visa compatible devices
        # If a device has been specified: Try to find the first specified device in the list of devices
        if USB_DEVICE != '':
            for i in range(len(devices)):
                # the specified string is in the name of the device -> device found
                if USB_DEVICE in str(devices[i]):
                    self._device = rm.open_resource(devices[i])
                    device_init_done = True
                    break                       # no need to run this loop any more

        # if no device was specified or the device cannot be found: ask for a device in the list from the comand line
        if device_init_done == False:

            # print a status message to inform the user about the current situation
            if USB_DEVICE == '':
                print("No USB device has been specified.")
            else:
                print("The specified device cannot be found in the list of available devices.")

            # now ask for a device from the list of devices
            while device_init_done == False:
                print("Please select the Waveform Generator from the list of available devices:")
                for i in range(len(devices)):
                    print("%i: %s" % (i + 1, devices[i]))

                dev_index = int(input()) - 1

                # just check weather the user input makes sense
                if (dev_index < 0) or (dev_index >= len(devices)):
                    log.error("Invalid number. Please try it again.")
                else:
                    self._device = rm.open_resource(devices[dev_index])
                    device_init_done = True
            
        self._device.read_termination = ''      # not sure wether this is needed or not, didn't worked independent of that option
        self._device.write_termination = '\n'   # PeakTech AWG needs / sends a '\n' after every single command
        self._device.baud_rate = baud_rate      # set baud rate of the device, the default is 9600
        # all the other RS232 Parameters should be visa default compliant

        self.Interface = prefix_interface(self._device, "")    # root interface -> no prefix
        self.Channels = [ channel(i + 1, self._device) for i in range(num_channels) ]   # initialise all channels

    def _close(self) -> None:  # close the device. This function will only be called by the destructor
        self._device.close()   # use visa close command

    def __del__(self) -> None:
        self._close()  # close the device before deleting it

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:   # crete a string if someone does some weird type conversion or wants to print this object on the command line
        return "Arbitrary Waveform Generator %s" % (self._device)

    def reset(self) -> None:
        self.Interface.write("*RST")  # IEEE488.2 Query to perform device reset
    
    # clear error queue off the device
    def clear_error(self) -> None:
        self.Interface.write("*CLS")  # IEEE488.2 Query to perform device reset
    
    def errors(self) -> str:
        return self.Interface.ask(":SYST:ERR?")

    def display(self, state : Union[bool, None] = None) -> Union[bool, None]:
        """
        Turn the display on and off or ask in which state the display currently is.

        If this function is called without the parameter it gets the current state of the display. If a boolean parameter is given to the function it will set the device display into the wanted state.

        Parameters
        ----------
        state: Boolean or None
            Set this parameter to `True` to turn the display on or to `False` to turn the display off

        Returns
        -------
        disp_state: Boolean or None
            Returns a `True` if the display is in use and a `False` if the display is turned off. The return value will only be returned if no parameter was specified.
        """
        return self.Interface.boolean_property(
            ":DISP",
            "root_class",
            "Display",
            state
        )

    def unlock(self) -> None:
        """
        Return to local control. After a PC link was established the device stops listening for input on any of its physical keys. To reenable them it can either be turned off and on again or unlocked with a call of this function.
        """
        self.Interface.write(":SYST:LOC")




# -------------------------------------------------------------------
# specific awg models from the vendors based on the generic awg class
# -------------------------------------------------------------------

class pt4115(awg_generic):

    def __init__(self) -> None:
        super().__init__(2)  # 2 channels
