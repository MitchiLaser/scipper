# -*- encoding: utf-8 -*-

"""

Library to control a Oscilloscope from the Rigol DS1000 series via its USB interface


Programming-Manual: https://beyondmeasure.rigoltech.com/acton/attachment/1579/f-0012/0/-/-/-/-/file.pdf
User Manual (german): https://www.batronix.com/files/Rigol/Oszilloskope/_DS1000DE/DS1000DE_Anleitung_DE.pdf


Currently I have only a DS1102E here to test the library. The 1102D part has never been tested on a device.
Right now the communication is done via visa (virtual instruments software architecture).
In the future there will hopefully be an option to choose between a visa, usbtmc os RS232 based interface


=========================================================================================================================

-----------------
work in progress:
-----------------

    - TIMebase
        - [DELayed] OFFset -> implement range check and fix issue with range in programming manual
        - [DELayed] SCAle -> implement range check and fix issue with range in programming manual AND: Parameter can only take several values
    - Trigger
        - everything missing except mode()
        - This is gonna be some serious amount of work
    - Oscilloscope
        - Choose between VISA or USBTMC or Serial interface
        - check return value of *IDN? string to be sure that it's the right scope
                alternative: global initialization of a scope and based on the *IDN? string the right object is chosen
    - Logic analyzer -> need a scope that has a logic analyzer
        |_ actually implemented: display()
        \_ don't forget to implement the ":WAV:DATA? DIGital" command in there
    - WAVeform commands » capture waveform data
      |_ Chanel::waveform()           » implement timebase axis generation for waveform data not in NORMAL mode
      |_ Math::waveform()             » temporarily disabled
      |_ FFT -> Math:FFT_waveform()   » temporarily disabled
     (\_ Logic::waveform() )          » temporarily disabled, I have no device here to check wether that will work
    - Chanel-Class:
        - Offset is depending on current scale -> Check scale before setting offset and inform the user if they use a wrong offset.
          \_ Programming manual: Page 68 (2-56)
        - Scale value is depending on currently used probe -> check before setting value and and inform the user if they try to set an invalid value
          \_ Programming manual: Page 69 (2-57)
    - Function to store scope Config (in file) and Upload Config (from file) to scope
    - Waveform-Capture: also support other timebase modes than 'Y-T' -> 'X-Y' and 'ROLLING' are missing
    - Maybe some functions can be written smaller by using prefix_interface::boolean_property() or something like prefix_interface::query() (like display::query())
      \_ take a look where this can be done, I never took the time to do that
    - replace self written ask() and ask_raw() functions with visa->query()


    - every time log.error() is called -> throw an exception
    - optionally use Scope.beep() when an error occurs
      |_ option that can be set during the initialization of the scope or during runtime
      \_ if I have enough time: morse code the error message of the scope
    - implement also a usbtmc and a serial alternative for the interface -> need to rework all that stuff, might end up in interface.py
      \_ merge that with prefix_interface class to make everything a bit cleaner
    - build a GUI or a TUI (curses) for this library that will run when module is executed as main

    



There's a research part in a comment by the end of this file below the credits list.
"""





from __future__ import print_function, division

import os                           # OS interface
import numpy as np                  # Numpy: Data storage
import sys                          # interface to the operating system
import pyvisa as visa               # serial interface to oscilloscope
from typing import Final, Union     # define constants
import logging as log               # error and debugging logging





# set logging level
log.basicConfig(level=log.ERROR)





class prefix_interface: # provide write(), read(), read_raw(), ask() and ask_raw() function for every class with separate prefix
                        # p.ex. you want to control a chanel. So you initialise a _interface instance of this class in the Chanel class
                        # and set one default prefix for all chanel commands, in this case ":CHAN%i"%(id_chanel).
                        # Then yon don't have to send the full command every single time.
    
    _prefix = None # the string prefix
    _device = None # the interface to which all the commands will be send



    def __init__(self, device, prefix) -> None:
        self._device = device
        self._prefix = prefix

    

    def __repr__(self) -> str:
        return self.__str__()



    def __str__(self) -> str:
        return "Prefix Interface for device %s with Prefix: \"%s\""%(self._device, self._prefix)
    


    def write(self, command) -> None:
        #print("Prefix-Interface Write: " + "%s%s"%(self._prefix, command))    # Sometimes usefull for debugging therefore still existing in this code.
        self._device.write( "%s%s"%(self._prefix, command) )
    


    def read(self) -> str:  # read the result from a command send to the scope
        return self._device.read()
    


    def read_raw(self) -> str:  # read the result from a command send to the scope
        return self._device.read_raw()
    


    def ask(self, command) -> str:  # send a command with Chanel Number to the scope and get the answer
        self.write(command)
        return self.read()



    def ask_raw(self, command) -> str:  # send a command with Chanel Number to the scope and get the answer (raw)
        self.write(command)
        return self.read_raw()
    


    def boolean_property(
            self,
            scpi_cmd : str,                     # command name of scpi option
            scpi_value_on : str,                # turn scpi option on  by setting it to this value
            scpi_value_off : str,               # turn scpi option off by setting it to this value
            err_description_class : str,        # generate usefull error messages
            err_description_option : str,       #  \_ needs to know in which class and for which scpi parameter the error ocurred
            value : Union[bool,None] = None,    # True or False -> set scpi option to value, None -> get current value of scpi option
            scpi_return_true : str = None,      # the scpi command can use some different return values to tell that something is turned on or not
            scpi_return_false : str = None      #  \_ to avoid issues with this behavior of the scope some separate return value options can be specified
        ) -> Union[bool, None]:
        
        # if parameter value is None -> get current state from scpi option
        if value == None:

            # if additional scpi return values have not been specified: use the same as the ones for sending
            scpi_return_true = scpi_value_on if scpi_return_true == None else scpi_return_true
            scpi_return_false = scpi_value_off if scpi_return_false == None else scpi_return_false

            return {
                scpi_return_true.upper()  : True,
                scpi_return_false.upper() : False
            }[ str(
                self.ask( "%s?"%(scpi_cmd.upper()) )
            ).upper() ]   # uppercase conversion is used to prevent issues with lowercase / uppercase letters
        
        # check wether the parameter is a boolean
        if not type(value) == bool:
            return log.error("%s, %s: Cannot assign \"%s\" for %s, must be bool(True) or bool(False)"%(self._device, err_description_class, value, err_description_option))
        
        # write the scpi command
        self.write("%s %s"%(
            scpi_cmd,
            {
                True  : scpi_value_on,
                False : scpi_value_off
            } [ value ]
        ))





