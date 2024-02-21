# -*- coding: UTF-8 -*-


### External library call ###
import numpy as np
import math
import logging
import global_param

# load global Parameters
GC = global_param.Global_Constant()
# GP = global_param.Global_Parameter()

# setup logger
logger = logging.getLogger('main.swap')
data_logger = logging.getLogger('data.swap')

######################################################################
####################### Class: Battery ###############################
######################################################################

class Battery:
    
    def __init__(self, soc, batterytype, target_max_soc = 1, target_min_soc=0, temperature = 25):
        '''
        Initializing the parameters in battery instance
        soc: double, state of charge: 0 -> empty; 1 -> full charged
        charge_limit: 8 * 13 matrix, tempurature -> current at limit_axis
        batterytype: string, indicate which type of batteries are chosen -> 70kWh, 100kWh, 75kWh
        support battery type: 
            1. 70kWh -> Large
            2. 75kWh -> Large
            3. 100kWh -> Large
            4. 40kWh -> Small
            5. 60kWh -> Small
        Note:   1-3 cannot combine with 4,5 -> not swapable
                if No Data avaiable, by default we use data from 100kWh
        '''
        self.charge_limit_100 = GC.charge_limit_100
        self.charge_limit_75 = GC.charge_limit_75
        self.charge_limit_70 = GC.charge_limit_70
        self.ocv_100 = GC.ocv_100
        self.ocv_70 = GC.ocv_70
        battery_charge_limit={  
            "70kWh": self.charge_limit_70,
            "75kWh": self.charge_limit_75,
            "100kWh": self.charge_limit_100,
            "40kWh": self.charge_limit_100,
            "60kWh": self.charge_limit_100
                            }
        self.battery_capacity = GC.battery_capacity                     # battery capacity [Ah]
        self.batterytype = batterytype                                  # string -> 70kWh, 100kWh, 75kWh..
        
        if batterytype in self.battery_capacity:
            self.capacity = self.battery_capacity[batterytype]          # Return the battery Ah number return int
            self.charge_limit = battery_charge_limit[batterytype]       # Return charging limit dict
        else:
            '''
            if No batteries type are found, return default setup (100kWh Batteries)
            '''
            print("No such battery type, using default type 100kWh")
            self.capacity = self.battery_capacity["100kWh"]
            self.charge_limit = battery_charge_limit["100kWh"]
        
        self.soc = soc
        self.set_temperature(temperature)                               # The default battery temperature is 25 degrees
        self.polar_r = 0.04                                             # Assuming 40 mohm, 0.04 ohm
        self.limit_axis = [0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95,] # soc limit values
        self.target_max_soc = target_max_soc
        self.target_min_soc = target_min_soc
        self.power_command = 0
        self.set_battery_voltage()
        self.calc_current_limit()
        self.power = 0
        self.current = 0

        self.charge_history = []                                        #Create a list according to {soc:???,voltage:???,current:???,temperature:???,timer:} to record the charging process of this battery during the simulation cycle
        self.charge_start_time = -1                                     #Record the time of t_timer, indicating when the battery started to be charged. -1 indicates that it has not been charged yet.
        self.charge_end_time = -1                                       #Record the time of t_timer, indicating when the battery stopped charging

    def battery_charge(self, current, timer, interval):
        # current is the charging current within small period of time, the time period defined as interval
        if self.charge_start_time == -1:
            self.charge_start_time = timer #If it has not been charged before, record the charging start time
        
        self.calc_current_limit() # calc the self.current_command
        if current > self.current_command:
            current = self.current_command
        
        self.soc = (self.soc * self.capacity + interval * current / 3600) / self.capacity

        if self.soc >= self.target_max_soc:
            self.soc = self.target_max_soc
            # self.charge_end_timer = timer #Charging termination, record the charging termination time. The charging termination here is the termination time under the defined charging pile charging situation. The charging termination SOC of the battery swap station is in the sr.power_distribution module.
        
        self.set_battery_voltage()

        self.power = self.battery_voltage * current / 1000.0 # return kWh
        temp = {"soc": self.soc, "voltage": self.battery_voltage, "current": current, "temperature": self.temperature, "timer": timer}
        self.charge_history.append(temp)
        self.current = current
        return

    ################################################################################

    def battery_discharge(self, current, timer, interval):
        '''
        perform the battery discharge behaviour
        '''
        if self.charge_start_time == -1:
            self.charge_start_time = timer # If it has not been charged before, record the charging start time
        # process 1: calculate the current
        self.calc_current_limit() # calc the self.current_command
        if current > self.current_command:
            current = self.current_command
        # process 2: calculate the soc status
        self.soc = (self.soc * self.capacity - interval * current / 3600) / self.capacity
        if self.soc < self.target_min_soc:
            self.soc = self.target_min_soc
        # process 3: calculate the voltage
        self.set_battery_voltage()
        # process 4: calculate the power (negative value means give the power out of the battery)
        self.power = (-1) * self.battery_voltage * current / 1000.0 # return kWh
        # process 5: log the data
        temp = {"soc": self.soc, "voltage": self.battery_voltage, "current": current, "temperature": self.temperature, "timer": timer}
        self.charge_history.append(temp)
        self.current = current

    def set_battery_voltage(self):
        '''
        ocv_100, ocv_70: battery open circuit voltage at each SOC value for 100 kWh and 70 kWh
        set the battery voltage of current time step according to the current_command
        '''
        cal_soc = self.soc
        if cal_soc < 0.05:
            cal_soc = 0.05
        if cal_soc > 1:
            cal_soc = 1
        cal_soc = int(cal_soc * 100) - 5 # maximal SOC = 96%, minimal SOC = 6%
        # set open circuit voltage under current soc value -> give it to battery_voltage
        if self.batterytype == "70kWh":
            
            self.battery_voltage = self.ocv_70[cal_soc]
            return
        else:
            
            self.battery_voltage = self.ocv_100[cal_soc]
            return

    def set_temperature(self, real_temperature):
        '''
        set the simulation temperature (closest to real temperature)
        '''
        test_temperature = [-20, -10, 0, 10, 20, 25, 30, 40]
        diff_min = abs(test_temperature[0] - real_temperature)
        temp = test_temperature[0]
        # find closet test temperature near the real temperature, use it as current temperature
        if isinstance(real_temperature, int):
            for t in test_temperature:
                diff = abs(t - real_temperature)
                if diff < diff_min:
                    temp = t
                    diff_min = diff
        self.temperature = temp
        return

    def calc_current_limit(self): 
        '''
        calculate the maximal current under the given SOC
        '''
        check_soc = self.soc
        if check_soc < 0.05:
            check_soc = 0.05
        if check_soc > 0.95:
            check_soc = 0.95
        if self.limit_axis.count(check_soc) > 0:
                   
            self.current_command = self.charge_limit[self.temperature][self.limit_axis.index(check_soc)]
            return

        for lim in self.limit_axis:
            if lim > check_soc:
                lim_index2 = self.limit_axis.index(lim)
                lim_index1 = lim_index2 - 1
                lim_num1 = self.limit_axis[lim_index1]
                lim_num2 = self.limit_axis[lim_index2]               
                # print("index1 = ",lim_index1,"index2 = ",lim_index2)
                # print("lim_current1 = ",self.charge_limit[temperature][lim_index1])
                # print("lim_current2 = ",self.charge_limit[temperature][lim_index2])
                # print("lim_soc1 = ",lim_num1)
                # print("lim_soc2 = ",lim_num2)
                cur_limit =(check_soc - lim_num1) * (self.charge_limit[self.temperature][lim_index2] - self.charge_limit[self.temperature][lim_index1]) / (lim_num2 - lim_num1)
                cur_limit = cur_limit + self.charge_limit[self.temperature][lim_index1]
                # print("Cur_limit = ",cur_limit)
                self.current_command = cur_limit 
                return

    def request_power(self, current_limit = -1):
        '''
        calculate the battery power output and return in [kW]
        '''
        self.calc_current_limit() # calc current_command
        self.set_battery_voltage() # calc battery_voltage
        if self.current_command > current_limit and current_limit > 0:
            self.current_command = current_limit
        self.power_command = self.battery_voltage * self.current_command / 1000.0
        return

######################################################################
####################### Class: Power_module ##########################
######################################################################

class Power_Module:
    def __init__(self, module, id):
        # Module parameters are entered using a dictionary, including maximum power and maximum current.
        self.max_power = module["max_power"]
        self.max_current = module["max_current"]
        self.line_resistance = 0.008 # 8 mohm
        self.id = id
        self.status = "free" # free & in_use
        # Defines the state of being connected to the battery compartment of the swap station 
        # or to an external charging pile
        self.link_to = 0 # 0 disconnect, Positive integer - battery compartment in the battery swap station, negative integer - charging pile
        self.power = 0
        self.output_voltage = 0
        self.output_current = 0

    def output_power(self, current_command, battery_voltage): 
        #Start charging, input the command current and current battery voltage, and return the output power and current according to the module characteristics.
        if self.link_to == 0:
            logger.info("forget to define the module output source")
            return
        if current_command > self.max_current:
            current_command = self.max_current
        expect_voltage = battery_voltage + current_command * self.line_resistance
        expect_power = expect_voltage * current_command / 1000.0 # return value in kW
        if expect_power <= self.max_power:
            self.output_current = current_command
            self.power = expect_power
            self.output_voltage = 1000.0 * self.power / self.output_current # return in Volt
            self.status = "in_use"
        else: # expect_power > max_power
            self.output_current = -1 * battery_voltage + math.sqrt(battery_voltage **2 + 4 * self.line_resistance * self.max_power * 1000)
            self.output_current = self.output_current / 2 / self.line_resistance
            self.power = self.max_power  
            self.output_voltage = 1000.0 * self.power / self.output_current
            self.status = "in_use"
        return
    
    ################################################################################
    ################################################################################
    def grid_interactive_output_power(self, current_command, battery_voltage): 
        '''
        calculate the power supply back to the grid according
        to the grid interaction order and voltage & current
        +1 positive power output means the bss charge the battery
        -1 negative power output means the bss discharge battery, send strom back to grid
        '''
        # power module should link to the battery in the swap rack
        if self.link_to <= 0:
            logger.info("Power module doesn't connect to battery in the rack. link_to = %d" %self.link_to)
            return
        # case: current should limited within upper limit
        if current_command > self.max_current:
            current_command = self.max_current
        
        expect_voltage = battery_voltage + current_command * self.line_resistance
        expect_power = expect_voltage * current_command / 1000.0            # return value in kW
        
        if expect_power <= self.max_power:
            self.output_current = current_command
            self.power = -1 * expect_power                                  # negative power output means back to grid
            self.output_voltage = 1000.0 * abs(self.power) / self.output_current # return in Volt
            self.status = "in_use"
        else: # expect_power > max_power
            self.output_current = -1 * battery_voltage + math.sqrt(battery_voltage **2 + 4 * self.line_resistance * self.max_power * 1000)
            self.output_current = self.output_current / 2 / self.line_resistance
            self.power = -1 * self.max_power  
            self.output_voltage = 1000.0 * abs(self.power) / self.output_current
            self.status = "in_use"
        return

    def stop_charge(self): #Stop charging
        self.power = 0
        self.output_current=0
        self.link_to = 0
        self.output_voltage = 0
        self.status = "free"

