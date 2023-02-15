#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

"""
Library to control the Siglent SDG 2082 X Arbitrary waveform generator


There is not much that has been implemented so far:
- Chanel » load a stored waveform, implementation of :<channel>:WVDT Command

"""

from __future__ import print_function, division

import pyvisa as visa               # serial interface to oscilloscope
from typing import Final            # define constants
import logging as log               # error and debugging logging


class prefix_interface:
    """
    Provide a 
        - write()
        - read()
        - ask()
        - read_raw()
        - ask_raw()
    function which also prefixes a command from the SCPI command tree. Therefore you don't have to write always the whole command.

    P.ex.: The `Channel` class has an interface with the prefix ":C{num}" where "{num}" is the channel number and instead of having to type ":C1:ARWV?" every time a call from one of fhe functions within this class will only contain the string ":ARWV" which will be completed to the example mentioned here.
    """

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
        # print("Prefix-Interface Write: " + "%s%s"%(self._prefix, command))    # Sometimes useful for debugging therefore still existing in this code.
        """
        Sent some a command to the device

        Parameters
        ----------
        command : str
            The SCPI command which was made to be send to the device
        """
        self._device.write("%s%s" % (self._prefix, command))

    def read(self) -> str:
        """
        Read an answer from the device

        Returns
        -------
        answer: str
            The query result from the device
        """
        return self._device.read()

    def read_raw(self) -> str:
        """
        Read an answer from the device but the results are no strings

        Returns
        -------
        answer: bytestring
            The query result from the device as a bytestring
        """
        return self._device.read_raw()

    def ask(self, command) -> str: 
        """
        Query information from the device

        Parameters
        ----------
        command : str
            The SCPI command to query some information

        Returns
        -------
        answer: bytestring
            The query result from the device
        """
        self.write(command)
        return self.read()

    def ask_raw(self, command) -> str:
        """
        Query information from the device but the results are not strings

        Parameters
        ----------
        command : str
            The SCPI command to query some information

        Returns
        -------
        answer: str
            The query result from the device as a bytestring
        """
        self.write(command)
        return self.read_raw()

    def boolean_property(
        self,
        scpi_cmd: str,
        scpi_value_on: str,
        scpi_value_off: str,
        err_description_class: str,
        err_description_option: str,
        value: bool | None = None,
        scpi_return_true: str = None,
        scpi_return_false: str = None
    ) -> bool | None:
        """
        Many SCPI commands are just querries for a boolean property. Sometimes it's the values "True" and "False", sometimes "ON" and "OFF", sometimes "1" and "0" ans sometimes setting the value requires another key of pairs than the device will return when querying the current setting. Therefore this wrapper function takes all possibilities for one specific SCPI command and converts from the boolean values `True` and `False` to the language the instrument is speaking.
        This function works in two directions (like the whole rest of this API): When no value which hast to be set was given to the function as an argument then the current setting will be read out from the device and returned. If the optional variable `value` was set then this function will return nothing but instead the setting inside the device is changed.

        Parameters
        ----------
        scpi_cmd : str
            Ths SCPI Command to access the specified property in the device settings
        scpi_value_on : str
            The value which has to be send to the string in order to turn the setting on aka. setting the property to `True`
        scpi_value_off : str
            The value which has to be send to the string in order to turn the setting off aka. setting the property to `False`
        err_description_class : str
            To provide error messages when something happens this helps specifying in which device control-object aka. class the error ocurred
        err_description_option : str
            Also useful to provide error information. This type of the error message specifies the SCPI command / function name / etc. for which the error ocurred. The rest of the error message is predefined.
        value : bool, optional
            When no parameter is specified then the current setting will be queried from the device and given back as a return value. When this value is set to something else than `None` then the setting in the device will change.
        scpi_return_true : str, optional
            Sometimes the device answers with another pair of keys than what is required to set a settings value. Therefore this can be used to specify which answer should be interpreted as a boolean `True`
        scpi_return_false : str, optional
            Sometimes the device answers with another pair of keys than what is required to set a settings value. Therefore this can be used to specify which answer should be interpreted as a boolean `False`
        
        Returns
        -------
        Return : boolean
            If the parameter value was not used or not set to something else than `None` then this function will return the current device setting for the specified SCPI command
        """

        # if parameter value is None -> get current state from scpi option
        if value == None:

            # if additional scpi return values have not been specified: use the same as the ones for sending
            scpi_return_true = scpi_value_on if scpi_return_true == None else scpi_return_true
            scpi_return_false = scpi_value_off if scpi_return_false == None else scpi_return_false

            return {
                scpi_return_true.upper(): True,
                scpi_return_false.upper(): False
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
                True: scpi_value_on,
                False: scpi_value_off
            }[value]
        ))


class Channel:

    """
    Output Channel Module
    =====================

    This class is used to define all the functionalities to drive an output channel.

    Summary
    -------

    .. TODO: Generate summary


    Background Information
    ----------------------

    An Arbitrary Waveform Generator has multiple output channels which this device is using to release analog voltages. Usually these channels are numbered starting with 1. This device can send electrical signals through the output channel with a high rate of output samples. 

    """

    _Num = None
    _Interface = None

    def __init__(self, num : int, device : object) -> None:
        """
        Initialize an Channel output

        Parameters
        ----------
        num : int
            Channel number, the first channel usually starts with number 1
        device: object
            the visa control object to interact with the device, this will only be passed to an prefix_interface class.
        """
        self._Num = num
        self._Interface = prefix_interface(device, (":C%i"%(num)))
    
    def waveform_index(self, num: int | None = None) -> int | None: 
        """
        Get / Set the waveform on the output channel by its index.
        The device contains a list of stored waveforms. Each builtin waveform can be referenced by its name or by its index.
        When this function is called with a parameter it sets the waveform to the index passed within the parameter.
        When this function is called without a parameter it queries the index of the currently displayed waveform.

        Parameters
        ----------
        num : int, optional
            The index number for the waveform that should be set. If this parameter is missing the output will not be set but instead the index of the currently selected waveform will be returned.

        Returns
        -------
        wav_index : int, optional
            The index of the currently released waveform. This value will only be returned if no parameter was passed to the call of this function.  
        """
        if num == None:
            return int(self._Interface.ask(":ARWV?").split(",")[1]) # filter the index id out of the response
        
        if not type(num) == int:
            return log.error( "Chanel %i: Cannot load waveform by index, %s is NaN"%(self._Num, num) )
        
        return self._Interface.write(":ARWV INDEX,%i"%(num))