class timebase: # a class to controll all the timebase settings
    
    
    _device = None     # the oscilloscope » talk to this interface
    _interface = None  # the prefix-interface to talk to this device



    def __init__(self, device : None) -> None:
        self._device = device      # a device to send the commands
        self._interface = prefix_interface(device, ":TIM") # a prefixed interface to send timebase commands with ":TIM" prefix
    


    # get / set timebase mode
    # no parameter -> get mode
    #                 oscilloscope returns values 'MAIN' or 'DELAYED'
    # parameter mode -> set value to mode which can be: (uppercase / lowercase invariant)
    #                   - "NORMAL"
    #                   - "DELAYED"
    def mode(self, mode = None) -> str:
        
        if mode == None:    # no parameter specified: ask for current mode setting
            return str( self._interface.ask(":MODE?") ).upper()    # uppercase conversion is unnecessary

        mode_types = {
            "MAIN" : "MAIN",    # main timebase
            "DELAYED" : "DEL"   # delayed timebase
        }

        mode = str(mode).upper()    # just in case there are some lowercase letters

        if not mode in [ *mode_types.keys() ]:
            return log.error("%s, Timebase: Cannot assign \"%s\" as mode, must be one of the following values: %s"%(self._device, mode, [ *mode_types.keys() ]))

        self._interface.write( ":MODE %s"%( mode_types[mode] ) )
    


    # get / set offset value
    # no parameter: get offfset value for the main timebase in unit Seconds, value of type float()
    # parameter value -> set offset value
    #                    - must be of type float()
    # TODO: Parameter value is depending on the current settings for the (whatever the parameter is, program manual is weird)
    #?      See Page 28 Programming manual (2-16)
    #?      Whoever the fuck wrote this programming manual never mentioned which Parameter it is depending on.
    #?      Hopefully this will be figured out soon. I am getting slightly mad from this poor documentation for the oscilloscope
    #?      Same Shit for the delayed_offset()
    def offset(self, value = None) -> float:
        
        if value == None:   # no value specified: ask for current setting
            return float(self._interface.ask(":OFFS?"))
        
        if not type(value) in [int, float]: # error: no number
            return log.error("%s, Timebase: Cannot assign \"%s\" as offset, must be of type int / float"%(self._device, value))
        
        self.mode("MAIN")   # following command only works in main Mode (It might be that I understood something wrong, maybe this line should be removed)
        self._interface.write(":OFFS %f"%(value))
    


    # same as offset() but this time its for the delayed timebase not the main timebase
    # take a look at the notes for the timebase::offset() function, it's exactly the same
    # Furthermore: There's a long TODO note at the offset() function which also applies to this function
    def delayed_offset(self, value = None) -> float:
        
        if value == None:   # no value specified: ask for current setting
            return float(self._interface.ask(":DEL:OFFS?"))
        
        if not type(value) in [int, float]: # error: no number
            return log.error("%s, Timebase: Cannot assign \"%s\" as delayed offset, must be of type int / float"%(self._device, value))
        
        self.mode("DELAYED")   # following command only works in delayed Mode (It might be that I understood something wrong, maybe this line should be removed)
        self._interface.write(":DEL:OFFS %f"%(value))
    


    # get / set scale value
    # no parameter: get scale value for the main timebase in unit Seconds, value of type float()
    # parameter value -> set offset value
    #                    - must be of type float
    # TODO: Parameter value is depenging on the current settings for the (whatever the parameter is, program manual is weird)
    #?      See Page 29 Programming manual (2-17)
    #?      Whoever the fuck wrote this programming manual never mentioned which Parameter it is depending on.
    #?      Hopefully this will be figured out soon. I am getting slightly mad from this poor documentation for the oscilloscope
    #?      same shit for delayed_scale()
    # TODO: The parameter can only take several values, these have to be checked.
    def scale(self, value = None) -> float:
        
        if value == None:   # no value specified: ask for current setting
            return float(self._interface.ask(":SCAL?"))
        
        if not type(value) in [int, float]: # error: no number
            return log.error("%s, Timebase: Cannot assign \"%s\" as scale, must be of type int / float"%(self._device, value))
        
        self.mode("MAIN")   # following command only works in main Mode (It might be that I understood something wrong, maybe this line should be removed)
        self._interface.write(":SCAL %f"%(value))

    

    # same as scale() but this time its for the delayed timebase not the main timebase
    # take a look at the notes for the timebase::scale() function, it's exactly the same
    # Furthermore: There's a long TODO note at the scale() function which also applies to this function
    def delayed_scale(self, value = None) -> float:
        
        if value == None:   # no value specified: ask for current setting
            return float(self._interface.ask(":SCAL?"))
        
        if not type(value) in [int, float]: # error: no number
            return log.error("%s, Timebase: Cannot assign \"%s\" as delayed scale, must be of type int / float"%(self._device, value))
        
        self.mode("DELAYED")   # following command only works in delayed Mode (It might be that I understood something wrong, maybe this line should be removed)
        self._interface.write(":DEL:SCAL %f"%(value))
    


    # get / set Timebase format
    # no parameter: get format setting for the timebase as str() from ["X-Y", "Y-T", "SCANNING"]
    # parameter value -> set Timebase format setting
    #                    - must be one of ["XY", "YT", "SCAN"]
    def format(self, type = None) -> str:
        
        if type == None:   # no value specified: ask for current setting
            return { "X-Y":"XY", "Y-T":"YT", "SCANNING":"SCAN" }[ str( self._interface.ask(":FORM?") ).upper() ]   # uppercase conversion is unnecessary

        type = str(type).upper()

        format_types = ["XY", "YT", "SCAN"]

        if not type in format_types:
            return log.error("%s, Timebase: Cannot assign \"%s\" as format, must be one of the following values: %s"%(self._device, type, format_types))

        self._interface.write( ":FORM %s"%(type) )