######################################################################
####################### Class: Power_Cabinet #########################
######################################################################

class Power_Cabinet:
    '''
    Define the arrangement of Cabinet
    Type - 1 Unmanned: 13 Power Modules with UU40kW
    Type - 2 Unmanned 600kWh: 10 Power Modules with UU60KW
    Type - 2 Unmanned 1200kWh: 20 Power Modules with UU60KW
    '''
    def __init__(self, station_type, pw_module_info = None):
        self.module_list = []
        self.module_number = 0

        # For bss Type - 1
        if station_type == "GEN2_530":
            self.cabinet_type = "GEN2_CAB"
            self.module_number = 13
            for i in range(self.module_number):
                self.module_list.append(Power_Module(GC.UU40kW, i)) # module, id
            self.module_power = self.module_list[0].max_power
            self.module_current = self.module_list[0].max_current
        

        # For bss Type - 2 600 kWh, B chargeable module
        if station_type == "GEN3_1200":
            self.cabinet_type = "GEN3_CAB"
            self.module_number = 10  
            for i in range(self.module_number):
                self.module_list.append(Power_Module(GC.UU60kW,i))
            self.module_power = self.module_list[0].max_power
            self.module_current = self.module_list[0].max_current
        

        if station_type == "User_Defined":
            self.cabinet_type = "User_Defined"
            self.module_number = pw_module_info["max_charger_number"] 
            for i in range(int(self.module_number)):
                self.module_list.append(Power_Module(pw_module_info["power_module_type"],i))
            self.module_power = self.module_list[0].max_power
            self.module_current = self.module_list[0].max_current

    def config_module(self, config_map): # config_map: list
        '''
        Detect the Error of arrangement (module number inconsistence)
        Connect the modules according to the config_map
        '''
        if len(config_map) != self.module_number:
            logger.error('config map size not matching module number')
            return
        for i in range(len(self.module_list)):
            self.module_list[i].link_to = config_map[i]
            if self.module_list[i].link_to == 0:
                self.module_list[i].stop_charge()
        return

    def get_power_pc(self):
        '''
        get total power of current time step, used for data logging
        '''
        total_power = 0
        for i in range(len(self.module_list)):
            if self.module_list[i].link_to != 0:
                total_power += self.module_list[i].power
        return total_power

######################################################################
####################### Class: Battery_Rack ##########################
######################################################################

class Battery_Rack:
    '''
    Basic parameters and operations related to single-layer battery racks are defined
    '''
    def __init__(self, id): 
        self.id = id # id number of battery rack (index of list), begins from 0
       
        self.status = "free" 
        '''
        Definition of status
        free: No battery avaiable
        loaded: battery stored in the rack
        charging: battery in charge
        discharging : battery in discharge back to grid
        '''
        self.battery = None # save a Battery instance
        self.plug = 0 # 0 - electrical connector disconnected; 1 - electrical connector connected
        '''
        Definition of plug
        0: disconnected
        1: connected
        '''

    def plug_in(self):
        '''
        set to "charging"
        '''
        if self.battery is not None: #If you find a battery in the battery holder
            self.plug = 1
            self.status = "charging" #Update the battery status to accept charging. The only place where you can set the charging on status to charging is

    ################################################################################
    ################################################################################
    def plug_in_for_discharge(self):
        '''
        set to discharge
        '''
        if self.battery is not None:
            self.plug = 1
            self.status = "discharging"

    def plug_out(self):
        '''
        charging -> loaded
        else -> free
        '''
        if self.status == "charging" or self.status == "discharging": #If you unplug the plug while waiting for charging, exit the charging state
            if self.battery is not None: #If there is a battery, set the battery rack status to Loaded
                self.status = "loaded"
            else:
                self.status = "free" #Otherwise set the battery rack status to Idle
        self.plug = 0

    def start_charge(self):
        if self.battery is not None: #If there are batteries in the battery holder
            self.plug_in() #Automatically charges when plugged in
            return True
        else:
            return False
    
    ################################################################################
    ################################################################################    
    def start_discharge(self):
        if self.battery is not None: #If there are batteries in the battery holder
            self.plug_in_for_discharge() #Automatically discharges back to the grid after plugging in
            return True 
        else:
            return False

    def stop_charge(self):
        if self.battery is not None: #If there are batteries in the battery holder
            self.status = "loaded"
        self.plug_out()
    
    def load_battery(self, battery : Battery):# If a battery is successfully loaded, the battery rack ID is returned. Otherwise, -1 is returned, indicating that there is a battery.
        if self.battery is not None: #If there are batteries in the battery holder
            return -1 #Returns -1 to indicate failure
        else:
            self.battery = battery
            self.status = "loaded"
            self.plug_out
            return self.id

    def remove_battery(self): # If a battery is successfully removed, the battery rack ID is returned, otherwise -1 is returned, indicating that it was originally empty.
        if self.battery is not None: #If there are batteries in the battery holder
            self.stop_charge()
            self.battery = None
            self.status = "free"
            return self.id
        else:
            self.plug_out()
            self.status = "free" 
            return -1

######################################################################
####################### Class: Charge_PIle ###########################
######################################################################

class Charge_Pile:
    def __init__(self, max_current, pile_id): #The charging gun head only defines the maximum charging current max current = 650
        '''
        Definition of status for piles
        free: No vehicle connected
        connected: vehicle connected but not charged
        charging: vehicle is in charging
        '''
        self.status = "free" #free & connected & charging
        self.vehicle_battery = None # Car battery connected to charging station
        self.max_current = max_current 
        self.output_power = 0
        self.output_current = 0
        self.id = pile_id 
        return
         
    def connect_to_vehicle(self, vehicle_battery : Battery):
        '''
        connect vehicle and piles, success return index of pile, failure return -1
        '''
        if vehicle_battery is None: #If the connected battery is empty
            logger.error('pile %d : vehicle_battery not exist',self.id)
            return -1 #Failed to connect vehicle battery
        elif self.vehicle_battery is not None: # for allready connected piles
            logger.info('pile %d : already has vehicle connected',self.id)
            return -1 #Failed to connect vehicle battery
        else:
            self.status = "connected"
            self.vehicle_battery = vehicle_battery
            return self.id
    
    def vehicle_leave(self): #Vehicle leaves the charging pile
        if self.vehicle_battery is None:
            logger.info('pile does not have vehicle connected, pile status = %s, pile# %d',self.status,self.id)
            return -1
        self.stop_charge()
        self.status = "free"
        self.vehicle_battery = None
        return self.id
    
    def stop_charge(self): #Charging terminal stops charging
        if self.vehicle_battery is None: #If no battery is connected to the charging terminal
            # logger.debug('temp to stop charge when there is no vehicle connected, pile status = %s, pile# %d',self.status,self.id)
            self.status = "free"
            return
        else:
            self.status = "connected"
            return

    def start_charge(self): #Charging terminal starts charging
        if self.vehicle_battery is None: #If no battery is connected to the charging terminal
            # logger.debug('temp to start charge when there is no vehicle connected, pile status = %s',self.status)
            self.status = "free"
            return -1
        else:
            self.status = "charging"
            return

######################################################################
####################### Class: Swap_Rack #############################
######################################################################

