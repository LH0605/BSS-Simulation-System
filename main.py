# -*- coding: UTF-8 -*-

import logging
import logging.config
import swap
import users
import queue
from swap import Battery, SwapStation
import global_param
import numpy as np
import pandas as pd

# GP = global_param.Global_Parameter()
GC = global_param.Global_Constant()

logger = logging.getLogger('main')
data_logger=logging.getLogger('data')


def log_data(station : swap.SwapStation, t_timer : int):
    '''
    log the simulation data in form of [time, power]
    '''
    data = ""
    data = data + 'timer<%d>, ' %t_timer
    for sr in station.swap_rack_list:
        for br in sr.battery_rack_list:
            if br.battery is not None:
                pass

        if sr.power_cabinet is not None:
            for module in sr.power_cabinet.module_list:
                if module.status == "in_use":
                    pass

    data = data + '%d' %station.power

    if len(data) > 0:
        # data = data +'%d' %t_timer
        data_logger.debug(data)    
        pass

def simulation_action_callback(station : swap.SwapStation, t_timer : int, interval : int, current_user : users.User):
    '''
    参数说明：
    station:        SwapStatin Class, representing the battery swap station entity used for simulation
    t_timer:        int, which is the current simulation cycle block, usually counter i                               -> from range(sim_ticks)
    interval:       int，is the current simulation period, in seconds, interval = 10 indicates a simulation step of 10 seconds      -> sim_interval
    current_user:   current user object in the BSS
    '''
    swap_result = station.do_swap(current_user, t_timer, interval)               # operate the swap behaviour, return True or False
    if station.trigger[-1] == 0:                                                                  # if grid interaction not activated -> do normal charge
        station.do_charge(t_timer, interval)
    else:                                                                                 # if grid interaction activated -> do discharge
        station.do_grid_interaction_discharge(t_timer, interval)
    
    log_data(station, t_timer)                                                            # logging the data
    
    return swap_result

def add_users(param: dict, station : swap.SwapStation, user_dist_list : list, user_label : list, swap_queue, charge_queue, BS_charge_list : list, non_BS_charge_list : list, t_timer : int, interval : int):
    '''
    This function is used in a simulation cycle. The function checks the preset user arrival sequence. 
    If a user arrives during the current simulation period, a user will be generated and added to the battery swap station queue sequence.
    Type parameter description:
    station:                SwapStatin Class, representing the battery swap station entity used for simulation
    user_dist_list:         The int list defines a sorted sequence according to 24 * 60 * 60 seconds every day, and defines the time sequence of user arrival user_sequence
                            Generally, it is generated before simulation through users.create_user_queue_random() function or users.create_user_statistical() function.
    user_label:             User category list, indicating whether the user is a BS or non_BS user
    swap_queue:             Battery swap station queuing queue, first in first out queue, defined by the main program, passed in as a parameter
    BS_charge_list:        Charging queue list, list form, main program definition, passed in as a parameter
    non_BS_charge_list:    Charging queue list (non-BS users), list form, main program definition, passed in as a parameter
    t_timer:               int, which is the current simulation cycle time point, usually counter i (= user arrival time)
    interval:              int, which is the simulation cycle step size, the unit is seconds, interval=10 indicates a simulation step size of 10 seconds
    '''

    # Check whether there are users who need service in the current time interval. service_n returns the timestamp list of user arrivals in the current iteration. label_n returns the category of the user.
    # Indicates how many users arrive in a simulation cycle. Note that more than one user may arrive in a simulation cycle.
    service_n, label_n = users.check_seq(t_timer, interval, user_dist_list, user_label)
    
    if len(service_n) > 0: #If more than one user arrives
        for i in range(len(service_n)):
            user_id = service_n[i]
            user_label = label_n[i]
            user = users.User(user_label=user_label)                                    # Create a user
            
            user.sequence = t_timer                                                     # Assign the timer when the user arrives to sequence as the time point when the user enters the queue.
            user.user_id = user_id

            if user.user_type == "non_BS":                                             # for Non-BS user, they can only select the charge service
                user.create_battery(battery_config=param["battery_config"], soc_low_limit = 0.05,\
                 soc_up_limit = 0.9, random_soc = 1)                                    # Add a user battery random_soc = 1 -> Gaussian distribution
                user.full_charge_preference()
            else:                                                                       # for BS user, they perform required selection preference
                user.create_battery(battery_config=param["battery_config"], soc_low_limit = 0.05,\
                 soc_up_limit = 0.9, random_soc = 0)                                    # Add a user battery random_soc = 0 -> Gamma distribution
                if param["user_preference"] == "full_swap":
                    user.full_swap_preference()
                elif param["user_preference"] == "fixed_value":
                    user.fixed_preference(param["service_ratio"])
                else:
                    # if param["user_preference"] == "markov"
                    # calculate the current waitting list length
                    queue_length = int(swap_queue.qsize() + charge_queue.qsize())
                    user.markov_preference(queue_length)

            # set up the temperature
            user.battery.temperature = param["swap_rack_temperature"]

            # put user into different queue according to their selection preference
            if user.charge_preference == "swap":
                swap_queue.put(user)
                logger.debug('timer<%d>: push user %d into swap queue', t_timer , user_id)

            if user.charge_preference == "charge":
                charge_queue.put(user)

            if user.charge_preference == "leave":
                logger.info("timer<%d>: User %d abandons the service and chooses to leave" ,t_timer, user.user_id)

    ###################################################################################
    ############################## Simulation Loop ####################################
    ###################################################################################