class chanel:   # a class to interface every chanel separately


    _Number = None          # the number of the chanel (CH1, CH2, ...)
    _device = None          # the oscilloscope » talk to this interface
    _interface = None       # the prefix-interface to talk to this device
    _scope_timebase = None  # the oscilloscope timebase -> waveform-capruting needs this



    def __init__(self, id : int, device : None, scope_timebase : timebase) -> None:
        self._device = device   # a device to send the commands
        self._Number = id       # Chanel id
        self._interface = prefix_interface(device, (":CHAN%i"%(id)) )
        self._scope_timebase = scope_timebase     # access to the timebase of the scope -> needed for waveform



    def __repr__(self) -> str:
        return self.__str__()
        


    def __str__(self) -> str:   # crete a string if someone does some weird type conversion or wants to print this object on the command line
        return "Chanel %i of %s"%(self._Number, self._device)
    


    # Invert the Chanel signal or check wether it is inverted
    # Inverted      <-> bool(True)
    # Not inverted  <-> bool(False)
    def invert(self, state = None) -> str:
        return self._interface.boolean_property(
            ":INV",
            "ON",
            "OFF",
            "Chanel %i"%(self._Number),
            "inversion",
            state)



    # get / set status of bandwith limit for the chanel
    # Enabled   <-> bool(True)
    # Disabled  <-> bool(False)
    def bw_limit(self, state = None) -> str:
        return self._interface.boolean_property(
            ":BWL",
            "ON",
            "OFF",
            "Chanel %i"%(self._Number),
            "Bandwith Limit",
            state
        )
    
    
    
    # Activate or Deactivate Chanel or just get activity information
    # No parameter -> return activity information
    #              -> return bool(True)  » Chanel activated
    #              -> return bool(False) » Chanel deactivated
    # Parameter bool(True) | bool(False) -> activated | deactivated
    def activity(self, state = None) -> None:

        return self._interface.boolean_property(
            ":DISP",
            "1",
            "0",
            "Chanel %i"%(self._Number),
            "activity",
            state
        )



    # Get Coupling information for oscilloscope Chanel or set Coupling mode
    # No parameter -> returns Coupling information
    # Parameter type = "AC". "DC" or "GND" -> set coupling state of this chanel (uppercase / lowercase invariant)
    def coupling(self, type = None) -> str:

        if type == None:  # No type specified: only ask for coupling
            return self._interface.ask(":COUP?")

        type = str(type).upper() # remove lowercase letters
        
        if not ( type in ["DC", "AC", "GND"] ): # error handling: someone put in some wrong values
            return log.error("%s, Chanel %i: Cannot assign \"%s\" for coupling, must be 'AC', 'DC' or 'GND')"%(self._device, self._Number, type))
        self._interface.write(":COUP %s"%(type))
    


    # Offset of the oscilloscope chanel:
    # No Parameter -> return offset value
    # Parameter value: set offset value, unit: Volt
    # Offset can be set to the following values in +/- 1 µV steps:
    # - Scale >= 250mV: -40V to +40V
    # - Scale <  250mV: -2V  to +2V
    def offset(self, value = None) -> float:
        
        if value == None:   # no parameter set: Ask for value
            return float( self._interface.ask(":OFFS?") )
        
        if not type(value) in [int, float]: # check for type of value to make sure nobody sends something like a string
            return log.error("%s, Chanel %i: Cannot assign \"%s\" as offset value, must be integer or float"%(self._device, self._Number, value))
        
        # parameter set: set offset value
        self._interface.write(":OFFS %.6f"%(value))
    


    # get / set the value for the probe
    # no parameter: return current probe setting
    # parameter value: set probe setting, can be a value from the following list: 1, 5, 10, 50, 100, 500, 1000
    def probe(self, value = None) -> int:
        
        if value == None:   # no parameter: Ask for value
            return int( float( self._interface.ask(":PROB?") ) )
        
        # define all values for the chanel probes
        PROBES : Final = {
            "1"    :    1,
            "5"    :    5,
            "10"   :   10,
            "50"   :   50,
            "100"  :  100,
            "500"  :  500,
            "1000" : 1000
        }
        
        if not str(value) in PROBES: # Check wether value for probe is possible
            return log.error("%s, Chanel %i: Cannot assign \"%s\" as probe, must be one of the following values: %s"%(self._device, self._Number, value, [*PROBES.values()]))

        self._interface.write(":PROB %i"%( PROBES[str(value)] ))
    


    # get / set scale of scope chanel
    # no parameter -> return currend scale value
    # parameter value: set scale value
    def scale(self, value = None) -> float:
        
        if value == None:   # No parameter: ask for value
            return float( self._interface.ask(":SCAL?") )

        # set scale value
        # this is currently an unsafe method, some checks wether the value is in range should be added.
        # the value will be printed up to the 6th number after the decimal separator: +/- 1µV, change to a useful value depending on current range
        if not type(value) in [int, float]: # value has wrong data type
            return log.error("%s, Chanel %i: Cannot assign \"%s\" as scale value, must be integer or float"%(self._device, self._Number, value))

        self._interface.write(":SCAL %.6f"%(value) )
    


    # get / set filter state
    # state can be True or False, for the oscilloscope: ON or OFF
    # no parameter -> get Filter state: function returns True or False
    # parameter state is bool(True) or bool(False) -> set Filter
    def filter(self, state = None) -> bool:
        return self._interface.boolean_property(
            ":FILT",
            "ON",
            "OFF",
            "Chanel %i"%(self._Number),
            "Filter",
            state
        )
    


    # get memory depth. This is only a getter because you cannot set the memory depth via this command
    def mem_depth(self) -> int:
        return int( self._interface.ask(":MEMD?") )



    # get / set fine scaling mode (aka vernier)
    # no parameter: get value -> True / False
    # @parameter value: set value -> True / False
    def fine_scale(self, value = None) -> bool:
        return self._interface.boolean_property(
            ":VERN",
            "ON",
            "OFF",
            "Chanel %i"%(self._Number),
            "Vernier mode (fine scaling)",
            value,
            "FINE",     # Vernier Mode activated   -> Scope returns 'Fine'
            "COARSE"    # Vernier Mode deactivated -> Scope returns 'Coarse'
        )
    


    # get sampling rate
    # this is only a getter
    # attention: this sends an ":ACQ" command not a ":CHAN" command
    def samplingrate(self) -> float:
        self._device.write(":ACQ:SAMP? CHAN%i"%(self._Number))
        return float( self._device.read() )
    


    # a function to get the waveform from this chanel
    # @parameter mode: the amount of data that can be acquired
    #            |_ default value: None -> use the value that is currently set in the device
    #            |_ can be "NORMAL", "RAW" or "MAXIMUM"
    #            \_ Programming-Manual: Page 82 (2-70)
    # returns a numpy -> ndarray with the waveform, all values use the unit "V" (voltage)
    def waveform(self, mode : str = None) -> np.ndarray:

        # if a mode has been specified: store the previous state of the mode, get data and restore it later
        prev_mode = None

        if not mode == None:

            # store the previous mode to make sure that the mode of the 
            prev_mode =  str( self._device.query(":WAV:POIN:MODE?") ).upper()


            # list of possible modes that can be set and their scpi commands
            modes = {
                "MAXIMUM" : "MAX",
                "NORMAL" : "NOR",
                "RAW" : "RAW"
            }

            
            ''' # TODO: as long as waveform capturing in normal mode is supported: only use normal mode
            # convert to uppercase to prevent from errors a user made by using lowercase letters in the keyword
            mode = str(mode).upper()
            
            # check wether mode that should be set is an appropriate value
            if not mode in [ *modes.keys() ]:
                return log.error("%s: Waveform-Capture: cannot assign \"%s\" as waveform mode, must be one of the following ones: %s"%(self._device, mode, [ *modes.keys() ]))
            
            # set new mode
            self._device.write( ":WAV:POIN:MODE %s"%( modes[mode] ) )
            '''
            self._device.write( ":WAV:POIN:MODE NOR" )



        # get waveform data
        self._device.write(":WAV:DATA? CHAN%i"%(self._Number))
        data = self._device.read_raw()

        

        # reset mode to previous state
        if not mode == None:
            self._device.write( ":WAV:POIN:MODE %s"%( modes[prev_mode] ) )
        

        # data has been send in raw binary format, convert it to numbers
        # after that map the data to an actual voltage value        
        # the first 10 bits are thrown away
        data = np.frombuffer( data[10:], "B" )

        # invert the data
        data = data * -1 + 255

        # shift by 130 - the voltage offset in counts, then scale to the actual voltage
        data = ( data - 130.0 - ( self.offset() / self.scale() * 25 ) ) / 25 * self.scale()


        # Generate time axis
        time = {    # generate the right timebase scale for the waveform, this is dependign on the 
                600 : np.linspace(self._scope_timebase.offset() - 6 * self._scope_timebase.scale(), self._scope_timebase.offset() + 6 * self._scope_timebase.scale(), 600), # CHx in NORmal mode: everything that is visible on the display
                8192 : None,    # TODO: CHx Half dublex short memory mode  \
                524288 : None,  # TODO: CHx Half dublex long  memory mode   \  maybe Acquire -> samplerate can help figuring that out
                16384 : None,   # TODO: CHx   simplex   short memory mode   /
                1048576 : None, # TODO: CHx   simplex   long  memory mode  /
            } [ len(data)]
        
        # processing is done, return values
        return [time, data]





class trigger:  # todo: a class to controll all the trigger settings
    
    _device = None     # the oscilloscope » talk to this interface
    _interface = None  # the prefix-interface to talk to this device



    def __init__(self, device : None) -> None:
        self._device = device      # a device to send the commands
        self._interface = prefix_interface(device, ":TRIG") # a prefixed interface to send timebase commands with ":TIM" prefix
    


    def mode(self, mode = None) -> str:
        
        if mode == None:    # no parameter: Check state
            return str( self._interface.ask(":MODE?") ).upper()    # uppercase conversion is unnecessary
        
        mode_commands = {
            "EDGE":"EDGE",
            "PULSE":"PULS",
            "VIDEO":"VIDEO",
            "SLOPE":"SLOP",
            "PATTERN":"PATT",
            "DURATION":"DUR",
            "ALTERNATION":"ALT"
        }
        mode = str(mode).upper()

        if not mode in [*mode_commands.keys()]:  # check for invalid keyword
            return log.error("%s, Trigger: Cannot assign \"%s\" as mode, must be one of the following values: %s"%(self._device, mode, [*mode_commands.keys()]))
        
        self._interface.write( ":MODE %s"%( mode_commands[mode] ) )