class Swap_Rack:
# Defines a set of battery racks, the number of battery racks, the basic power that can be allocated to each battery storage location, and the number of external charging pile expansions supported by each battery rack.
# And how much to match, what kind of charging module and other parameters
    def __init__(self, param, station_type, psc_num, id):
        self.id = id
        self.psc_num = psc_num
        self.battery_num = 0
        self.pile_connected = 0
        self.battery_rack_list = []
        self.charge_pile_list = []
                                                    # define how module connect with battery or charge pile (index->ID of modules, values->connection form)
        self.connection_map = []                    # Defines the status of each module connected to the battery and charging pile
        self.station_type = station_type
        self.target_soc = param["target_soc"]       # For bsc upper limit
        self.select_soc = param["select_soc"]       # For bss upper limit
        self.set_sr_temperature()                   # The default temperature inside and outside the warehouse is 25 degrees
        self.charge_power_redist_trigger = param["charge_power_redist"] # bool
        self.power_dist_option = param["power_dist_option"] # "bss prefered" or "bsc prefered"

        # For bss Type - 1
        if station_type == "GEN2_530":
            self.power_cabinet = Power_Cabinet(station_type)
            self.max_rack_number = 13
            for i in range(self.max_rack_number):
                self.battery_rack_list.append(Battery_Rack(i)) 
            self.max_pile_number = 0
            self.charge_pile_list = None
            self.connection_map = [0,0,0,0,0,0,0,0,0,0,0,0,0]
            '''
            Definition of connection_map
            list index: Index number of power modules in the cabinet
            list value:
                0: current power module has "No connection"
                -1 ... -4: Index number of charge Pile, current power module connect with this pile No.
                1 ... N: Index number of batteries, current power modules connect with this battery No.
            
            connection_mapinstruction：
            connection_map defines the connection relationship between the output of each power module and the demand side
            The index of each element of connection_map represents the index of the module, and the value represents the connection target. The connection target includes the battery rack battery in the station and the charging terminal outside the station.
            If the element in the connection_map is a positive integer N greater than 0, it means that the module is connected to the Nth battery rack in the site, and the index of the battery rack battery_rack is equal to N-1
            If the element in connection_map is a negative integer N less than 0, it means that the module is connected to the Nth charging terminal outside the station, and the index of the charging terminal pile is equal to -1*N-1
            If the element in connection_map is 0, it means that the module is not connected to any charging device.
            Example: connection_map[0] = 1 Module No. 0 is connected to battery rack No. 0
            Example: connection_map[1] = -2 Module No. 1 is connected to charging terminal No. 1
            Example: connection_map[2] = 0 Module No. 2 has no connection and no output.
            '''
        
        # Swap Rack Arrangement:
        # For bss Type - 2 600 kWh: one Form 1 + one Form 2
        # For bss Type - 2 1200 kWh: two Form 2
        
        # For bss Type - 2 Form 1
        if station_type == "GEN3_600":
            self.power_cabinet = None
            self.max_rack_number = 10
            for i in range(self.max_rack_number):
                self.battery_rack_list.append(Battery_Rack(i))
            self.max_pile_number = 0
            self.charge_pile_list = None
            self.connection_map = []
        
        # For bss Type - 2 Form 2
        if station_type == "GEN3_1200":
            self.power_cabinet = Power_Cabinet(station_type)
            self.max_rack_number = 10
            for i in range(self.max_rack_number):
                self.battery_rack_list.append(Battery_Rack(i)) # i -> id
            self.max_pile_number = int(self.psc_num)
            for i in range(self.max_pile_number):
                self.charge_pile_list.append(Charge_Pile(650, i)) # i -> id
            self.connection_map = [0,0,0,0,0,0,0,0,0,0]




        # For User Defined
        if station_type == "User_Defined":
            self.power_cabinet = Power_Cabinet(station_type, pw_module_info=param["station_type"])
            self.max_rack_number = int(param["station_type"]["max_charger_number"])
            for i in range(self.max_rack_number):
                self.battery_rack_list.append(Battery_Rack(i)) # i -> id
            self.max_pile_number = int(self.psc_num)
            for i in range(self.max_pile_number):
                self.charge_pile_list.append(Charge_Pile(650, i)) # i -> id
            cm = np.zeros(int(param["station_type"]["max_charger_number"]))
            self.connection_map = list([int(s) for s in cm])


    def set_temperature(self, real_temp):
        '''
        set simulation temperature (setup test temp that closest to the real temp)
        '''
        test_list_dict = [-20,-10,0,10,20,25,30,40]
        diff_min = abs(test_list_dict[0] - real_temp)
        temp = test_list_dict[0]
        if isinstance(real_temp, int):
            for t in test_list_dict:
                diff = abs(t - real_temp)
                if diff < diff_min:
                    temp = t
                    diff_min = diff
        return temp

    def set_sr_temperature(self, rack_temperature = 25, external_temperature = 25):
        '''
        set swap rack temp = 25 (real)
        set external temp = 25 (real)
        set batteries temp (in rack) = rack temp
        set batteries on vehicles temp = external temp
        '''
        self.rack_temperature = self.set_temperature(rack_temperature)
        self.external_temperature = self.set_temperature(external_temperature)
        for rack in self.battery_rack_list:
            if isinstance(rack.battery, Battery):
                rack.battery.set_temperature(rack_temperature)
        if self.charge_pile_list is not None:
            for pile in self.charge_pile_list:
                if isinstance(pile.vehicle_battery, Battery): 
                    pile.vehicle_battery.set_temperature(external_temperature)
        return

    def load_battery(self, battery : Battery, position = -1):
        '''
        put batteries into battery rack
        position: -1, find first empty position; otherwise, put battery into given position index
        '''
        if battery is not None: #If the battery is present
            if position == -1:  #For parameters of -1, automatically find the first free position to import the battery.
                for battery_rack in self.battery_rack_list:
                    if battery_rack.status == "free":
                        self.battery_num += 1
                        return(battery_rack.load_battery(battery)) # return battery rack id or -1
            else:
                if position < len(self.battery_rack_list) and position >= 0:
                    if self.battery_rack_list[position].status == "free":
                        self.battery_num += 1
                        return(self.battery_rack_list[position].load_battery(battery))
        return -1 # return failed

    def unload_battery(self, position = -1):
        '''
        take batteries out of battery rack
        position: -1, take all batteries; otherwise, take out battery from given position index
        '''
        if position == -1:
            for battery_rack in self.battery_rack_list:
                battery_rack.remove_battery() # return rack id or -1, status -> free
            self.battery_num = 0
            return
        
        else:
            if self.battery_rack_list[position].status != "free":
                self.battery_rack_list[position].remove_battery()
                self.battery_num -= 1
                return

    def stop_charge(self, equipment_number): # equipment number: The battery number in the battery compartment is 0 ~ N, and the charging terminal number is -1 ~ -N
        '''
        stop the charging behaviour for batteries or charge piles
        equipment_number: 0 -> N: battery; -1 -> -M: charge pile 
        '''
        # For battery
        if equipment_number >= 0: #Internal battery bay ready to stop charging
            if equipment_number >= len(self.battery_rack_list):
                logger.error('stop_charge:equipment number %d larger than rack number %d',equipment_number,len(self.battery_rack_list))
                return
            self.battery_rack_list[equipment_number].stop_charge()
            return
        # For charge pile
        if equipment_number < 0: #Charging station stops charging
            equipment_number = (equipment_number * (- 1)) - 1 #Change to the index of the charging pile list
            if equipment_number >= len(self.charge_pile_list):
                logger.error('stop_charge:equipment number %d larger than charger number %d',equipment_number,len(self.charge_pile_list))
                return
            self.charge_pile_list[equipment_number].stop_charge()
            return
            
    def stop_charge_all(self): #Stop all on-site battery and charging station charging
        '''
        stop charging behaviour for all facilities
        '''
        if self.power_cabinet is None:
            if self.power_cabinet is None:
                logger.debug('swap rack without power cabinet: exit')
                return
            
        if self.battery_rack_list is not None:
            for i in range(len(self.battery_rack_list)): #All batteries in the station have stopped charging.
                self.stop_charge(i)
        if self.charge_pile_list is not None:
            for i in range(len(self.charge_pile_list)): #All charging stations have stopped charging.
                self.stop_charge((i + 1) * (-1))

    def start_charge(self, equipment_number): # equipment number: The battery number in the battery compartment is 0 ~ N, and the charging terminal number is -1 ~ -N
        '''
        start the charging behaviour
        equipment_number: 0->N:battery; -1->-M:charge pile
        '''
        if equipment_number >= 0: #Internal battery bay ready for charging
            if equipment_number >= len(self.battery_rack_list):
                logger.error('start_charge:equipment number %d larger than rack number %d',equipment_number,len(self.battery_rack_list))
                return
            self.battery_rack_list[equipment_number].start_charge()
        
        if equipment_number < 0: #Reserve charging pile to start charging
            equipment_number = (equipment_number * (-1)) - 1 #Change to the index of the charging pile list
            if equipment_number >= len(self.charge_pile_list):
                logger.error('start_charge:equipment number %d larger than charger number %d',equipment_number,len(self.charge_pile_list))
                return
            self.charge_pile_list[equipment_number].start_charge()
        
    def start_charge_all(self): #Enable charging of all batteries and charging stations in the station
        '''
        start charging behaviour for all facilities
        '''
        if self.power_cabinet is None:
            logger.debug('swap rack without power cabinet: exit')
            return
        if self.battery_rack_list is not None:        
            for i in range(len(self.battery_rack_list)):
                self.start_charge(i)
        if self.charge_pile_list is not None:        
            for i in range(len(self.charge_pile_list)):  #All charging stations start charging
                self.start_charge((i + 1) * (-1))
    
    ################################################################################
    ################################################################################
    def start_discharge(self, equipment_number):
        '''
        start the discharge behaviour of certain battery rack
        '''
        if equipment_number >= 0: #Internal battery bay ready for charging
            if equipment_number >= len(self.battery_rack_list):
                logger.error('start_charge:equipment number %d larger than rack number %d',equipment_number,len(self.battery_rack_list))
                return
            self.battery_rack_list[equipment_number].start_discharge()

    def connect_vehicle(self, vehicle_battery : Battery, pile_number : int): # The charging pile is connected to the external vehicle battery, and the pile_number is 0 ~ N (the index of the charging pile list is used here)
        '''
        connect pile with vehicle battery
        pile_number: index of charge pile list
        '''
        if pile_number < 0 or pile_number >= len(self.charge_pile_list):
            logger.error('pile number %d larger than charger number %d',pile_number,len(self.charge_pile_list))
            return -1
        if vehicle_battery is not None: #If the vehicle battery is present
            if self.charge_pile_list[pile_number].connect_to_vehicle(vehicle_battery) >= 0: # pile id
                self.pile_connected += 1
                return pile_number
            else:
                return -1
        else:
            return -1
        
    def vehicle_leave(self, pile_number : int): #The vehicle leaves the charging terminal, pile_number is 0 ~ N (the index of the charging pile list is used here)
        '''
        vehicle leaves the charge pile
        pile number: index of charge pile list
        '''
        if pile_number < 0 or pile_number >= len(self.charge_pile_list):
            logger.error('pile number %d larger than charger number %d',pile_number,len(self.charge_pile_list))
            return
        if self.charge_pile_list[pile_number].vehicle_leave() >= 0: # pile id
            self.pile_connected -= 1

    def module_number_check(self, battery : Battery, current_limit = 250): #Calculate how many modules the battery can be charged by and return the number of modules
        '''
        calculate the maximal allowable number of power modules (in Power Cabinet) to a battery
        return 0 or module_num
        '''
        # No battery return 0 module
        if battery is None:
            return 0
        # battery reachs its target soc return 0 module
        if battery.soc >= battery.target_max_soc:
            return 0
        
        battery.request_power(current_limit = 250) # calc power_command
        current_allowable = min(battery.current_command, current_limit)        
        power_allowable = current_allowable * battery.battery_voltage / 1000.0 # max allowable power return in kW
        for i in range(10):
            module_num = i + 1
            powerd = power_allowable / module_num
            currentd = current_allowable / module_num
            if powerd <= self.power_cabinet.module_power or currentd <= self.power_cabinet.module_current:
                break
        return module_num

    ################################################################################
    ################################################################################
    def connect_charge_pile(self, pile : Charge_Pile): #Connect the charging terminal vehicle battery to the largest module that can be connected, which is reflected in the connection_map. If the connection is successful, True is returned.
        '''
        connect the pile with max number of Power modules
        '''
        if pile.vehicle_battery is None:
            logger.error('pile number %d no vehicle connected - %s',pile.id,pile.status)
            return False
        # calculate the max allowable number of modules connect with this battery
        module_num = self.module_number_check(pile.vehicle_battery, pile.max_current)
        # get the num of still connectable power modules
        module_num = module_num - self.connection_map.count(-1 * pile.id  - 1) # pile id: 0 -> N; pile id in connection map: -N-1 -> -1
        
        # strategy 1: bss prefered
        if self.power_dist_option == "BSS preferred":
            for i in range(len(self.connection_map)):
                # if current module is free and battery still allow to connect with another module
                if self.connection_map[i] == 0 and module_num > 0:
                    module_num -= 1
                    self.connection_map[i] = ((-1) * pile.id - 1) # for pile index: -1 -> -N-1
                # if current module connect with this id pile, but extend max allowable connection number of modules
                if self.connection_map[i] == ((- 1) * pile.id -1) and module_num < 0:
                    module_num += 1
                    self.connection_map[i] = 0
                # if battery allready connected with max allowable number of modules
                if module_num == 0:
                    break
        # strategy 2: bsc prefered
        else:
            rack_soc_list = self.get_rack_battery_soc()
            while module_num > 0:
                for i in range(len(self.connection_map)):
                    # if current module is free and battery still allow to connect with another module
                    if self.connection_map[i] == 0 and module_num > 0:
                        module_num -= 1
                        self.connection_map[i] = ((-1) * pile.id - 1) # for pile index: -1 -> -N-1
                    # if current module connect with this id pile, but extend max allowable connection number of modules
                    if self.connection_map[i] == ((- 1) * pile.id -1) and module_num < 0:
                        module_num += 1
                        self.connection_map[i] = 0
                    # if battery allready connected with max allowable number of modules
                    if module_num == 0:
                        break
                # after arrangement if residual num still > 0 -> reconnect rack power module with min soc to the PSC
                if module_num > 0:
                    rack_idx = self.get_min_soc_rack_index(rack_soc_list)
                    map_idx = [x for x,y in list(enumerate(self.connection_map)) if y == rack_idx+1]
                    self.stop_charge(rack_idx)
                    for i in map_idx:
                        self.connection_map[i] = ((-1) * pile.id - 1)
                    rack_soc_list.remove(min(rack_soc_list))
                    module_num -= 1
                else:
                    break
        ################################################################################
        ################################################################################
        # if self.power_dist_option == "Smart advicer":


    ################################################################################
    ################################################################################
    def get_rack_battery_soc(self):
        '''
        read the rack list and get all soc values -> return in format list
        '''
        rack_battery_soc = []
        for i in range(len(self.battery_rack_list)):
            if isinstance(self.battery_rack_list[i].battery, Battery): #If the corresponding battery is present
                    rack_battery_soc.append(self.battery_rack_list[i].battery.soc)
        return rack_battery_soc
    
    ################################################################################
    ################################################################################
    def get_min_soc_rack_index(self, soc_list:list):
        '''
        return the index of corresponding minimal value of rack soc
        '''
        idx = soc_list.index(min(soc_list))

        return idx 

    def power_distribution_max(self):
        '''
        distribute the power arrangement
        The power allocation principle is that even-numbered bins 0/2/4/6/8/10/12 can be allocated to N and N+1 power, and odd-numbered bins can be allocated to N and N-1 power.
        The power allocation principle for external discharge is: the power of No. 0-9 (10 batteries) can be allocated to No. 0-3 external charging terminals, and the power of No. 10-19 (10 batteries) can be allocated to No. 4-7 external charging terminals.
        '''
        # ======================================================================================
        # ================= Part 0: Exception case -> No Power Cabinet =========================
        # ======================================================================================
        # If this battery compartment does not have a power cabinet
        if self.power_cabinet is None: 
            # logger.debug('no power cabinet connected')
            return
        
        # ======================================================================================
        # ================= Part 1: Get the power request for BSS and charge piles =============
        # ======================================================================================
        
        # save the battery power command
        swap_power_req = []
        for battery_rack in self.battery_rack_list:
            if battery_rack.battery is not None:
                battery_rack.battery.request_power()
                if battery_rack.battery.soc < self.select_soc:
                    swap_power_req.append(battery_rack.battery.power_command)
                else:
                    swap_power_req.append(-1) # -1 means no power request
            else:
                swap_power_req.append(-1)
        # save the pile(vehicle battery) power command
        charge_power_req = []
        for charge_pile in self.charge_pile_list:
            if charge_pile.vehicle_battery is not None:
                charge_pile.vehicle_battery.Request_Power(current_limit=charge_pile.max_current)
                if charge_pile.vehicle_battery.soc < charge_pile.vehicle_battery.target_max_soc:
                    charge_power_req.append(charge_pile.vehicle_battery.power_command)
                else:
                    charge_power_req.append(-1)
                    charge_pile.vehicle_leave()
            else:
                charge_power_req.append(-1)
    # The above calculation is performed on the charging power requirements of all target batteries that can currently be charged, and the current power requirements of each charging load are obtained.
    # The charging power requirements of the battery swap station are stored in the swap_power_req list
    # The charging power requirements of the charging terminal are stored in the charge_power_req list
    
        # ======================================================================================
        # ================= Part 2: Setup the power arrangement in the BSS =====================
        # ======================================================================================

        #If the battery in the battery swap station needs charging, first connect a module to the demand position
        connection_map_save = self.connection_map
        for i in range(len(self.connection_map)):
            self.connection_map[i] = 0 # rearrange the power connection 
            if swap_power_req[i] > 0:
                self.connection_map[i] = i + 1 # battery index 0 -> N; battery index in connection map: 1 -> N + 1
    
        #If there is a charging module requested by the battery in the power swap station > 1 and there is an adjacent power module that can be allocated, connect the module to the battery in the battery compartment
        for i in range(len(self.battery_rack_list)):
            if (i % 2) == 0: # even digits
                if self.connection_map[i] == i + 1 and i + 1 < len(self.battery_rack_list):
                    r_b = self.battery_rack_list[i].battery
                    m_n = self.module_number_check(r_b, current_limit = 250) #The maximum current limit in the battery swap station is 250                                                     
                    if m_n > 1:
                        if self.connection_map[i + 1] == 0:
                            self.connection_map[i + 1] = i + 1
            else: # Odd digits
                if self.connection_map[i] == i + 1:
                    r_b = self.battery_rack_list[i].battery
                    m_n = self.module_number_check(r_b, current_limit = 250) #The maximum current limit in the battery swap station is 250                                                    
                    if m_n > 1:
                        if self.connection_map[i - 1] == 0:
                            self.connection_map[i - 1] = i + 1

        # ======================================================================================
        # ================= Part 3: Setup the power arrangement for charge piles ===============
        # ======================================================================================

        #If there is already a charging module connected to the external charging pile, one module will be allocated first.
        for j in range(len(self.charge_pile_list)): #Check the charging pile load that is currently charging
            r_b = self.charge_pile_list[j].vehicle_battery
            m_n = self.module_number_check(r_b, current_limit = self.charge_pile_list[j].max_current)
            pid = -1 * j - 1 # charge piles index in connection_map:  -1 -> -N - 1
            if connection_map_save.count(pid) > 0 and m_n > 0: #If there is a connection in the original charging connection and the number of charging modules currently required is greater than 0
                for i in range(len(self.connection_map)):
                    if self.connection_map[i] == 0: #If there are modules that can be assigned
                        self.connection_map[i] = pid #Connect the charging module to the target charging pile
        
        #If the charging module is still free, connect it to an external charging device
        for j in range(len(self.charge_pile_list)):
            r_b = self.charge_pile_list[j].vehicle_battery
            m_n = self.module_number_check(r_b, current_limit = self.charge_pile_list[j].max_current)
            pid = -1 * j - 1
            m_n = m_n - self.connection_map.count(pid)
            for i in range(len(self.connection_map)):
                if self.connection_map[i] == 0 and m_n > 0:
                    self.connection_map[i] = pid
                    m_n -= 1

        # ======================================================================================
        # ================= Part 4: config modules and start charging behaviour ================
        # ======================================================================================

        self.power_cabinet.config_module(self.connection_map)
        self.stop_charge_all()
        for equipment_id in self.connection_map:
            if equipment_id > 0: #If it is the equipment inside the battery
                self.start_charge(equipment_id - 1)
            if equipment_id < 0: #If it is the equipment for an external charging pile
                self.start_charge(equipment_id)
        return
        
    def power_distribution_pss_preferred(self):
        '''
        Calculate power allocation rules based on the current connected battery status and implement it through the connection_map list
         Rule 1: When the battery SOC in the battery swap station reaches the charging station termination SOC (select_soc), charging will be stopped and the charging module will be released.
         Rule 2: The priority of the battery in the battery swap station is higher than the priority of the charging pile. When the battery swap station has remaining power, it will be allocated externally -> modify!
         Rule 3: The power module will not be released before the charging pile completes charging.
​

        The power allocation principle is that even-numbered bins 0/2/4/6/8/10/12 can be allocated to N and N+1 power, and odd-numbered bins can be allocated to N and N-1 power.
        The power allocation principle for external discharge is: No. 0-9 (the first 10 charging modules) power can be allocated to No. 0-3 external charging terminals, No. 10-19 (the last 10 charging modules) power can be allocated to No. 4-7 external charging terminals. Charging terminal allocation
​

        connection_map description:
         connection_map defines the connection relationship between the output of each power module and the demand side
         The index of each element of connection_map represents the index of the module, and the value represents the connection target. The connection target includes the battery rack battery in the station and the charging terminal outside the station.
         If the element in the connection_map is a positive integer N greater than 0, it means that the module is connected to the Nth battery rack in the site, and the index of the battery rack battery_rack is equal to N-1
         If the element in connection_map is a negative integer N less than 0, it means that the module is connected to the Nth charging terminal outside the station, and the index of the charging terminal pile is equal to -1*N-1
         If the element in connection_map is 0, it means that the module is not connected to any charging device.
         Example: connection_map[0] = 1 Module No. 0 is connected to battery rack No. 0
         Example: connection_map[1] = -2 Module No. 1 is connected to charging terminal No. 1
         Example: connection_map[2] = 0 Module No. 2 has no connection and no output.
​
        '''

        # ======================================================================================
        # ================= Part 0: Exception case -> No Power Cabinet =========================
        # ======================================================================================

        if self.power_cabinet is None: #If this battery compartment does not have a power cabinet
            if(self.station_type != "GEN3_600"):
                logger.debug('no power cabinet connected')
            return
        
        # ======================================================================================
        # ================= Part 1: Arrangement power modules to BSS and charge piles ==========
        # ======================================================================================

        for i in range(len(self.connection_map)):
            # case 1: check the Battery in Swap Rack
            if self.connection_map[i] > 0:
                '''
                If the current module is assigned to the battery rack in the station
                 In the following situations:
                 1. There is no battery in the battery rack - release the module and set the Rack to remove_battery state
                 2. The battery is fully charged
                 3. The battery plug has been unplugged - release the module and set the rack to plug_out state.
                 Release the module by setting the corresponding position of connection_map to zero.
                '''
                rack_id = self.connection_map[i] - 1

                if isinstance(self.battery_rack_list[rack_id].battery, Battery): #If the corresponding battery is present
                    # for event 2 and 3
                    if self.battery_rack_list[rack_id].battery.soc >= self.select_soc or self.battery_rack_list[rack_id].plug == 0:
                        self.battery_rack_list[rack_id].plug_out()
                        self.connection_map[i] = 0
                else:
                    # for event 1
                    self.connection_map[i] = 0
                    self.battery_rack_list[rack_id].remove_battery()

            # case 2: bsc charge piles
            if self.connection_map[i] < 0:
                '''
                If the current module is assigned to a charging pile
                 Press under the following conditions:
                 1. The charging pile is not connected to the vehicle battery - release the charging module, charging pile vehicle_leave
                 2. The vehicle battery SOC has reached the set value target_max_soc - release the charging module and stop_charge the charging pile
                 3. The vehicle stops charging pile.status = "connected" - Release the charging module and the charging pile stops_charge
                '''
                if self.charge_pile_list is not None:
                    # recalculate the charge pile id
                    pile_id = -1 * self.connection_map[i] - 1

                    if isinstance(self.charge_pile_list[pile_id].vehicle_battery, Battery): #If the corresponding battery is present
                        # for case 2 and 3
                        if self.charge_pile_list[pile_id].vehicle_battery.soc >= self.target_soc or self.charge_pile_list[pile_id].status == "connected":
                            self.connection_map[i] = 0
                            self.charge_pile_list[pile_id].stop_charge()    
                    else:
                        # for case 1
                        self.connection_map[i] = 0      
                        self.charge_pile_list[pile_id].vehicle_leave()       
                else:
                    logger.error('do not have charge pile list')
        
        # ======================================================================================
        # ================= Part 2: Power distribution and optimization ========================
        # ======================================================================================
                 
        #Recheck the power distribution of the battery swap station to see if the simultaneous output of both modules is maintained.
        for i in range(len(self.battery_rack_list)):
            if self.connection_map.count(i + 1) > 1:                                        # check if one item connect with more than one power module
                rack_battery = self.battery_rack_list[i].battery
                module_num = self.module_number_check(rack_battery, current_limit = 250)    #The maximum current limit in the battery swap station is 250
                if module_num < 2:                                                          #If one module can support charging
                    if (i % 2) == 0:                                                        #If it is the battery holder No. 0/2/4..
                        if i < len(self.battery_rack_list) - 1:                             #Protect i + 1 index from overflow
                            self.connection_map[i + 1] = 0                                  # release the residual power module
                    else:
                        self.connection_map[i - 1] = 0


        #Allocate charging modules according to the power requirements of the battery swap station warehouse
        for i in range(len(self.battery_rack_list)):
            # Battery exists & battery soc < target soc & power module pluged
            if isinstance(self.battery_rack_list[i].battery, Battery) and self.battery_rack_list[i].battery.soc < self.select_soc and self.battery_rack_list[i].plug == 1:
                rack_battery = self.battery_rack_list[i].battery
                module_num = self.module_number_check(rack_battery, current_limit = 250)
                # If this module is occupied by an external charging pile and the number of connections is greater than 1, no processing will be performed.
                if self.connection_map[i] < 0 and self.connection_map.count(self.connection_map[i]) > 1: 
                    pass
                else:
                    # If the module is not occupied by an external charging pile, first ensure that there is no full battery in the battery compartment and the battery plugged into the connector can be charged.
                    self.connection_map[i] = i + 1 
                
                # Force the power of external charging piles to be distributed back to the station
                if self.charge_power_redist_trigger == True: 
                    self.connection_map[i] = i + 1
                
                #If it can be charged by an adjacent charging module, or this module is occupied externally
                if module_num > 1 or self.connection_map[i] != i + 1: 
                    if (i % 2) == 0: 
                        if i < len(self.battery_rack_list) - 1: #Protect i + 1 index from overflow
                            if self.connection_map[i + 1] == 0:
                                self.connection_map[i + 1] = i + 1
                    else:
                        if self.connection_map[i - 1] == 0:
                            self.connection_map[i - 1] = i + 1

        #Optimize the charging power of connected external charging piles
        if self.charge_pile_list is not None:
            for pile in self.charge_pile_list:
                # if exists battery connected to bsc
                if isinstance(pile.vehicle_battery, Battery):
                    if pile.vehicle_battery.soc >= self.target_soc: #If it has been charged to the specified SOC, the vehicle leaves
                    # if pile.vehicle_battery.soc >= pile.vehicle_battery.target_max_soc: #If it is full, the vehicle leaves
                        self.vehicle_leave(pile.id)
                    if pile.status == "charging": #If it is still charging, optimize the charging power
                        self.connect_charge_pile(pile) #There is a question of priority here. Not yet resolved
            #Allocate charging modules to external charging piles based on remaining power
            for pile in self.charge_pile_list:
                if pile.vehicle_battery is not None: #If a battery is connected to the charging terminal
                    if pile.status == "connected" and self.connection_map.count(-1 * pile.id - 1) == 0: #Not charging and no modules are assigned
                        self.connect_charge_pile(pile) #Connect the charging terminal to the module through connect_map
        # ======================================================================================
        # ================= Part 3: Restart the power distribution and charging ================
        # ======================================================================================

        self.power_cabinet.config_module(self.connection_map)
        self.stop_charge_all()
        for equipment_id in self.connection_map:
            if equipment_id > 0: #If it is the equipment inside the battery
                self.start_charge(equipment_id - 1)
            if equipment_id < 0: #If it is the equipment for an external charging pile
                self.start_charge(equipment_id)

    ################################################################################
    ################################################################################
    def power_distribution_psc_preferred(self):
        

        # ======================================================================================
        # ================= Part 0: Exception case -> No Power Cabinet =========================
        # ======================================================================================
        if self.power_cabinet is None: 
            if(self.station_type != "GEN3_600"):
                logger.debug('no power cabinet connected')
            return
        
        # ======================================================================================
        # ================= Part 1: Arrangement power modules to BSS and charge piles ==========
        # ======================================================================================
        for i in range(len(self.connection_map)):
            # case 1: check the Battery in Swap Rack
            if self.connection_map[i] > 0:
            
                rack_id = self.connection_map[i] - 1
                if isinstance(self.battery_rack_list[rack_id].battery, Battery): 
                    # for event 2 and 3
                    if self.battery_rack_list[rack_id].battery.soc >= self.select_soc or self.battery_rack_list[rack_id].plug == 0:
                        self.battery_rack_list[rack_id].plug_out()
                        self.connection_map[i] = 0
                else:
                    # for event 1
                    self.connection_map[i] = 0
                    self.battery_rack_list[rack_id].remove_battery()

            # case 2: bsc charge piles
            if self.connection_map[i] < 0:
            
                if self.charge_pile_list is not None:
                    # recalculate the charge pile id
                    pile_id = -1 * self.connection_map[i] - 1

                    if isinstance(self.charge_pile_list[pile_id].vehicle_battery, Battery): 
                        # for case 2 and 3
                        if self.charge_pile_list[pile_id].vehicle_battery.soc >= self.target_soc or self.charge_pile_list[pile_id].status == "connected":
                            self.connection_map[i] = 0
                            self.charge_pile_list[pile_id].stop_charge()    
                    else:
                        # for case 1
                        self.connection_map[i] = 0      
                        self.charge_pile_list[pile_id].vehicle_leave()       
                else:
                    logger.error('do not have charge pile list')
        
        # ======================================================================================
        # ================= Part 2: Power distribution and optimization ========================
        # ======================================================================================        

        
        for i in range(len(self.battery_rack_list)):
            if self.connection_map.count(i + 1) > 1:                                        
                rack_battery = self.battery_rack_list[i].battery
                module_num = self.module_number_check(rack_battery, current_limit = 250)    
                if module_num < 2:                                                          
                    if (i % 2) == 0:                                                        
                        if i < len(self.battery_rack_list) - 1:                             
                            self.connection_map[i + 1] = 0                                  
                    else:
                        self.connection_map[i - 1] = 0

        
        if self.charge_pile_list is not None:
            for pile in self.charge_pile_list:
                # if exists battery connected to bsc
                if isinstance(pile.vehicle_battery, Battery):
                    if pile.vehicle_battery.soc >= self.target_soc:                                     
                        self.vehicle_leave(pile.id)                                                     
                    if pile.status == "charging":                                                      
                        self.connect_charge_pile(pile)                                                  
                    if pile.status == "connected" and self.connection_map.count(-1 * pile.id - 1) == 0: 
                        self.connect_charge_pile(pile)                                                      

        
        for i in range(len(self.battery_rack_list)):
            # Battery exists & battery soc < target soc & power module pluged
            if isinstance(self.battery_rack_list[i].battery, Battery) and self.battery_rack_list[i].battery.soc < self.select_soc and self.battery_rack_list[i].plug == 1:
                rack_battery = self.battery_rack_list[i].battery
                module_num = self.module_number_check(rack_battery, current_limit = 250)
                
                if self.connection_map[i] < 0 and self.connection_map.count(self.connection_map[i]) > 1: 
                    pass
                else:
                    
                    self.connection_map[i] = i + 1 
                
                if module_num > 1 or self.connection_map[i] != i + 1: 
                    if (i % 2) == 0: 
                        if i < len(self.battery_rack_list) - 1: 
                            if self.connection_map[i + 1] == 0:
                                self.connection_map[i + 1] = i + 1
                    else:
                        if self.connection_map[i - 1] == 0:
                            self.connection_map[i - 1] = i + 1

        # ======================================================================================
        # ================= Part 3: Restart the power distribution and charging ================
        # ======================================================================================

        self.power_cabinet.config_module(self.connection_map)
        self.stop_charge_all()
        for equipment_id in self.connection_map:
            if equipment_id > 0: #If it is the equipment inside the battery
                self.start_charge(equipment_id - 1)
            if equipment_id < 0: #If it is the equipment for an external charging pile
                self.start_charge(equipment_id)

    ################################################################################
    ######################## Modified by Hao Liu ####################################
    ################################################################################


    def power_distribution_smart_advicer(self):
    

    # ======================================================================================
    # ================= Part 0: Exception case -> No Power Cabinet =========================
    # ======================================================================================
        if self.power_cabinet is None:  # If this battery compartment does not have a power cabinet
            if (self.station_type != "GEN3_600"):
                logger.debug('no power cabinet connected')
            return

        # ======================================================================================
        # ================= Part 1: Arrangement power modules to BSS and charge piles ==========
        # ======================================================================================
        for i in range(len(self.connection_map)):
            # case 1: check the Battery in Swap Rack
            if self.connection_map[i] > 0:
                '''
                If the current module is assigned to the battery rack in the station
                 In the following situations:
                 1. There is no battery in the battery rack - release the module and set the Rack to remove_battery state
                 2. The battery is fully charged
                 3. The battery plug has been unplugged - release the module and set the rack to plug_out state.
                 Release the module by setting the corresponding position of connection_map to zero.
                '''
                rack_id = self.connection_map[i] - 1
                if isinstance(self.battery_rack_list[rack_id].battery, Battery):  # 如果相应电池存在
                    # for event 2 and 3
                    if self.battery_rack_list[rack_id].battery.soc >= self.select_soc or self.battery_rack_list[
                        rack_id].plug == 0:
                        self.battery_rack_list[rack_id].plug_out()
                        self.connection_map[i] = 0
                else:
                    # for event 1
                    self.connection_map[i] = 0
                    self.battery_rack_list[rack_id].remove_battery()

            # case 2: bsc charge piles
            if self.connection_map[i] < 0:
                '''
                If the current module is assigned to a charging pile
                 Press under the following conditions:
                 1. The charging pile is not connected to the vehicle battery - release the charging module, charging pile vehicle_leave
                 2. The vehicle battery SOC has reached the set value target_soc - release the charging module and stop_charge the charging pile
                 3. The vehicle stops charging pile.status = "connected" - Release the charging module and the charging pile stops_charge
                '''
                if self.charge_pile_list is not None:
                    # recalculate the charge pile id
                    pile_id = -1 * self.connection_map[i] - 1

                    if isinstance(self.charge_pile_list[pile_id].vehicle_battery, Battery):  # If the corresponding battery is present
                        # for case 2 and 3
                        if self.charge_pile_list[pile_id].vehicle_battery.soc >= self.target_soc or self.charge_pile_list[
                            pile_id].status == "connected":
                            self.connection_map[i] = 0
                            self.charge_pile_list[pile_id].stop_charge()
                    else:
                        # for case 1
                        self.connection_map[i] = 0
                        self.charge_pile_list[pile_id].vehicle_leave()
                else:
                    logger.error('do not have charge pile list')

        # ======================================================================================
        # ================= Part 2: Power distribution and optimization ========================
        # ======================================================================================

        # Recheck the power distribution of the battery swap station to see if the simultaneous output of both modules is maintained.
        for i in range(len(self.battery_rack_list)):
            if self.connection_map.count(i + 1) > 1:  # check if one item connect with more than one power module
                rack_battery = self.battery_rack_list[i].battery
                module_num = self.module_number_check(rack_battery, current_limit=250)  # The maximum current limit in the battery swap station is 250
                if module_num < 2:  # If one module can support charging
                    if (i % 2) == 0:  # If it is the battery holder No. 0/2/4..
                        if i < len(self.battery_rack_list) - 1:  # Protect i + 1 index from overflow
                            self.connection_map[i + 1] = 0  # release the residual power module
                    else:
                        self.connection_map[i - 1] = 0

        # Optimize the charging power of external charging piles
        if self.charge_pile_list is not None:
            for pile in self.charge_pile_list:
                # if exists battery connected to bsc
                if isinstance(pile.vehicle_battery, Battery):
                    if pile.vehicle_battery.soc >= self.target_soc:  
                        self.vehicle_leave(pile.id)  
                    if pile.status == "charging":  
                        self.connect_charge_pile(pile)  
                    if pile.status == "connected" and self.connection_map.count(-1 * pile.id - 1) == 0:  
                        self.connect_charge_pile(pile)  

        # Allocate redundant charging modules according to the power requirements of the battery swap station.
        for i in range(len(self.battery_rack_list)):
            # Battery exists & battery soc < target soc & power module pluged
            if isinstance(self.battery_rack_list[i].battery, Battery) and self.battery_rack_list[
                i].battery.soc < self.select_soc and self.battery_rack_list[i].plug == 1:
                rack_battery = self.battery_rack_list[i].battery
                module_num = self.module_number_check(rack_battery, current_limit=250)
                # If this module is occupied by an external charging pile and the number of charging modules connected to the object is greater than 1, no processing will be done.
                if self.connection_map[i] < 0 and self.connection_map.count(self.connection_map[i]) > 1:
                    pass
                else:
                    # If the module is not occupied by an external charging pile, first ensure that there is no full battery in the battery compartment and the battery plugged into the connector can be charged.
                    self.connection_map[i] = i + 1


                # If it can be charged by an adjacent charging module, or this module is occupied externally
                if module_num > 1 or self.connection_map[i] != i + 1:
                    if (i % 2) == 0:
                        if i < len(self.battery_rack_list) - 1:  # 保护i + 1 index 不溢出
                            if self.connection_map[i + 1] == 0:
                                self.connection_map[i + 1] = i + 1
                    else:
                        if self.connection_map[i - 1] == 0:
                            self.connection_map[i - 1] = i + 1

        # ======================================================================================
        # ================= Part 3: Restart the power distribution and charging ================
        # ======================================================================================

        self.power_cabinet.config_module(self.connection_map)
        self.stop_charge_all()
        for equipment_id in self.connection_map:
            if equipment_id > 0:  
                self.start_charge(equipment_id - 1)
            if equipment_id < 0:  
                self.start_charge(equipment_id)

    ################################################################################

    def power_distribution_grid_interaction(self):
        '''
        stop the charging behaviour of the swap rack;
        reconnect the connection map to the batterries in the swap rack, this function is
        used for grid interaction, prepare for batteries discharge behaviour.
        '''
        # process 1: check cabinet
        if self.power_cabinet is None:                          # If this battery compartment does not have a power cabinet
            if(self.station_type != "GEN3_600"):
                logger.debug('no power cabinet connected')
            return
        # process 2: rearrange the connection map
        for i in range(len(self.connection_map)):
            if self.battery_rack_list[i].battery is not None:       # the batteries may not full loaded
                self.connection_map[i] = i + 1                      # reconnect the batteries in the rack
            else:
                self.connection_map[i] = 0
        self.power_cabinet.config_module(self.connection_map)
        self.stop_charge_all()
        for equipment_id in self.connection_map:
            if equipment_id > 0:                                # If it is the equipment inside the battery
                self.start_discharge(equipment_id - 1)
        return

    def do_charge(self, t_timer:int, interval = 1):
        '''
        excute the charging beheviours
        '''
        charge_complete=[]
        for i in range(len(self.connection_map)):
            equipment_id = self.connection_map[i]
            if charge_complete.count(equipment_id) == 0: # current equipment not counted in charge complet list
                charger_array=[]
                for j in range(len(self.connection_map)):
                    if equipment_id == self.connection_map[j]:
                        charger_array.append(j) # append connecting module index

                # for battery in BSS
                if equipment_id > 0:
                    rack_id = equipment_id - 1
                    charge_battery = self.battery_rack_list[rack_id].battery
                    module_num = len(charger_array)
                    charge_battery.request_power(250)
                    charger_current = charge_battery.current_command / module_num
                    total_current = 0
                    for t in charger_array:
                        self.power_cabinet.module_list[t].output_power(charger_current, charge_battery.battery_voltage)
                        total_current += self.power_cabinet.module_list[t].output_current
                    charge_battery.battery_charge(total_current, t_timer, interval)
                    charge_complete.append(equipment_id)

                # for battery on charge piles
                if equipment_id < 0:
                    pile_id = equipment_id * -1 - 1
                    charge_battery = self.charge_pile_list[pile_id].vehicle_battery
                    module_num = len(charger_array)
                    charge_battery.request_power(self.charge_pile_list[pile_id].max_current)
                    charger_current = charge_battery.current_command / module_num
                    total_current = 0
                    for t in charger_array:
                        self.power_cabinet.module_list[t].output_power(charger_current,charge_battery.battery_voltage)
                        total_current = total_current + self.power_cabinet.module_list[t].output_current
                    charge_battery.battery_charge(total_current,t_timer,interval)
                    charge_complete.append(equipment_id)
    
    ################################################################################

    def do_grid_discharge(self, t_timer:int, interval = 1):
        '''
        discharge the batteries from swap rack, send power back to grid
        '''
        discharge_complete=[]
        for i in range(len(self.connection_map)):
            equipment_id = self.connection_map[i]
            if discharge_complete.count(equipment_id) == 0:        # current equipment not counted in charge complet list
                discharger_array=[]
                for j in range(len(self.connection_map)):
                    if equipment_id == self.connection_map[j]:
                        discharger_array.append(j)                 # append connecting module index
        
                if equipment_id > 0:
                    rack_id = equipment_id - 1
                    if rack_id < len(self.battery_rack_list):
                        discharge_battery = self.battery_rack_list[rack_id].battery
                    module_num = len(discharger_array)
                    discharge_battery.request_power(250)
                    charger_current = discharge_battery.current_command / module_num
                    total_current = 0
                    for t in discharger_array:
                        self.power_cabinet.module_list[t].grid_interactive_output_power(charger_current, discharge_battery.battery_voltage)
                        total_current += self.power_cabinet.module_list[t].output_current
                    discharge_battery.battery_discharge(total_current, t_timer, interval)                      
                    discharge_complete.append(equipment_id)

    def get_power_sr(self):
        if self.power_cabinet is None:
            return 0
        return self.power_cabinet.get_power_pc()