def do_simulation(param):
    '''
    excute the simulation loop of the BSS
    '''
    ###################################################################################
    ##################### Part 1: Simualtion parameters setting #######################
    ###################################################################################
    sim_days = param["sim_days"]                                # define simulation days in int (by dafult 1)
    sim_interval = param["sim_interval"]                        # define the simulation step in int, unit 1 sec
    sim_ticks = param["sim_ticks"]                              # define the total simulation bins    
    station1 = SwapStation(param)                               # setup Swap station instance 

    # battery_actual_num = sum(list(param["battery_config"].values()))
    # if battery_actual_num != station1.max_battery_number:       # check the battery num configuration
    #     logger.error("battery num not identical, check battery_config")
    #     return
    
    # load the batteries into the swap rack
    for i in param["battery_config"].items():
        for num in range(i[1]):                                 # i[1] = num of each battery type
            station1.load_battery_auto(Battery(soc=param["init_battery_soc_in_BSS"], batterytype=i[0])) # i[0] = battery type

    station1.init_charge()                                      # init the BSS charge modules, set select soc
    station1.set_temperature(rack_temperature=25, env_temperature=25)
    
    if param["user_sequence_mode"] == "random" and param["opening_hours"] == "24 hours":
        # queue generation mode "random"
        BS_user_num = param["BS_user_num"]                    # define the number of daily BS clients
        non_BS_user_num = param["non_BS_user_num"]            # define the number of daily non BS clients
        user_dist_lst, user_label = users.create_user_queue_random(BS_user_num, non_BS_user_num)        # 根据user_distribtion.dat定义的分布规律，生成一个用户列表，user_dist_lst 记录用户到达的timestamp
    elif param["user_sequence_mode"] == "random" and param["opening_hours"] == "9:00 to 19:30":
        # queue generation mode "random"
        BS_user_num = param["BS_user_num"]                    # define the number of daily BS clients
        non_BS_user_num = param["non_BS_user_num"]            # define the number of daily non BS clients
        user_dist_lst, user_label = users.create_user_queue_random_opening(BS_user_num, non_BS_user_num)
    else:
        # queue generation mode "statistical"
        area = param["user_area"]
        non_BS_user_num = param["non_BS_user_num"] 
        user_dist_lst, user_label = users.create_user_queue_statistical(area=area, non_BS_user_num = non_BS_user_num) # 根据GC中的user_dist_file_list列表中的文件(data文件夹下)，随机选取一个定义的一天内到达时间生成用户序列

    # change and modify the charge list into queue object
    swap_queue = queue.Queue()                                  # define a FIFO queue object used for manage waiting clients, command: ".put()", ".get()"
    charge_queue = queue.Queue()                                # define a FIFO queue for charging service
    BS_charge_list = []                                        # save for BS charged clients (BSC)
    non_BS_charge_list = []                                    # save for non_BS charged clients (BSC)
    swap_list = []                                              # save for swap serviced clients (BSS)
    swap_user = None                                            # save for swap user object in the queue
    charge_user = None                                          # save for charge user object
    queue_length_swap = []                                      # save for queue length notation of swap
    queue_length_charge = []                                    # save for queue length notation of charge
    swap_user_wait_time = []
    charge_user_wait_time = []
    
    ###################################################################################
    ########################### Part 2: Simualtion Loop ###############################
    ###################################################################################
    logger.info('start_simulatin')
    
    # interation every 10 sec for 24hrs (8640 interation steps)
    for i in range(sim_ticks):
        
        #Check whether any user has arrived during the current simulation cycle. If so, add the user to service_queue.
        add_users(param, station1, user_dist_lst, user_label, swap_queue, charge_queue, BS_charge_list, non_BS_charge_list, i, sim_interval) 
        # calculate the queue length for two group
        queue_length_swap.append(swap_queue.qsize())
        queue_length_charge.append(charge_queue.qsize())     

        # process 1: No current servicing client, but there exists clients in the waiting queue
        if swap_user is None and swap_queue.qsize() > 0: 
            swap_user = swap_queue.get()
            logger.debug('timer<%d>: Set Swap User No. (%d), total %d users remains in waitlist', i, swap_user.user_id, swap_queue.qsize())
        
        if charge_user is None and charge_queue.qsize()> 0:
            charge_user = charge_queue.get()
        
        # process 2: there exists client in the service
        if swap_user is not None:
            if station1.start_swap(swap_user.battery, swap_targetsoc = param["select_soc"]):
                logger.debug('timer<%d>: User #%d start swap',i, swap_user.user_id)
                swap_user.swap_start_time = i
                swap_user_wait_time.append(swap_user.swap_waiting_time())
        
        if charge_user is not None:
            charge_user.battery.target_max_soc = param["target_soc"]   #Defines the maximum SOC the user wishes to achieve
            pile_id = station1.vehicle_charge(charge_user.battery)      #Try to connect the user to a charging station  
            # case 1: successful connect to a charge pile
            if pile_id >= 0: 
                charge_user.charge_connect_time = i
                charge_user.connect_pile = pile_id
                charge_user_wait_time.append(charge_user.charge_waiting_time())
                # devide the charge list into BS and non_BS user list
                if charge_user.user_type == "BS":
                    BS_charge_list.append(charge_user)
                else:
                    non_BS_charge_list.append(charge_user)
                logger.debug('timer<%d>: Connect user %d to charge pile %d', i , charge_user.user_id, pile_id)
                charge_user = None
            # case 2: failed to connect to a charge pile
            else:
                # charge user waiting for a place
                pass
                # logger.info('timer<%d>: User %d can not find free charger,user left', i , user.id)
        
        # process 3: clients who select swap
        swaptrigger = simulation_action_callback(station1, i, sim_interval, swap_user) # user -> do_swap & batteries in hotel charge
        if swaptrigger == True: #执行仿真周期内需要完成的动作 do_swap, do_charge
            logger.debug('timer<%d>: User #%d complete swap', i, swap_user.user_id)
            swap_user.swap_complete_time = i
            swap_user.swap_service_time = i - swap_user.sequence
            swap_list.append(swap_user)
            swap_user = None
        

        
    ###################################################################################
    ##################### Part 3: Data Analysis & Plot ################################
    ###################################################################################

    # Here calculate the total number of swap/charge clients
    logger.info('Total swap user %d', len(swap_list))
    logger.info('Total charge user %d', len(BS_charge_list) + len(non_BS_charge_list))
    
    # calculate the average charge service time for BS user
    if len(BS_charge_list) > 0:
        c_average_time = 0
        for charge_user in BS_charge_list:
            c_average_time += abs(charge_user.charge_service_time())
        logger.info('Average charge service time (BS user) = %.2f', (c_average_time / len(BS_charge_list)) * sim_interval / 60.0)    
        BS_average_time_charge = (c_average_time / len(BS_charge_list)) * sim_interval / 60.0
    else:
        c_average_time = 0
        BS_average_time_charge = 0
    
    # Here calculate the average charge service time for Non BS user
    if len(non_BS_charge_list) > 0:
        c_average_time_non_BS = 0
        for charge_user in non_BS_charge_list:
            c_average_time_non_BS += abs(charge_user.charge_service_time())
        logger.info('Average charge service time (Non BS user) = %.2f', (c_average_time_non_BS / len(non_BS_charge_list)) * sim_interval / 60.0)    
        non_BS_average_time_charge = (c_average_time_non_BS / len(non_BS_charge_list)) * sim_interval / 60.0
    else:
        c_average_time_non_BS = 0
        non_BS_average_time_charge = 0

    # Here calculate the average swap service time
    if len(swap_list) > 0:
        s_average_time = 0
        for swap_user in swap_list:
            s_average_time += swap_user.swap_service_time
        logger.info('Average swap service time = %.2f', (s_average_time / len(swap_list)) * sim_interval / 60.0)
        average_time_swap = (s_average_time / len(swap_list)) * sim_interval / 60.0
    else:
        average_time_swap = 0
    
    # Here calculate the residual power distribution
    residual_power = []
    for pw in station1.power_history:
        residual_temp = station1.max_power - pw[1]
        residual_power.append(residual_temp)
    
    # Here calculate the success ratio within 15 min for swap
    swap_time_list = []
    count = 0
    for i in range(sim_ticks):
        for user in swap_list:
            if user.sequence == i:
                swap_time_list.append(user.swap_service_time * sim_interval / 60.0)
                break
    for num in swap_time_list:
        if num <= 15:
            count += 1
    
    if len(swap_time_list) > 0:
        # ratio = successful count / (serviced number of user + unserviced overflow number of user)
        swap_ratio_in_15_min = count / (len(swap_time_list) + queue_length_swap[-1])
    else:
        swap_ratio_in_15_min = 0
    
    # Here calculate the wait time into [minutes]
    swap_user_wait_time = [s * sim_interval/60 for s in swap_user_wait_time]
    charge_user_wait_time = [s * sim_interval/60 for s in charge_user_wait_time]

    return swap_user_wait_time, charge_user_wait_time, queue_length_swap, queue_length_charge, user_dist_lst, station1.max_power, station1.power_history, residual_power, swap_list, BS_charge_list, \
        non_BS_charge_list, average_time_swap, BS_average_time_charge, non_BS_average_time_charge, swap_ratio_in_15_min