class measure:  # a class to ask for all the measurement values and access the measurement menu on the scope

    # there is a list of valid measurement commands
    # implementing them as a global variable would give the user the possibility to change them
    # therefore this list is a private variable in this class
    _valid_commands = [
            "VPP",      # Peak-Peak-Value 
            "VMAX",     # maximum value 
            "VMIN",     # minimum value
            "VAMP",     # amplitude
            "VTOP",     # top value
            "VBAS",     # bottom value
            "VAV",      # average value
            "VRMS",     # root-mean-square
            "OVER",     # overshoot
            "PRES",     # preshoot
            "FREQ",     # frequency
            "RIS",      # rising time
            "FALLT",    # falling time
            "PER",      # period
            "PWID",     # positive pulse width
            "NDIW",     # negative pulse width
            "PDUT",     # positive duty cycle
            "NDUT",     # negative duty cycle
            "PDEL",     # rising edge delay
            "NDEL"      # falling edge delay
        ]

    _device = None     # the oscilloscope » talk to this interface
    _interface = None  # the prefix-interface to talk to this device
    _Num_Chanels = None    # the amount of input chanels on the scope



    def __init__(self, device : None, num_chanels : int) -> None:
        self._device = device      # a device to send the commands
        self._interface = prefix_interface(device, ":MEAS") # a prefixed interface to send measurement commands with ":MEAS" prefix
        self._Num_Chanels = num_chanels
    


    # clears all current measurements visible on the screen
    def clear(self) -> None:
        self._interface.write(":CLE")
    


    # get / set the state of the total measurement information on the screen
    # no parameter -> get state: Is it visible or not?
    #              -> function returns bool(True) or bool(False)
    # parameter state -> can be bool(True) or bool(False) and displays the measurement information or hides it
    def total(self, state : bool = None) -> bool:

        if state == None:    # no parameter: Check state
            # Option activated -> Scope returns 'ON'
            # Option deactivated -> Scope returns 'OFF'
            return {"ON":True, "OFF":False}[ self._interface.ask(":TOT?").upper() ]   # Uppercase conversion just in case something is transmitted wrong
        
        if not state in [True, False]:  # the parameter must be bool(True) or bool(False). Otherwise throw error.
            return log.error("%s, Measure: Cannot assign \"%s\" for Total measurement info screen, must be bool(True) or bool(False)"%(self._device, state))

        self._interface.write(":TOT %s"%({True:"ON", False:"OFF"}[state] ))   # type conversion without any problem, send signal to scope
    


    # get / set the source for the measurement operations
    # no parameter: get the source, Chanel Number of type int()
    # parameter source: set measurement source to chanel number int(source)
    #                   start counting chanels from 0
    def source(self, source : int = None) -> int:
        
        if source == None:
            # the scope returns the strings "CH1", "CH2", ...
            # these will be parsed into integer numbers by removing the first two letters
            return int( self._interface.ask(":SOUR?")[2:] ) - 1
        
        if ( source < 0 ) or (source > (self._Num_Chanels - 1) ):
            return log.error("%s, Measure: Invalid Chanel number for source selection, must be between 0 and %s. %s is not in this range"%(self._device, self._Num_Chanels, source - 1))
        
        self._interface.write(":SOUR CHAN%i"%(source + 1))
    


    # get / set counter state
    # No parameter -> return information os requested option
    #              -> return bool(True)  » activated
    #              -> return bool(False) » deactivated
    # Parameter question: bool(True) | bool(False) -> activated | deactivated
    def counter_state(self, state : bool = None) -> bool:

        if state == None:    # no parameter: Check state
            # Option activated -> Scope returns 'ON'
            # Option deactivated -> Scope returns 'OFF'
            self._device.write(":COUN:ENAB?" )
            return { "ON":True, "OFF":False } [ str( self._device.read() ).upper() ]   # Uppercase conversion is unnecessary
        
        if not state in [True, False]:  # the parameter must be bool(True) or bool(False). Otherwise throw error.
            return log.error("%s, Measurement: Cannot assign \"%s\" for counter_enable, must be bool(True) or bool(False)"%(self._device, state))

        self._device.write(":COUN:ENAB %s"%( {True:"ON", False:"OFF"}[state] ))   # type conversion without any problem, send signal to scope
    


    # get the value from the internal frequency counter
    # the unit of the value is Hz
    # Attention: This sends a :COUNter command, not a :MEASurement command
    def counter(self) -> float:
        self._device.write(":COUN:VALue?") # it only works with ":VALue" but not with ":VAL"
        return float( self._device.read() )
    


    # get measurement values from the oscilloscope:
    # @param measure: string or list of strings with measurement queries
    #                 the measurement queries can be looked up in the list self._valid_commands
    # @param chanel: integer or list of integers with chanel numbers
    # @return: a single measurement value if len(measure) == 1 and @len(chanel) == 1
    #          or a list if multiple measurement values should be collected ( len(measurement) > 1 and @len(chanel) == 1 )
    #          or a list if multiple source chanels have been selected ( len(measure) == 1 and @len(chanel) > 1 )
    #          or a two dimensional list if multiple measurement queries and multiple source chanels have been selected ( len(measure) > 1 and @len(chanel) > 1 )
    #             |- the first dimension is the selected chanel from the list of source chanels (@param chanel)
    #             \- the second dimension is the list of measurement queries
    def measure(self, measure : Union[str, list], chanel : Union[int, list] = None) -> Union[float, list]:

        # first: check how many chanels have been passed as arguments
        if chanel != None:
            
            # convert chanel to a list
            if type(chanel) in [list, tuple, set, frozenset, np.ndarray]:
                chanel = list(chanel)
                
                # check wether all values are integer or float type:
                for i in range( len(chanel) ):
                    if type(chanel[i]) in [int, float]:
                        chanel[i] = int( chanel[i] )    # convert all floats to int
                    
                    # if there is something witch is not an int or a float: error
                    else:
                        return log.error("%s, Measure: Chanel number at index %i must be an integer or a float"%(self._device, i))

            # chanel can also be a single integer
            elif type(chanel) in [int, float]:
                chanel = [ int(chanel) ]

            # error if chanel is not the right data type
            else:
                return log.error("%s, Measure: Chanel has a value which does not match the required data types, must be one if the following: [int, float, tuple, set, frozenset, numpy -> ndarray]"%(self._device))
        # from here on, the variable chanel is either None or a list with at least one chanel number


        
        # if the measurement value is a single string: convert to a list with this single entry
        if type(measure) == str:
            measure = [measure]
        
        # if the measurement value is an array: check for every single entry in the array if it is a string
        elif type(measure) in [list, tuple, set, frozenset, np.ndarray]:
            measure = list(measure) # convert to list

            # check for every single query wether it is a string
            for i in range( len(measure) ):
                if not type(measure[i]) == str:
                    return log.error("%s, Measure: Measurement query at index %i must be a string"%(self._device, i))
        
        # if it is none of them: error
        else:
            return log.error("%s, Measure: Measurement query has a value which does not match the required data types, must be one if the following: [str, list, tuple, set, frozenset, numpy -> ndarray]"%(self._device))
        # data check done: the variable measurement is a list of strings with at least one entry



        # if a chanel or multiple chanels have been specified: get chanel count to iterate over all the chanels.
        # if no chanel was specified: set chanel count to 1 to iterate over the default source.
        chanel_len = 1 if chanel == None else len(chanel)

        # get the length of the amount of measurement queries to iterate over all of them
        measure_len = len(measure)

        # before running the loops to ask for all measurement queries: Create multi dimensional array to store return values
        Return = [ [ None for j in range(measure_len) ] for i in range(chanel_len) ]


        # start iterating over all the chanels
        for i in range( chanel_len ):

            # check chanel value at index i
            if chanel == None:
                # no chanel has been specified as a parameter for this function -> set chanel selector for this loop iteration to None
                chan_sel = None

            # else: a chanel has been specified: check wether the value is in the correct range.
            else:
                chan_sel = chanel[i]
                if ( chan_sel < 0 ) or (chan_sel > (self._Num_Chanels - 1) ):
                    return log.error("%s, Measure: Invalid Chanel number at index %i must be between 0 and %s. %s is not in this range"%(self._device, i, self._Num_Chanels - 1, chan_sel))
            # the value of chan_sel is now a valid chanel number or None
            


            # iterate over all the measurement queries
            for j in range(measure_len):
                
                # check wether value at index [i] is a valid scpi command
                measure[j] = str( measure[j] ).upper()  # uppercase conversion in case someone ape used a lowercase letter

                if not measure[j] in self._valid_commands:
                    return log.error("%s, Measure: Measurement query at index %i is not a valid query, must be one of the following: %s"%(self._device, j, self._valid_commands))

                # the scpi command where the index [j] is pointing to is a valid SCPI command » ask for the measurement value and store it in the array of return values
                answer = self._interface.ask(
                    ":%s?"%( measure[j] )                                           # send command
                    + ( " CHAN%i"%(chan_sel + 1) if (not chan_sel == None) else "") # if chanel number specified: add chanel number to the command
                )

                # if them measurement can't be done because there is no data on this chanel the scope will return '********'
                Return[i][j] = None if '*' in answer else float(answer)
        
        # now all measurement values should be collected
        # if only one measurement value has been collected: remove the list wrapper from the single response
        for i in range( chanel_len ):
            if len( Return[i] ) == 1:
                Return[i] = Return[i][0]    # remove list wrapper by initializing list with first entry
        
        # and now the same with the chanels: if there was only one chanel: remove the list wrapper over all the chanels
        if len( Return ) == 1:
            Return = Return[0]
        
        # all work is done: return measurement results
        return Return