######################################################################
####################### Class: SwapStation ###########################
######################################################################
class SwapStation:
    '''
    BSS Type-1, with a maximum of 13 batteries, 0 external charging piles, a maximum charging input power of 530kW, and a maximum of 13 assignable charging units.
    BSS Type-2-10-20, can accommodate up to 20 batteries, up to 4 external charging piles, maximum charging input power of 600kW, and can be allocated to a maximum of 10 charging units
        BSS Type-2-10-20, can accommodate up to 20 batteries, up to 8 external charging piles, maximum charging input power of 1200kW, and can be allocated to a maximum of 20 charging units



    The power allocation principle is that even-numbered bins 0/2/4/6/8/10/12 can be allocated to N and N+1 power, and odd-numbered bins can be allocated to N and N-1 power.
    The power allocation principle for external discharge is: the power of No. 0-9 (10 batteries) can be allocated to No. 0-3 external charging terminals, and the power of No. 10-19 (10 batteries) can be allocated to No. 4-7 external charging terminals.
    '''

    def __init__(self, param):
        '''
        self.GEN2_530kW = {"station_type":"GEN2_530","max_battery_number": 13,"max_charge_terminal":0,"max_power":520,"max_charger_number":13}
        self.GEN3_600kW = {"station_type":"GEN3_600","max_battery_number": 20,"max_charge_terminal":4,"max_power":600,"max_charger_number":10}
        self.GEN3_1200kW = {"station_type":"GEN3_1200","max_battery_number": 20,"max_charge_terminal":8,"max_power":1200,"max_charger_number":20}
        self.User_Defined = {"station_type":"User_Defined","max_battery_number": 0,"max_charge_terminal":0,"max_power":0,"max_charger_number":0,
                             "power_module_type":None}
        '''
        self.pss_type_dict = param["station_type"]                                      # get the BSS data dict
        self.max_battery_number = self.pss_type_dict["max_battery_number"]              # num of battery in the station
        self.max_charge_terminal = self.pss_type_dict["max_charge_terminal"]            # num of charge piles
        self.max_power = self.pss_type_dict["max_power"]                                # max allowable chargeable power upper limit
        self.max_charger_num = self.pss_type_dict["max_charger_number"]                 # num of power modules
        self.station_type = self.pss_type_dict["station_type"]                          # type of BSS (string)
        self.psc_num = param["psc_num"]                                                 # num of bsc connected with BSS
        self.power = 0                                                                  # save the real time power cosumption 
        self.status = "free"                                                            # 换电平台状态，free = 没有换电操作，in_use = 换电中，switch = 电池执行仓位交换中
        self.full_battery = 0                                                           # 满电电池数量
        self.swap_timer = 0                                                             # 用来为换电过程计时。这个乘以sim仿真周期就是换电进行多少时间
        self.residual_power = self.max_power - self.power                               # calculate the residual power
        self.swap_rack_list = []                                                        # empty list save for battery swap rack objects
        self.buff_rack = None
        self.battery_num = 0                                                            # !!! battery_num has calculation error !!!!
        self.enable_me_switch = param["enable_me_switch"]
        self.power_history = []                                                         # 记录充电功率的历史，记录在power_history队列中，记录结构为[timer, power]
        self.target_soc = param["target_soc"]                                           # for the bsc charge pile target soc
        self.select_soc = param["select_soc"]                                           # for the BSS battery charge target upper limit, will be select to swap when reaches this soc
        self.power_dist_option = param["power_dist_option"]                             # trigger of bsc or BSS power priority
        if param["grid_interaction_idx"] != -1:                                         # define the grid interaction start time stamp (if idx != -1)
            self.grid_interaction_timeStamp = int(param["grid_interaction_idx"] * 3600 / param["sim_interval"])
            self.grid_interaction_counter = 0                                           # define the how many times the grid interaction will perform
            self.grid_interaction_time_upper_limit = int((param["grid_interaction_idx"] + 1) * 3600 / param["sim_interval"]) # define the upper limit of grid interaction time interval
        else:
            self.grid_interaction_timeStamp = None
            self.grid_interaction_counter = 1
            self.grid_interaction_time_upper_limit = None
        self.trigger = []                                                               # trigger for grid interaction, once time for discharge, this will be 1 otherwise 0, same length as sim_ticks
        self.interaction_num = param["interaction_num"]                                 # number of interaction will be performed
        
        # Set up the station variations
        if self.station_type == "GEN2_530":
            self.swap_period = int(param["swap_time"] * 60) 
            self.swap_rack_list.append(Swap_Rack(param=param, station_type=self.station_type, psc_num=0, id=0))
            self.module_power = 40

        if self.station_type == "GEN3_600":
            self.swap_period = int(param["swap_time"] * 60) 
            self.swap_rack_list.append(Swap_Rack(param=param, station_type="GEN3_1200", psc_num=self.psc_num, id=0))
            self.swap_rack_list.append(Swap_Rack(param=param, station_type="GEN3_600", psc_num=0, id=1))         
            self.module_power = 60    

        if self.station_type == "GEN3_1200":
            self.swap_period = int(param["swap_time"] * 60)
            psc_num_1 = int(self.psc_num / 2) # num of bsc arranged to first cabinet
            psc_num_2 = int(self.psc_num - psc_num_1)  # num of bsc arranged to second cabinet        
            self.swap_rack_list.append(Swap_Rack(param=param, station_type=self.station_type, psc_num=psc_num_1, id=0))
            self.swap_rack_list.append(Swap_Rack(param=param, station_type=self.station_type, psc_num=psc_num_2, id=1))
            self.module_power = 60


        if self.station_type == "User_Defined":
            self.swap_period = int(param["swap_time"] * 60) 
            self.swap_rack_list.append(Swap_Rack(param=param, station_type=self.station_type, psc_num=int(self.psc_num), id=0))
            self.module_power = self.pss_type_dict["power_module_type"]["max_power"]

        self.set_temperature(rack_temperature = param["swap_rack_temperature"], env_temperature = param["swap_rack_temperature"]) #Default temperature 25 degrees

    def set_temperature(self, rack_temperature = 25, env_temperature = 25):
        '''
        set up environment temperature and rack temperature
        '''
        for swap_rack in self.swap_rack_list:
           if isinstance(swap_rack, Swap_Rack):
               swap_rack.set_sr_temperature(rack_temperature, env_temperature)
               self.rack_temperature = swap_rack.rack_temperature
               self.env_temperature = swap_rack.external_temperature

    def cal_battery_num(self):
        '''
        calculate batteries number
        '''
        self.battery_num = 0
        for swap_rack in self.swap_rack_list:
            self.battery_num += swap_rack.battery_num
        
    def load_battery_auto(self, battery : Battery):
        '''
        load batteries into rack list
        '''
        if isinstance(battery, Battery):
            for swap_rack in self.swap_rack_list:
                tmp = swap_rack.load_battery(battery)  
                if tmp >= 0:
                    logger.debug("Battery Loaded into SWAP_RACK # %d, Battery Rack # %d",swap_rack.id, tmp)
                    break
            if tmp == -1:
                print("No space to load battery")
        else:
            print("Unable to handle illegal battery object")
        self.cal_battery_num()

    def load_battery_target(self, battery : Battery, swap_rack_id, rack_id):
        '''
        load battery into target rack(rack_id)
        '''
        # if not isinstance(battery,Battery):
        #     return -1
        if battery is None:
            return -1
        if swap_rack_id > len(self.swap_rack_list) - 1 or swap_rack_id < 0:
            return -1
        if rack_id > self.swap_rack_list[swap_rack_id].max_rack_number - 1:
            return -1
        re = self.swap_rack_list[swap_rack_id].load_battery(battery, rack_id)
        self.cal_battery_num()
        return(re)

    def remove_battery_target(self, swap_rack_id, rack_id):
        '''
        remove battery from target rack(rack_id)
        '''
        if swap_rack_id > len(self.swap_rack_list) - 1 or swap_rack_id < 0:
            return -1
        if rack_id > self.swap_rack_list[swap_rack_id].max_rack_number - 1:
            return -1
        self.swap_rack_list[swap_rack_id].unload_battery(rack_id)
        self.cal_battery_num()

    def exchange_battery_target(self, battery : Battery, swap_rack_id, rack_id):
        '''
        remove the old battery in the rack, load new given battery into target rack_id
        '''
        if not isinstance(battery, Battery):
            return -1
        if swap_rack_id > len(self.swap_rack_list) - 1 or swap_rack_id < 0:
            return -1
        if rack_id > self.swap_rack_list[swap_rack_id].max_rack_number - 1:
            return -1        
        self.remove_battery_target(swap_rack_id, rack_id)
        self.load_battery_target(battery, swap_rack_id, rack_id)

    def switch_battery(self, source_swap_rack, source_rack, target_swap_rack, target_rack):
        '''
        switch the two batteries position btw source and target rack
        '''
        if source_swap_rack > len(self.swap_rack_list) - 1 or source_swap_rack < 0:
            return
        if target_swap_rack > len(self.swap_rack_list) - 1 or target_swap_rack < 0:
            return
        if source_rack > self.swap_rack_list[source_swap_rack].max_rack_number - 1:
            return           
        if target_rack > self.swap_rack_list[target_swap_rack].max_rack_number - 1:
            return                     
        if not isinstance(self.swap_rack_list[source_swap_rack].battery_rack_list[source_rack].battery, Battery):
            return
        if not isinstance(self.swap_rack_list[target_swap_rack].battery_rack_list[target_rack].battery, Battery):
            return
        # self.swap_rack_list[source_swap_rack].battery_rack_list[source_rack].stop_charge()
        # self.swap_rack_list[target_swap_rack].battery_rack_list[target_rack].stop_charge()
        self.swap_rack_list[source_swap_rack].stop_charge(source_rack)
        self.swap_rack_list[target_swap_rack].stop_charge(target_rack)
        
        temp_battery = self.swap_rack_list[source_swap_rack].battery_rack_list[source_rack].battery
        self.swap_rack_list[source_swap_rack].battery_rack_list[source_rack].battery = self.swap_rack_list[target_swap_rack].battery_rack_list[target_rack].battery
        self.swap_rack_list[target_swap_rack].battery_rack_list[target_rack].battery = temp_battery
        
        # self.swap_rack_list[source_swap_rack].battery_rack_list[source_rack].start_charge()
        # self.swap_rack_list[target_swap_rack].battery_rack_list[target_rack].start_charge()
        self.swap_rack_list[source_swap_rack].start_charge(source_rack)
        self.swap_rack_list[target_swap_rack].start_charge(target_rack)
        self.status = "switch"
        self.switch_timer = 0
        return

    def select_battery_rack(self, vehicle_battery : Battery, swap_target_soc):
        '''
        Automatically select battery rules:
             1. The battery type needs to be consistent vehicle_battery.batterytype -> This restriction is temporarily lifted
             2. The battery in the site reaches soc > swap_target_soc
             3. Optimize selection according to the charging and idle status of the warehouse
         Return value: None or corresponding rack object
        '''
        if not isinstance(vehicle_battery, Battery):
            return
        for swap_rack in self.swap_rack_list:
            for rack in swap_rack.battery_rack_list:
                if isinstance(rack.battery, Battery):
                    if rack.battery.soc >= swap_target_soc:
                    # if (rack.battery.batterytype == vehicle_battery.batterytype) and (rack.battery.soc >= swap_target_soc):
                        return rack

    def start_swap(self, vehicle_battery : Battery, swap_targetsoc) -> bool:
        '''
        start swapping behaviour, detect whether suitable battery exists
        Return value: True or False
        '''
        if self.status != "free":
            return False
        
        if isinstance(vehicle_battery, Battery): #If it is a legal battery
            self.buff_rack = self.select_battery_rack(vehicle_battery, swap_targetsoc)
            self.vehicle_battery = vehicle_battery
            if not isinstance(self.buff_rack, Battery_Rack):
                # logger.debug('can not find proper battery')
                return False
            # logger.debug("start swap timer start --- ")

            # init the swap timer, switch the status to "in use"
            self.swap_timer = 0
            self.status = "in_use"
            return True
        else:
            logger.error("illegel battery")
            return False
    
    ################################################################################
    ################################################################################
    def do_swap(self, current_user, t_timer, interval=1):
        '''
        swapping process
        grid interaction trigger will be calculated in form of list, when the counter
        not reaches max interaction num nor extend the time interval, it will be activated
        when the swap user utilizes the BSS, otherwise will this trigger == 0, we use trigger
        to detect whether we perform the grid interaction or not
        
        return value: True or False
        
        '''
        # case: Battery rack in switch operation
        if self.status == "switch":
            self.switch_timer += 1
            if self.switch_timer * interval >= 30:
                self.status = "free"
        
        # case: detect whether the time extend the grid interaction interval, if so the counter = max performed number
        if self.grid_interaction_timeStamp != None and self.grid_interaction_time_upper_limit != None:
            if t_timer > self.grid_interaction_time_upper_limit:
                self.grid_interaction_counter = self.interaction_num
        
        # case: swap platform in use status
        if self.status == "in_use":

            # establish the grid interaction trigger
            if self.grid_interaction_timeStamp != None:                         # condition1: the grid interaction activated
                if t_timer >= self.grid_interaction_timeStamp:                  # condition2: timestamp reaches into the grid interaction time interval
                    if self.grid_interaction_counter < self.interaction_num:    # condition3: the grid interaction times not extend max allowable number
                        self.trigger.append(1)                                  # if all conditions fullfilled, trigger activated as 1 otherwise 0
                    else:
                        self.trigger.append(0)
                else:
                    self.trigger.append(0)
            else:
                self.trigger.append(0)
            
            # swap time iteration
            self.swap_timer += 1

            if self.swap_timer * interval >= self.swap_period: #换电完成时的动作，交换车上和电池仓里的电池
                # load the vehicle battery, give the stored battery away, start charging new loaded battery
                self.buff_rack.stop_charge()
                temp_battery = self.vehicle_battery
                self.vehicle_battery = self.buff_rack.battery # give buff_rack battery to user
                self.buff_rack.battery = temp_battery         # load vehicle battery into buff_rack
                self.buff_rack.start_charge()
                if current_user is not None:
                    current_user.battery = self.vehicle_battery
                
                # init the swap setup
                self.vehicle_battery = None                     #Clear vehicle battery cache
                # total_time = self.swap_timer * interval
                self.swap_timer = 0                             #Clear the battery replacement timer
                self.status = "free"                            #Set the battery swap station status to idle
                # after first swap user (that after certain time stamp comes) finished service, counter up tp 1
                # if counter > 0 then the grid service deactivated.
                if self.grid_interaction_timeStamp != None:
                    if t_timer >= self.grid_interaction_timeStamp:
                        if self.grid_interaction_counter < self.interaction_num:
                            self.grid_interaction_counter += 1
                        else:
                            self.grid_interaction_counter = self.interaction_num
                
                return True
        
        else: #When there is no battery replacement, adjust the battery position in the battery compartment.
            self.trigger.append(0)
            if self.status != "switch":
                if (self.enable_me_switch > 0):
                    self.switch_in_rack()
                    if len(self.swap_rack_list) > 1 and self.enable_me_switch > 1:
                        self.switch_two_racks()
                        # logger.error('Swap between different swap racks -- Have not implemented')
                        pass
        
        return False
    
    ###################################################################################
    ###################################################################################
    def do_charge(self, timer, interval=1):
        self.power = 0
        for swap_rack in self.swap_rack_list:

            if self.power_dist_option == "BSS preferred":        
                swap_rack.power_distribution_pss_preferred()
            else:
                swap_rack.power_distribution_psc_preferred()  
             
            swap_rack.do_charge(timer, interval)
            self.power += swap_rack.get_power_sr()
        self.power_history.append([timer, self.power])
    
    ###################################################################################
    ###################################################################################
    def do_grid_interaction_discharge(self, timer, interval=1):
        '''
        perform the grid interaction discharge behaviours while a swap service is executing.
        '''
        self.power = 0
        for swap_rack in self.swap_rack_list:
            swap_rack.power_distribution_grid_interaction()
            swap_rack.do_grid_discharge(timer, interval)
            self.power += swap_rack.get_power_sr()
        self.power_history.append([timer, self.power])
    
    ###################################################################################
    ###################################################################################
    def init_charge(self):
        for swap_rack in self.swap_rack_list:
            swap_rack.select_soc = self.select_soc
            swap_rack.target_soc = self.target_soc
            if swap_rack.power_cabinet is not None:
                # logger.debug(swap_rack.power_cabinet)
                swap_rack.start_charge_all()
                if self.power_dist_option == "BSS preferred":        
                    swap_rack.power_distribution_pss_preferred()
                else:
                    swap_rack.power_distribution_psc_preferred()    

    def vehicle_charge(self, vb : Battery, pile_id = -1):
        # pile id = -1 indicates automatically connecting to an idle charging pile,
        # Returning -1 means there is no successful connection, returning 0-N means the charging pile ID to which it is connected.
        # For scenarios where more than 4 external charging piles are connected, or more than two swap racks can be connected to charging piles, pile_id = swap_rack_id * swap_rack_pile_number + pile_id
        if self.max_charge_terminal == 0:
            logger.info('No pile defined in this type of swap station')
            return -1
        if pile_id == -1:
            for sr in self.swap_rack_list:
                if sr.max_pile_number > 0:
                    for j in range(len(sr.charge_pile_list)):
                        if sr.connect_vehicle(vb, j) == j:
                            # logger.info('battery connected to pile number %d',j)
                            return j
        
            return -1

          
    def vehicle_stop_charge(self, vehicle_battery : Battery):
        if self.max_charge_terminal == 0:
            logger.info('No pile defined in this type of swap station')
            return -1
        
        for sr in self.swap_rack_list:                          # check each swap rack
            if sr.max_pile_number > 0:
                for j in range(len(sr.charge_pile_list)):
                    connected_battery = sr.charge_pile_list[j].vehicle_battery
                    if connected_battery == vehicle_battery:
                        sr.charge_pile_list[j].vehicle_leave()
                        return j
        return -1

    def switch_in_rack(self):
        '''
        rearrange the position of battery in the BSS according to the power distribution
        '''
        for sr in self.swap_rack_list:                      # Traverse all battery compartments (bss Type - 2 has two battery compartments, each with 10 battery bays)
            if sr.power_cabinet is not None:                # If the battery compartment is equipped with charging capabilities
                rack_n = len(sr.battery_rack_list)
                for i in range(rack_n):
                    if (i % 2) == 0:                        # at even number index of batteries
                        if sr.battery_rack_list[i].status == "charging": # battery status
                            if i + 1 < rack_n:
                                if sr.battery_rack_list[i + 1].status == "charging":
                                    for j in range(rack_n):
                                        if (j % 2) == 0 and j < rack_n - 1:
                                            if sr.battery_rack_list[j].status != "charging" and sr.battery_rack_list[j + 1].status != "charging":
                                                self.switch_battery(self.swap_rack_list.index(sr), i, self.swap_rack_list.index(sr), j)
                                                break
                                        if (j % 2) == 0 and j == rack_n - 1:
                                            if sr.battery_rack_list[j].status != "charging":
                                                self.switch_battery(self.swap_rack_list.index(sr), i, self.swap_rack_list.index(sr), j)
                                                break

    def switch_two_racks(self):
        '''
        For BSS Type - 2 600kW arrange the battery position btw rack with 
        charging ability and rack without charging ability
        '''
        # Case 1: for the case with only one swap_rack object (BSS Type - 1)
        if len(self.swap_rack_list) <= 1:
            return
        
        # Case 2: 600kW station
        if self.station_type == "GEN3_600":
            sr_b = self.swap_rack_list[1]        # rack unable to be charged
            sr_c = self.swap_rack_list[0]        # rack able to be charged
            rack_n = len(sr_b.battery_rack_list)
            for i in range(rack_n):
                # visit storage rack(unable to charge) to find a unfullcharged battery
                if sr_b.battery_rack_list[i].battery.soc < sr_b.target_soc:
                    # once find a unfull battery, then visit batteries at chargeable rack
                    for j in range(rack_n):
                        # find a full charged battery at chargeable rack
                        if sr_c.battery_rack_list[j].battery.soc >= sr_c.target_soc:
                            # switch 2 batteries
                            self.switch_battery(1,i,0,j)
                            break
                        # or find a empty position at chargeable rack
                        if sr_c.battery_rack_list[j].battery is None:
                            sr_c.battery_rack_list[j].battery = sr_b.battery_rack_list[i].battery
                            sr_b.battery_rack_list[i].battery = None              
                            break
        
        # Case 3: 1200kW station
        if self.station_type == "GEN3_1200":
            rack_n = len(self.swap_rack_list[0].battery_rack_list)
            for sr in self.swap_rack_list: #Traverse all battery compartments
                for i in range(rack_n):
                    if (i % 2) == 0: # even number of rack
                        if sr.battery_rack_list[i].status == "charging":
                            if i + 1 < rack_n:
                                if sr.battery_rack_list[i+1].status == "charging":
                                    find_flag = 0
                                    for sr_t in self.swap_rack_list:
                                        for j in range(rack_n):
                                            if (j % 2) == 0 and j < rack_n - 1:
                                                if sr_t.battery_rack_list[j].status != "charging" and sr_t.battery_rack_list[j+1].status != "charging":
                                                    self.switch_battery(self.swap_rack_list.index(sr), i, self.swap_rack_list.index(sr_t), j)
                                                    find_flag = 1
                                                    break
                                            if (j % 2) == 0 and j == rack_n - 1:
                                                if sr_t.battery_rack_list[j].status != "charging":
                                                    self.switch_battery(self.swap_rack_list.index(sr), i, self.swap_rack_list.index(sr_t), j)
                                                    find_flag = 1
                                                    break   
                                    if find_flag == 1:
                                        break 