class SDG2082X:

    _device = None
    _Interface = None

    def __init__(self, DEVICE: str) -> None:
        """
        Initialise the waveform generator device

        Parameters
        ----------
        DEVICE : str
            This is a device descriptor which specifies the device that the VISA resource manager should access.
        """
        rm = visa.ResourceManager('@py')    # get the list of USB devices
        # The '@py' string tells the resource manager to look for the pyvisa library.
        # this works better than the ni-visa library
        # without this parameter it might use the ni-visa library as default
        devices = rm.list_resources()       # list all available visa compatible devices

        ## TODO: Make the initialization process properly working. Currently it only works when the device descriptor is passed to this function as an argument but the device is not connected via USB. Is there a possibility to scan through the network with the visa resource manager?
        """
        device_init_done = False

        # now we start looking for our awg in the list of visa compatible devices
        # If a device has been specified: Try to find the first fitting value in the list of all devices
        if DEVICE != '':
            for i in range(len(devices)):
                # the specified string is in the name of the device -> device found
                if DEVICE in str(devices[i]):
                    self._device = rm.open_resource(devices[i])
                    device_init_done = True
                    break   # no need to run this loop any more

        # if no device was specified or the device cannot be found: ask for a device in the list from the command line
        if device_init_done == False:

            # print a status message to inform the user about the current situation
            if DEVICE == '':
                print("No USB device has been specified.")
            else:
                print(
                    "The specified device cannot be found in the list of available devices.")

            # now ask for a device from the list of devices
            while device_init_done == False:
                print(
                    "Please select the Waveform Generator from the list of available devices:")
                for i in range(len(devices)):
                    print("%i: %s" % (i + 1, devices[i]))

                dev_index = int(input()) - 1

                # just check weather the user input makes sense
                if (dev_index < 0) or (dev_index >= len(devices)):
                    log.error("Invalid number. Please try it again.")
                else:
                    self._device = rm.open_resource(devices[dev_index])
                    device_init_done = True
        """
        self._device = rm.open_resource(DEVICE, timeout=5000, chunk_size=40*1024, query_delay=0.25, read_termination='\n', write_termination='\n') 
        self._device.read_termination = "\n"

        self.Channel = [ Channel(i+1, self._device) for i in range(2) ]

        self.Interface = prefix_interface(self._device, "") # root interface -> empty prefix

    def _close(self) -> None:  # close the device. This function will only be called by the destructor
        self._device.close()   # use visa close command

    def __del__(self) -> None:
        self._close()  # close the device before deleting it

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:   # create a string if someone does some weird type conversion or wants to print this object on the command line
        return "Arbitrary Waveform Generator %s" % (self._device)

    def reset(self) -> None:
        """
        Reset Device by performing the IEEE\ 488.2 Reset query `*RST`
        """
        self.Interface.write("*RST")  # IEEE488.2 Query to perform device reset

    def clear_error(self) -> None:
        """
        Clear status register including error queue. This command will send the IEEE\ 488.2 Command to Clear the status register `*CLS`

        Returns
        -------
        None
        """
        self.Interface.write("*CLS")  # IEEE488.2 Query to perform device reset

    def errors(self) -> str:
        """
        Query the Error List (IEEE\ 488.2)

        Returns
        -------
        errors : string
            The list of errors from the device

        Notice
        ------
        Querying the error list will also flush the list.
        """
        return self.Interface.ask(":SYST:ERR?")

    def identify(self) -> str:
        """
        Get IEEE488.2 Device Identification string `*IDN?`
    

        Returns
        -------
        identification : string
            each device has its own identification string which will be returned in this specific case.
        """
        return self.Interface.ask("*IDN?")
    
    def get_builtin_list(self) -> list :
        """
        Returns the list of builtin waveforms, sorted by the waveform index and including the waveform name

        Parameters
        ----------
        None

        Returns
        -------
        waveforms : 2d-list
            The list contains a all the builtin waveforms, each list entry is a list with two entries where the first one is the waveform index (integer) and the second one is the waveform name (string). 
            If the list is empty the call of this function will return the string "EMPTY"
        """
        answer = self.Interface.ask(":STL? BUILDIN")
        if answer == "EMPTY":
            return answer
        answer = answer.split(",")
        answer_sorted = [ [ int( str(answer[i]).split("M")[1] ), answer[i+1][1:] ] for i in range(0, len(answer), 2) ]
        answer_sorted.sort(key=lambda x:x[0])
        return answer_sorted


    def get_user_list(self) -> list :
        """
        Returns the list of user defined waveforms, sorted by the waveform index and including the waveform name

        Parameters
        ----------
        None

        Returns
        -------
        waveforms : list
            The list contains a all the waveforms which were uploaded by the user onto this device. Each list entry contains a string with the waveform name.
            If the list is empty the call of this function will return the string "STL WVNM"
        """
        answer = self.Interface.ask(":STL? USER")
        if answer == "EMPTY" or answer == "STL WVNM":
            return answer
        answer = answer[9::].split(",")
        return answer
    