class display:  # a class to control the scope display
    
    
    _device = None     # the oscilloscope » talk to this interface
    _interface = None  # the prefix-interface to talk to this device



    def __init__(self, device : None) -> None:
        self._device = device      # a device to send the commands
        self._interface = prefix_interface(device, ":DISP") # a prefixed interface to send timebase commands with ":DISP" prefix



    # I am tired of writing every function in nearly the same was so I am trying to replace nearly all of them with this monster. Just trying it in this class.
    # give it a scpi command for a scpi option that can be set to a certain value or where wou can ask for the current setting
    # if the parameter 'send' is None -> ask for the current setting. Otherwise set it to the value of 'send'
    # a list of valid values for the 'send' parameter has to be passed to the function. This function checks wether the value of 'send' is in the list
    # \_ furthermode a dictionary can be used and the function checks wether the value of 'send' is a key in the dictionary
    def _query(self, scpi_command : str, send : str = None, send_allowed_values : str = None, err_info : str = None) -> str:
        
        # if nothing has to be send: ask for the value of the scpi parameter and return answer
        # all answers will be converted to uppercase to make sure that they all work the same way
        if send == None:
            return str( self._interface.ask(scpi_command + "?") ).upper()

        # if the function reaches until here then some commands have to be set
        # first: make sure that everything is working properly by parsing the parameter to uppercase
        #   this is not necessary but good if someone used lowercase letters because the don't know better
        send = str( send ).upper()

        # check wether the send command is in a list of allowed commands. If this isn't the case: display an error message
        # this whole process depends on wether the allowed list of commands is a dictionary with matching SCPI values or an array
        if type( send_allowed_values ) == dict:
            
            # check wether the value is accepted
            if not send in [ *send_allowed_values.keys() ]:
                return log.error("%s, Display: Cannot assign \"%s\" as %s, must be one of the following values: %s"%(self._device, send, err_info, [ *send_allowed_values.keys() ]))
            else:
                self._interface.write( "%s %s" % (scpi_command, send_allowed_values[send]) )

        elif type( send_allowed_values ) == list:
            
            # check wether the value is accepted
            if not send in send_allowed_values:
                return log.error("%s, Display: Cannot assign \"%s\" as %s, must be one of the following values: %s"%(self._device, send, err_info, send_allowed_values))
            else:
                self._interface.write( "%s %s" % (scpi_command, send) )

        else:
            log.error("Display -> _query(): The allowed values are neither a list nor a dictionary.")



    # get / set display type
    # no parameter -> get type
    #                 oscilloscope returns values 'VECTORS' or 'DOTS'
    # parameter mode -> set display type to 'mode' which can be: (uppercase / lowercase invariant)
    #                   - "VECTORS"
    #                   - "DOTS"
    def type(self, mode : str  = None) -> str:
        return self._query(
            ":TYPE",
            mode,
            {
                "VECTORS" : "VECT",     # vectors displayed
                "DOTS" : "DOTS"         # dots displayed
            },
            "type"
        )
        



    # get / set grid state
    # no parameter -> get state
    #                 oscilloscope returns values 'FULL', 'HALF' or 'NONE'
    #                   FULL -> background grid and coordinates
    #                   HALF -> display coordinates and turn the grid off
    #                   NONE -> no grid and no coordinates
    # parameter mode -> set display type to 'mode' which can be: (uppercase / lowercase invariant)
    #                   - 'FULL'
    #                   - 'HALF'
    #                   - 'NONE'
    def grid(self, mode : str = None) -> str:
        return self._query(
            ":GRID",
            mode,
            [
                "FULL",
                "HALF",
                "NONE"
            ],
            "Grid"
        )
    


    # get / set display persistence
    # no parameter -> get value ( bool(True) or bool(False) )
    # parameter state -> set Value to bool(True) or bool(False)
    def persistence(self, state : bool = None) -> bool:
        return self._interface.boolean_property(
            ":PERS",
            "ON",
            "OFF",
            "Display",
            "Persistence",
            state
        )
    


    # get / set the value for the display time for a menu
    # the number is the time how long the scope will wait until the menu will disappear
    # int(0) is the equivalent to "infinity"
    # no parameter: get value (int)
    # @parameter time: set display time of the menu to 'time' value
    def menu_time(self, time : int = None) -> int:
        
        if time == None:
            return {    # this is a pretty decent lookup table
                "1s":1,
                "2s":2,
                "5s":5,
                "10s":10,
                "20s":20,
                "Infinite":0
            }[self._interface.ask(":MNUD?")]
        
        time_values = {
            0 : "INF",  # infinite
            1 : 1,
            2 : 2,
            5 : 5,
            10 : 10,
            20 : 20
        }

        if not time in [ *time_values.keys() ]:
            return log.error("%s, Display: Cannot assign \"%s\" as Menu Display Time, must be one of the following values: %s"%(self._device, time, [ *time_values.keys() ]))
        
        self._interface.write(":MNUD %s"%(time_values[time]))
    


    # get / set status of menu
    # no parameter -> get value ( bool(True) or bool(False) )
    # parameter state -> set Value to bool(True) or bool(False)
    def menu_status(self, state : bool = None) -> bool:
        return self._interface.boolean_property(
            ":MNUS",
            "ON",
            "OFF",
            "Display",
            "Menu State",
            state
        )
    


    # clear the display
    # removes out of date waveforms
    # clears the screen during waveform persist
    def clear(self) -> None:
        self._interface.write(":CLE")
    


    # use _interface.ask() and _interface.write() method to ask a query for a value between 0 and 32
    # this will be used to ask for the value for the interface brightness and intensity
    # if parameter 'value' is set then the scpi parameter (scpi_comand) is set to 'value'
    # if 'value' remains None then the value for scpi_command will be asked from the device
    def _0_32_value(self, value : int = None, scpi_command : str = None, err_info : str = None) -> int:
        
        if value == None:
            return int( self._interface.ask(scpi_command + "?") )

        if not value in [ *range(33)]:
            return log.error("%s, Display: Cannot assign \"%s\" as %s, must be an integer between 0 and 32"%(self._device, value, err_info))
        
        self._interface.write("%s %i"%(scpi_command, value))
    


    # get / set grid brightness
    # no parameter -> return brightness, value from 0 to 32
    # parameter value between 0 and 32 -> set brightness to 'value'
    def brightness_grid(self, value : int = None) -> int:
        return self._0_32_value(value, ":BRIG", "Grid Brightness")
    


    # get / set waveform brightness
    # no parameter -> return brightness, value from 0 to 32
    # parameter value between 0 and 32 -> set brightness to 'value'
    def brightness_wave(self, value : int = None) -> int:
        return self._0_32_value(value, ":INT", "Waveform Brightness")





class acquire:  # a class to control all the options available via the "acquire" button


    _device = None     # the oscilloscope » talk to this interface
    _interface = None  # the prefixed interface to send acquire commands
    


    def __init__(self, device : None) -> None:
        self._device = device      # a device to send the commands
        self._interface = prefix_interface(device, ":ACQ") # a prefixed interface to send acquire commands with ":ACQ" prefix



    # get / set acquire type
    # no parameter: get type
    # parameter type: set type to 'NORM'(Normal), 'AVER'(Average) or 'PEAK'(Peak Detect)
    # returns: 'Normal', 'Average' or 'Peak detect'
    def type(self, type = None) -> str:
        
        if type == None:    # no parameter -> get Acquire type value
            return self._interface.ask(":TYPE?")
        
        # define alle the Acquire types
        ACQUIRE_TYPES : Final = ["NORM", "AVER", "PEAK"]
        
        
        if not type in ACQUIRE_TYPES:  # if value is not set correctly
            return log.error("%s, Acquire: Cannot assign \"%s\" as type, must be one of the following values: %s"%(self._device, type, ACQUIRE_TYPES))

        self._interface.write(":TYPE %s"%(type))



    # get / set acquire mode
    # no parameter: get type -> return value can be str("REAL_TIME") or str("EQUAL_TIME")
    # parameter mode: set type to "REAL_TIME" (Real time sampling) or "EQUAL_TIME" (Equivalent sampling time)
    # mode can be str("REAL_TIME") or str("EQUAL_TIME") (uppercase / lowercase invariant)
    def mode(self, mode = None) -> str:
        
        if mode == None:    # No Parameter -> Ask for ACQUIRE Type
            # Oscilloscope returns "REA_TIME" or "EQUAL_TIME"
            return str( self._interface.ask(":MODE?") ).upper()    # uppercase conversion is unnecessary
        
        mode = str(mode).upper()    # remove lowercase letters

        # define all Acquire Modes
        ACQUIRE_MODES   : Final = {
            "REAL_TIME"     : "RTIM", 
            "EQUAL_TIME"    : "ETIM"
        }
        
        if not mode in [*ACQUIRE_MODES.keys()]: # Check wether parameter mode is set to a valid value
            return log.error("%s, Acquire: Cannot assign \"%s\" as mode, must be one of the following values: %s"%(self._device, mode, [*ACQUIRE_MODES.keys()]))
        
        self._interface.write(":MODE %s"%( ACQUIRE_MODES[mode] ))
    


    # get / set average acquisition time
    # no parameter -> get value: int()
    # parameter: value in [2**N, n from 1 to 8]: set average value
    def average_time(self, value = None) -> int:
        
        if value == None:
            return int( self._interface.ask(":AVER?") )    # get parameter value and parse as integer
        
        average_values = [ 2**(i+1) for i in range(8) ] # generate an array with all acceptale values for the acquire average

        if not value in average_values: 
            return log.error("%s, Acquire: Cannot assign \"%s\" as average value, must be one of the following values: %s"%(self._device, value, average_values))
        
        self._interface.write(":AVER %i"%(value))
    


    # get sampling rate only for DIGITAL
    # this is only a getter
    # Alternative: CHANel<i> -> samplingrate() gets the sampling rate for every single chanel
    # this function only asks for sampling rate for DIGITAL
    # see programming manual page 20 (2-8)
    def samplingrate(self) -> float:
        return float( self._interface.ask(":SAMP? DIGITAL") )
    


    # get / set Memory Depth
    # no parameter -> get Mem Depth, function returns "LONG" or "NORMAL"
    # parameter value is "LONG" or "NORMAL" ->Set Bandwith
    def mem_depth(self, value = None) -> float:
        
        if value == None:
            return str( self._interface.ask(":MEMDepth?") ).upper()
        
        MEMD_DICT = {
            "LONG" : "LONG",
            "NORMAL" : "NORM"
        }

        value = str(value).upper()

        if not value in [ *MEMD_DICT.keys() ]:
            return log.error("%s, Acquire: Cannot assign \"%s\" as Memory Depth, must be one of the following values: %s"%(self._device, value, [*MEMD_DICT.keys()]))
        
        self._interface.write(":MEMDepth %s"%( MEMD_DICT[value ] ))





class math:  # interface to all the options available via the "Math" button


    _device = None     # the oscilloscope » talk to this interface
    _interface = None  # the prefixed interface to send acquire commands
    


    def __init__(self, device : None) -> None:
        self._device = device      # a device to send the commands
        self._interface = prefix_interface(device, ":MATH") # a prefixed interface to send math commands with ":MATH" prefix
    


    # turn Math operations on / off or ask for current state
    # no parameter -> return current state which can be bool(True) or bool(False)
    # parameter state: set to value of 'state' which can be bool(True) or bool(False)
    def display(self, state : bool = None) -> bool:

        if state == None:    # no parameter: Check state
            # Option activated -> Scope returns 'ON'
            # Option deactivated -> Scope returns 'OFF'
            return {"ON":True, "OFF":False}[ self._interface.ask(":DISP?").upper() ]   # Uppercase conversion just in case something is transmitted wrong
        
        if not state in [True, False]:  # the parameter must be bool(True) or bool(False). Otherwise throw error.
            return log.error("%s, Math: Cannot assign \"%s\" for Display, must be bool(True) or bool(False)"%(self._device, state))

        self._interface.write(":DISP %s"%({True:"ON", False:"OFF"}[state] ))   # type conversion without any problem, send signal to scope
    


    # get / set mode for math operation
    # no parameter -> get mode can be either '+', '-', '*' or 'FFT'
    # parameter 'mode' is '+', '-', '*' or 'FFT' -> set math operation to 'mode'
    def mode(self, mode : str = None):
        
        if mode == None:    # no parameter: Check state
            return {
                "A+B":"+",
                "A-B":"-",
                "A*B":"*",
                "FFT":"FFT"
            }[ self._interface.ask(":OPER?") ]
        
        mode_dict = {
            "+":"A+B",
            "-":"A-B",
            "*":"AB",
            "FFT":"FFT"
        }

        mode = str( mode ).upper()  # remove lowercase letters for the dictionary

        if not mode in [ *mode_dict.keys() ]:
            return log.error("%s, Math: Cannot assign \"%s\" as mode, must be one of the following values: %s"%(self._device, mode, [*mode_dict.keys()]))
        
        self._interface.write(":OPER %s"%( mode_dict[mode] ))



    # turn FFT on / off or ask for current state
    # no parameter -> return current state which can be bool(True) or bool(False)
    # parameter state: set to value of 'state' which can be bool(True) or bool(False)
    # Attention: This sends an ":FFT" command, not a ":MATH" command
    def fft(self, state : bool = None) -> bool:

        if state == None:    # no parameter: Check state
            # Option activated -> Scope returns 'ON'
            # Option deactivated -> Scope returns 'OFF'
            # send an ":FFT" command » cannot use self._interface
            self._device.write(":FFT:DISP?")
            return {"ON":True, "OFF":False}[ self._device.read().upper() ]   # Uppercase conversion just in case something is transmitted wrong
        
        if not state in [True, False]:  # the parameter must be bool(True) or bool(False). Otherwise throw error.
            return log.error("%s, Math: Cannot assign \"%s\" for FFT, must be bool(True) or bool(False)"%(self._device, state))

        self._interface.write(":FFT:DISP %s"%({True:"ON", False:"OFF"}[state] ))   # type conversion without any problem, send signal to scope
    


    # TODO: implement function, this is just here as a placeholder
    def waveform(self):
        raise NotImplementedError
    


    # TODO: implement function, this is just here as a placeholder
    def fft_waveform(self):
        raise NotImplementedError





class logic_analyzer: # interface to the Logic Analyzer options

    _device = None     # the oscilloscope » talk to this interface
    _interface = None  # the prefixed interface to send acquire commands
    


    def __init__(self, device : None) -> None:
        self._device = device      # a device to send the commands
        self._interface = prefix_interface(device, ":LA") # a prefixed interface to send math commands with ":LA" prefix
    


    # get / set logic analyzer activity or visibility
    # no parameter -> get current state ( bool(True) or bool(False) )
    # @parameter state: set state
    #                   - True -> Logic Analyzer active
    #                   - False -> Logic Analyzer inactive
    def display(self, state : bool = None) -> Union[None, bool]:
        return self._interface.boolean_property(
            ":DISP",
            "ON",
            "OFF",
            "Logic Analyzer",
            "Logic Analyzer Display",
            state
        )
    


    # TODO: implement function, this is just here as a placeholder
    def waveform(self):
        raise NotImplementedError





class keys: # interface to press a key

    _keys = {  # key names and their names in the scpi command set 
        "RUN"           : "RUN",                # Run / Stop
        "AUTO"          : "AUTO",               # Auto

        # The Chanel keys are generated during initialization from the available number of chanels

        "MATH"          : "MATH",               # Math
        "REF"           : "REF",                # Ref

        # The F1, F2, ... Keys are generated in a loop below this dictionary

        "MENU"          : "MNU",                # Menu On Off
        "MEASURE"       : "MEAS",               # Measure
        "CURSOR"        : "CURS",               # Cursor
        "ACQUIRE"       : "ACQ",                # Acquire
        "DISPLAY"       : "DISP",               # Display
        "STORAGE"       : "STOR",               # Storage
        "UTILITY"       : "UTIL",               # Utility
        "TIME"          : "MNUTIME",            # Time Menu
        "TRIGGER"       : "MNUTRIG",            # Trigger Menu
        "TRIG50%"       : "Trig%50",            # Trigger 50%
        "FORCE"         : "FORC",               # Force local

        "VP_PUSH"       : "PROMPT_V_POS",       # Push the Vertical Position Knob
        "VP+"           : "V_POS_INC",          # increment vertical offset of currently selected chanel, "VP" stands for "Vertical Position"
        "VP-"           : "V_POS_DEC",          # decrement ↑

        "VS_PUSH"       : "PROMPT_V",           # Push the Vertical Scale Knob
        "VS+"           : "V_SCALE_INC",        # increment vertical scale of currently selected chanel, "VS" stands for "Vertical Scale"
        "VS-"           : "V_SCALE_DEC",        # decrement ↑

        "HP_PUSH"       : "PROMPT_H_POs",       # Push the Horizontal Position Knob
        "HP+"           : "H_POS_INC",          # increment horizontal offset of timebase, "HP" stands for "Horizontal Position"
        "HP-"           : "H_POS_DEC",          # decrement ↑

        "HS_PUSH"       : "PROMPT_H",           # Push the Horizontal Scale Knob
        "HS+"           : "H_SCALE_INC",        # increment horizontal scale of timebase, "HS" stands for "Horizontal Scale"
        "HS-"           : "H_SCALE_DEC",        # decrement ↑

        "T_PUSH"        : "PROMPT_TRIG_LVL",    # Push the Trigger level Knob
        "T+"            : "TRIG_LVL_INC",       # increment Trigger Level
        "T-"            : "TRIG_LVL_DEC",       # decrement ↑

        "FUNCTION"      : "FUNC",               # Multi-Function Knob
        "FUNCTION+"     : "+FUNC",              # increase ↑
        "FUNCTION-"     : "-FUNC",              # decrease ↑

        "LA"            : "LA",                 # logic analyzer
        "OFF"           : "OFF"                 # this command turns off the CH1, CH2, MATH, REF and LA chanels one by one through sending the command continuosly
    }
    # add the F1, F2, ... Keys via a loop
    _max_F = 5
    _keys.update( { "F%i"%(i + 1) : "F%i"%(i + 1) for i in range(_max_F) } )


    _device = None     # the oscilloscope » talk to this interface
    _interface = None  # the prefixed interface to send acquire commands
    


    def __init__(self, device : None, num_chanels : int) -> None:
        self._device = device      # a device to send the commands
        self._interface = prefix_interface(device, ":KEY") # a prefixed interface to send math commands with ":KEY" prefix

        # generate the dictionary from the number of chanels
        self._keys.update( { "CHANEL%i"%(i + 1) : "CHAN%i"%(i + 1) for i in range(num_chanels)} )


    # get / set key lock state
    # no parameter -> get current state
    #                   - bool(True)  » keys are locked
    #                   - bool(False) » keys are not locked
    # @parameter state -> set lock state to value of state
    #                   - bool(True)  » lock keys
    #                   - bool(False) » unlock keys
    def lock(self, state : bool = None) -> Union[bool, None]:

        if state == None:   # no parameter -> get state
            return {        # convert from "ENABLE" | DISABLE to bool(True) | bool(False)
                "ENABLE" : True,
                "DISABLE" : False
            } [ str( self._interface.ask(":LOCK?") ).upper() ]

        if not type(state) == bool:
            return log.error("%s, Keys: Cannot assign \"%s\" as locking state, must be bool(True) or bool(False)"%(self._device, state))
        
        self._interface.write(":LOCK %s"%( {
            True : "ENAB",
            False : "DIS"
        }[state] ))
    


    # press a button on the oscilloscope
    # @parameter key: a key on the oscilloscope from the following list: self._keys
    def press(self, key):
        
        if not type(key) == str:
            return log.error("%s, Keys -> press(): parameter must be of type String and not %s"%(self._device, str( type(key) )))
        
        key = key.upper()   # uppercase conversion because all keys in the key dictionary are written in uppercase
        
        if not key in [ *self._keys.keys() ]:
            return log.error("%s, Keys: \"%s\" is not a valid Key name, must be one of the following: %s"%(self._device, key, [ *self._keys.keys() ]))
        
        self._interface.write( ":%s"%( self._keys[key] ) )





class DS1000_Generic:


    _Num_Chanels = None    # the number of analog signal input chanels
    
    _device = None      # the interface on which the device is attached to
    Chanels = None      # the chanels of the oscilloscope
    Acquire = None      # access to the menu available via the "Acquire" button
    Timebase = None     # access to the menu which is relevant to set the oscilloscope timebase
    Trigger = None      # access to the menu of the Trigger
    Display = None      # access to the scope display
    Math = None         # access to the menu for the Math Options
    Measurement = None  # access to the measurement options and the values    
    Keys = None         # access to the keys


    def __init__(self, num_chanels : int, USB_DEVICE : str = '') -> None:
        
        self._Num_Chanels = num_chanels    # store the number of Chanels


        rm = visa.ResourceManager('@py')    # get the list of USB devices
                                            # The '@py' string tells the resource manage rto look for pyvisa library.
                                            # this works better than the ni-visa library
                                            # without this parameter it will use the ni-visa library
        devices = rm.list_resources()       # try to find the instrument


        device_init = False     # no device has been initialized yet
        
        
        # now we start looking for our oscilloscope in the list of visa compatible devices
        # If a device has beenspecified: Try to find the first specified device in the list of devices
        if USB_DEVICE != '':
            for i in range(len(devices)):
                if USB_DEVICE in str(devices[i]):    # the specified string is in the name of the device
                    self._device = rm.open_resource( devices[i] )  # device found
                    device_init = True
                    break                       # no need to run this loop any more

        
        # if no device was specified or the device cannot be found: ask for a device in the list from the comand line
        if device_init == False:

            # print a status message to inform the user about the current situation
            if USB_DEVICE == '':
                print("No USB device has been specified.")
            else:
                print("The specified device cannot be found in the list of available devices.")
            

            # now ask for a device from the list of devices
            while device_init == False:
                print("Please select the Oscilloscope from the list of available devices:")
                for i in range( len(devices) ):
                    print("%i: %s"%(i + 1, devices[i]))
                
                dev_index = int( input() ) - 1

                # just check weather the user input makes sense
                if (dev_index < 0) or (dev_index >= len(devices)):
                    log.error("Invalid number. Please try it again.")
                else:
                    self._device = rm.open_resource( devices[dev_index] )
                    device_init = True


        # first step: stop the scope
        self.write(":STOP")


        # initialise interfaces to submenus:
        self.Acquire = acquire(self._device)
        self.Timebase = timebase(self._device)
        self.Chanels = [ chanel(i + 1, self._device, self.Timebase) for i in range(self._Num_Chanels) ]       # (i + 1) because Rigol starts counting chanels from 1
        self.Trigger = trigger(self._device)
        self.Display = display(self._device)
        self.Math = math(self._device)
        self.Measurement = measure(self._device, self._Num_Chanels)
        self.Keys = keys(self._device, self._Num_Chanels)

        ## everything done: the oscilloscope is initialized



    def _close(self) -> None:  # close the oscilloscope. This function will only be called by the destructor
        self._device.close()   # use visa close command



    def __del__(self) -> None:
        self._close()  # close the oscilloscope before deleting it



    def __repr__(self) -> str:
        return self.__str__()



    def __str__(self) -> str:   # crete a string if someone does some weird type conversion or wants to print this object on the command line
        return "Oscilloscope %s"%(self._device)

    

    def write(self, command) -> None:    # write a VISA command to the scope
        self._device.write(command)



    def read(self) -> str:  # read the result from a command send to the scope
        return self._device.read()
    


    def read_raw(self) -> str:  # read the result from a command send to the scope
        return self._device.read_raw()



    def ask(self, command) -> str:  # send a command to the scope and get the answer
        self.write(command)
        return self.read()
    


    def ask_raw(self, command) -> str:  # send a command to the scope and get the answer
        self.write(command)
        return self.read_raw()



    def reset(self) -> None:
        self.write("*RST") # IEEE488 Query to perform device reset
    


    def device_info(self) -> None:
        self.write("*IDN?")    # IEEE488 Query to ask for device info
        return self.read_raw().splitlines()[0]  # only return first line from answer



    def run(self) -> None:      # run measurement
        self.write(":RUN")
    


    def stop(self) -> None:     # stop measurement
        self.write(":STOP")
    


    def auto(self) -> None:     # auto-scale
        self.write(":AUTO")
        


    def hard_copy(self) -> None:    # Store current waveform on internal memory. Waveform can be recalled. I don't know more about this function but you can look it up at the programming manual on page 17
        self.write(":HARDcopy")


    
    # get / set scope language
    # no parameter -> get scope language
    # @parameter lang: set language
    def language(self, lang : str = None) -> str:
        
        if lang == None:    # no parameter -> ask for current value
            return str( self.ask(":INFO:LANG?") ).upper() # remove lowercase letters
        
        lang = str( lang ).upper()  # remove lowercase letters in language names

        known_lang = {
            "SIMPLIFIEDCHINESE" : "SIMPC",
            "TRADITIONALCHINESE" : "TRADC",
            "ENGLISH" : "ENGL",
            "KOREAN" : "KOR",
            "JAPANESE" : "JAP",
            "FRENCH" : "FREN",
            "GERMAN" : "GERM",
            "RUSSIAN" : "RUSS",
            "SPANISH" : "SPAN",
            "PORTUGUESE" : "PORT"
        }

        if not lang in known_lang:
            return log.error("%s, Language: Cannot assign \"%s\", must be one of the following values: %s"%(self._device, lang, [*known_lang.keys()]))
        
        self.write( ":INFO:LANG %s"%( known_lang[ lang ] ) )
    


    def beep(self) -> None:
        self.write(":BEEP:ACT")
    


    # get / set the state for an acoustic feedback
    # No parameter -> return information os requested option
    #              -> return bool(True)  » activated
    #              -> return bool(False) » deactivated
    # @parameter question: bool(True) | bool(False) -> activated | deactivated
    def feedback(self, state : bool = None) -> bool:
        
        if state == None:   # no parameter specified -> ask for current state
            # Option activated -> Scope returns 'ON'
            # Option deactivated -> Scope returns 'OFF'
            return {
                "ON" : True,
                "OFF" : False
            } [ str( self.ask( ":BEEP:ENAB?" ) ).upper() ]
    
        if not state in [True, False]:  # the parameter must be bool(True) or bool(False). Otherwise throw error.
            return log.error("%s, acoustic feedback: Cannot assign \"%s\", must be bool(True) or bool(False)"%(self._device, state))
        
        self.write( ":BEEP:ENAB %s"%( {True:"ON", False:"OFF"}[state] ) )



    # perform a factory reset
    # @parameter quiet -> optional only perform the reset and do not ask in the command line wether the user really wants to do that
    def factory_reset(self, quiet : bool = False) -> None:

        assert type(quiet) == bool  # no error messsage on this point because the user should be knowing what he is doing!

        if not quiet:
            ReallyDoThat = input("Are you sure you really want to perform a factory reset?[y/N]")

            if not ReallyDoThat in ["Y", "y"]:
                print("Aborted")
                return
            else:
                print("Accepted")
        
        self.write(":STORage:FACTory:LOAD")   # Attention: this command has not been tested, I never wanted to perform a default reset on my device
    


    '''
    # ? Temporatily disabled because there is no use-case for this as long as there actually is only the option to get chanel waveform
    # TODO: implement all the rest and then re-enable this functions.
    # Also: instaead of strings, the waveform-Capture function could take references to the scope chanels / Math_objects / logic Analyzer...
    #    \_ there should be an fft object in the scope 

    
    # get / set waveform mode
    # mode must be one of the followings: 
    def waveform_mode(self, mode : str = None) -> Union[str, None]:
        
        # no parameter -> ask for current setting in the device
        if mode == None:
            return self.ask(":WAV:POIN:MODE?")
        
        # check wether parameter is a valid value
        mode = str(mode).upper()

        modes = {
            "NORMAL" : "NOR",
            "RAW" : "RAW",
            "MAXIMUM" : "MAX"
        }

        if not mode in [ *modes.keys() ]:
            return log.error("%s: Waveform-Mode: Cannot assign \"%s\" as mode, must be one of the followings: %s"%(self._device, mode, [ *modes.keys() ]))
        
        self.write(":WAV:POIN:MODE %s"%( modes[mode] ))



    # get waveform data
    # @parameter source: a string for waveform source or a list of waveform sources
    #                    Waveform source, can be one of the followig:
    #                    |_ "CHx" where x is a number between 0 and (self._Num_Chanels - 1)
    #                    |_ "MATH" for Math Chanel
    #                    |_ "FFT" for fourier transformation data
    #                  ( \_ Digital for logic analyzer chanel )
    # @parameter mode: optional, can set a capturing mode.
    #                  \_ function calls self.waveform_mode() with this parameter
    # return: numpy-array of waveform data with [time, data] pairs or jist a single pair if there is only one entry in the list
    def waveform(self, source : Union[str, list], mode : str = None) -> np.ndarray:

        # set waveform mode to the parameter value
        if not mode == None:
            self.waveform_mode(mode)

        
        # first: check wether source parameter is valid

        # list of possible sources and the functions that they call
        possible_sources = {}
        """
        # Math, FFT and Digital have been disabled because they're not implemented yet
        # TODO: implement these functions and re-enable the following options
        # at first: MATH and FFT
        possible_sources = {
            "MATH" : self.Math.waveform,
            "FFT" : self.Math.fft_waveform,
        }

        # if digital Chanel is available: also generate digital chanel
        if hasattr(self, 'Logic'):
            possible_sources.update( {"LOGIC" : self.Logic.waveform } )
        """
        
        # add singel chanels according to the amount of chanels
        possible_sources.update( { "CH%i"%(i) : self.Chanels[i].waveform for i in range( self._Num_Chanels) } )



        # check data type of the source parameter
        if type(source) == str: # if string: convert to list with single entry
            source = [source]
        
        elif type(source) == list:
            # list -> check wether every entry is a string
            for i in range(len(source)):
                # if the current focused value in the list is not a string: throw an error
                if not type( source[i] ) == str:
                    return log.error( "Waveform-Capture: source index %i must be of type string" % (i) )
        else: # error: neither a list or a string
            return log.error("Waveform-Capture: source must be of type string or list of strings")


        # the type checking is done
        # check for right values in the entries of the list
        for i in range(len(source)):
            if not source[i].upper() in [ *possible_sources.keys() ]:
                log.error( "Waveform-Capture: source index %i: \"%s\" is not a valid keyword, must be one of the following: %s" % (i, source[i], [ *possible_sources.keys() ]) )
            else:   # if it is a keyword: perform an uppercase conversion to prevent errors comming from lowercase letters in the list pf keywords
                source[i] = source[i].upper()
            
        # now all the entries in the source list are valid. The waveform capture process can be performed.

        Return = [ possible_sources[ i ]() for i in source ]

        return Return[0] if len(Return) == 1 else Return    # if only one [time, data] pair is in the list -> just return this pair
        '''





class DS1102E(DS1000_Generic):

    # initialise a generic DS1000 Scope with 2 chanels
    def __init__(self, USB_DEVICE: str = '') -> None:
        super().__init__(2, USB_DEVICE=USB_DEVICE)





class DS1102D(DS1000_Generic):

    # initialise a generic DS1000 Scope with 2 chanels
    def __init__(self, USB_DEVICE: str = '') -> None:
        super().__init__(2, USB_DEVICE=USB_DEVICE)

        # also initialize the logic analyzer
        self.Logic = logic_analyzer(self._device)





"""

 /\_/\  
( o o ) 
/  ˇ  \ 
| ::: | 
 \\ //  


--------
Credits:
--------

- Michael Hohenstein, michael@hohenste.in, https://spice-space.de/navigation/ueber-michi/



-------------------------
A little bit of research:
-------------------------

There are some trials documented to send a couple of SCPI commands which are not listed in the programming manual \
    ore some stuff we know from rigol software the scope can do but it isn't mentioned in the programming manual at all.


List of SCPI Commands that are not mentioned in the programmig manual and might be implemented in the future:

- :STOR:TYPE (?) » tested, works on this device
  \_ maybe there is an option to store data on the internal / external memory and do this via the scpi interface


- Hopefully there will be a SCPI command to send screenshots to the device
  \_ The DS1102z supports a screenshot with :DISP:DATA?
                                            |_ :DISP:DATA? [<color>,<invert>,<format>]
                                            |_ Color: {ON|OFF}
                                            |_ invert: { {1|ON} | {0|OFF} }
                                            \_ format: {BMP24|BMP8|PNG|JPEG|TIFF}
"""
