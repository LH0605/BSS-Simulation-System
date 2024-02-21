# -*- coding: UTF-8 -*-

import logging
import random
import string
import time
import numpy as np
import pandas as pd
import swap
from swap import Battery
import global_param

# set up the global param
GC = global_param.Global_Constant()
# set up logger
logger = logging.getLogger('main.users')
data_logger = logging.getLogger('data.users')


class User():

    def __init__(self, user_label) -> None:

        self.preference_distribution = {"charge":30,"swap":70,"leave":0} # by dafult setup of the user preference
        self.battery = None                 # save the battery instance object
        self.user_type = user_label         # user_type define the classification of BS & Non-BS user, "BS" indicates user belong to BS group, "non-BS" means user belongs to third party
        self.charge_preference = "swap"     # "swap": swap, "charge": charge, "leave": leave
        self.arrival_time = -1              #Set a counter to record the user arrival time, accurate to the number of seconds after the simulation starts, to generate a user queue, -1 means not to put it in the queue
        self.max_wait_number = 20           #Set a maximum waiting time. If the battery replacement does not start within this time, the user will leave the queue. Unit = number of people in the queue.
        self.max_charge_time = -1           #Set a maximum charging time parameter, from the beginning of charging to the end of charging. After this time, the user will stop charging and leave.
        self.min_charge_soc = 1             #Set the minimum SOC state that the user is willing to charge to. If it exceeds it, he will leave. The default is 100 (full).
        self.power_consumption = 20         #Set the user’s power consumption per 100 kilometers
        self.min_milage = -1                #Set the user's minimum satisfactory charging mileage. Based on powr_cosumption, you can calculate the minimum amount of electricity required. When min_milage is not equal to -1, calculate the smaller of min_charge_soc and min_milage.
        self.status = "waiting"             #"charging" is charging and occupies a charging terminal. "swaping" is exchanging battery and occupies a battery swap platform.
        self.timer = 0                      #Record the time the user is in a certain state, in seconds, and calculate the increment based on one simulation cycle.
        self.sequence = -1                  #Record the user's position in the user queue, which is the time the user arrives.
        self.swap_start_time = -1           #Record the user’s battery replacement start time
        self.swap_complete_time = -1        #Record the end time of user's battery replacement
        self.swap_service_time = -1         #Equal to swap_complete_time-sequence
        self.charge_connect_time = -1       #The time to connect to the charging pile, but not necessarily the time when charging starts
        self.id = -1                        #This is used to record the arrival time of users in the simulation time series of a day.
        self.connect_pile = None
        self.temp = 25

    def charge_service_time(self, mode = 1):   #mode = 1 returns charging plus queuing time; mode = 0 returns only charging time
        if mode == 1:
            # service time = charge time + waiting time
            tt = abs(self.battery.charge_start_time + len(self.battery.charge_history) - self.sequence)
        else:
            # mode == 0
            # only charge time
            tt = len(self.battery.charge_history)
        return tt

    ###################################################################################
    ###################################################################################    
    def swap_waiting_time(self):
        '''
        Returns the queuing time of the user's battery swap queue (starting battery swap time - entering the queue time)
        '''
        if self.charge_preference == "swap" and self.sequence != -1 and self.swap_start_time != -1:
            swap_waiting_t = self.swap_start_time - self.sequence
        else:
            swap_waiting_t == None
        return swap_waiting_t
    ###################################################################################
    ###################################################################################
    def charge_waiting_time(self):
        '''
        Returns the time period from when the user enters the queue to connecting to the charging pile
        '''
        if self.charge_preference == "charge" and self.sequence != -1 and self.charge_connect_time != -1:
            wait_time = self.charge_connect_time - self.sequence
        else:
            wait_time = None
        return wait_time
    ###################################################################################

    ###################################################################################
    def markov_preference(self, queue_length):
        '''
        Rearrange the user selection preference based on markov chain
        --> Modify: input temp, soc state, queue length
        '''
        x_state = ["swap", "charge", "leave"]
        x_prior = np.array([0.7, 0.25, 0.05],dtype=np.float64)
        Transition_matrix = np.array([[0.8, 0.1, 0.1],
                                      [0.1, 0.1, 0.8],
                                      [0.0, 0.0, 1.0]], dtype=np.float64)
        Observation_matrix = self.O_matrix_generation(self.temp, self.battery.soc, queue_length)
        x_1 = Observation_matrix.dot(Transition_matrix.dot(x_prior))    # one step forward procedure
        x_1 = x_1 / sum(x_1)
        x_1 = [round(s,2) for s in x_1]                                 # estimate probability
        ulist = [1, 2, 3]
        numb = get_number_by_pro(number_list = ulist, pro_list = x_1)
        
        self.charge_preference = x_state[int(numb)]                     # save as string
        return x_state[int(numb)]
    ###################################################################################
    ###################################################################################
    def O_matrix_generation(self, temp, soc_state, queue_len):

        if (temp>=5 and temp<=26) and soc_state>=0.4 and queue_len<=12:
            O_matrix = np.array([[0.5, 0.0, 0.0],[0.0, 0.4, 0.0],[0.0, 0.0, 0.1]],dtype=np.float64)
            return O_matrix
        
        if (temp<5 or temp>26) and soc_state>=0.4 and queue_len<=12:
            O_matrix = np.array([[0.7, 0.0, 0.0],[0.0, 0.2, 0.0],[0.0, 0.0, 0.1]],dtype=np.float64)
            return O_matrix

        if (temp>=5 and temp<=26) and soc_state<0.4 and queue_len<=12:
            O_matrix = np.array([[0.9, 0.0, 0.0],[0.0, 0.1, 0.0],[0.0, 0.0, 0.0]],dtype=np.float64)
            return O_matrix

        if (temp>=5 and temp<=26) and soc_state>=0.4 and queue_len>12:
            O_matrix = np.array([[0.6, 0.0, 0.0],[0.0, 0.3, 0.0],[0.0, 0.0, 0.1]],dtype=np.float64)
            return O_matrix

        if (temp<5 or temp>26) and soc_state<0.4 and queue_len<=12:
            O_matrix = np.array([[0.8, 0.0, 0.0],[0.0, 0.1, 0.0],[0.0, 0.0, 0.1]],dtype=np.float64)
            return O_matrix

        if (temp<5 or temp>26) and soc_state>=0.4 and queue_len>12:
            O_matrix = np.array([[0.3, 0.0, 0.0],[0.0, 0.3, 0.0],[0.0, 0.0, 0.4]],dtype=np.float64)
            return O_matrix

        if (temp>=5 and temp<=26) and soc_state<0.4 and queue_len>12:
            O_matrix = np.array([[0.6, 0.0, 0.0],[0.0, 0.2, 0.0],[0.0, 0.0, 0.2]],dtype=np.float64)
            return O_matrix

        if (temp<5 or temp>26) and soc_state<0.4 and queue_len>12:
            O_matrix = np.array([[0.7, 0.0, 0.0],[0.0, 0.1, 0.0],[0.0, 0.0, 0.2]],dtype=np.float64)
            return O_matrix
    ###################################################################################
    ###################################################################################
    def full_swap_preference(self):
        self.charge_preference = "swap"
        return
    ###################################################################################
    ###################################################################################
    def full_charge_preference(self):
        self.charge_preference = "charge"
        return
    ###################################################################################
    ###################################################################################
    def fixed_preference(self, swap_ratio:int):
        '''
        Rearrange the user selection preference
        '''
        # self.preference_distribution = pref_dist # reset the probability of user selection
        if swap_ratio == -1:
            logger.error("this preference mode is not selected")
            return
        else:
            self.preference_distribution["swap"] = swap_ratio
            self.preference_distribution["charge"] = 100 - swap_ratio
            self.preference_distribution["leave"] = 0
        
        tt = self.preference_distribution["charge"] + self.preference_distribution["swap"] + self.preference_distribution["leave"]
        
        if tt != 100:
            logger.error('preference distribution need to sum up to 100 (%d)',tt)
            return 
        pref_c = ["swap", "charge", "leave"]
        
        # ulist = range(1, 5)
        ulist = [1, 2, 3] # 1, 2, 3, 4
        plist = [self.preference_distribution["swap"] / 100, self.preference_distribution["charge"] / 100, 
                self.preference_distribution["leave"] / 100]
        numb = get_number_by_pro(number_list = ulist, pro_list = plist)
        # data_logger.debug(int(numb))
        self.charge_preference = pref_c[int(numb)] # save as string
        return pref_c[int(numb)]
    ###################################################################################
    ###################################################################################
    def create_battery(self, battery_config : dict, soc_low_limit = 0.0, soc_up_limit = 1.0, random_soc = 0) -> bool: 
        '''
        Generate the user initial battery with selected generation mode:
        Mode 1 (random_soc = 0): configurate the initial SOC based on real data distribution, namely gamma distribution
        Mode 2 (random_soc = 1): configurate the initial SOC based on real data distribution, but with gaussian distribution (centriod mu and sigma)
        Mode 3 (random_soc = 2): configurate the initial SOC based on uniform distribution
        '''
        # # set up the battery type by ratio in the battery_config dict
        if len(battery_config) ==2:
            ratio = list(battery_config.values())[0] / sum(list(battery_config.values()))
            # set up a flag value that compare with the ratio in order to confirm the battery type
            flag = random.random()
            # Here currently only allows 2 type of battery configuration -> 100 kWh and 75 kWh
            if flag <= ratio:
                # first type of battery
                battery_type = list(battery_config.keys())[0]
            else:
                # second type of battery
                battery_type = list(battery_config.keys())[1]
        else:
            ratio1 = list(battery_config.values())[0] / sum(list(battery_config.values()))
            ratio2 = list(battery_config.values())[0] + list(battery_config.values())[1] / sum(list(battery_config.values()))
            flag = random.random()
            # Here currently only allows 2 type of battery configuration -> 100 kWh and 75 kWh
            if flag <= ratio1:
                # first type of battery
                battery_type = list(battery_config.keys())[0]
            elif flag > ratio1 and flag <= ratio2:
                # second type of battery
                battery_type = list(battery_config.keys())[1]
            else:
                battery_type = list(battery_config.keys())[2]
        
        # check the validity of soc configuration
        if battery_type not in ["70kWh", "75kWh", "100kWh", "60kWh", "40kWh"]:
            logger.error('invalid battery type %s',battery_type)
            return False
        if soc_up_limit > 1.0:
            logger.debug('invalid battery soc limit: %.2f --> set soc to 1.0',soc_up_limit)
            soc_up_limit = 1.0
        if soc_low_limit < 0.0:
            logger.debug('invalid battery soc limit: %.2f --> set soc to 0.0',soc_low_limit)
            soc_low_limit = 0.0
        
        if random_soc == 0:
            # set up the clients initial soc based on real statistic data -> Gamma distribution
            shape, scale = 3.0, 12.0
            input_soc = random.gammavariate(shape, scale)
            input_soc = round(input_soc/100, 2)

        elif random_soc == 1:
            # set up the clients initial soc based on real statistic data -> Gaussian distribution
            input_soc = random.normalvariate(mu=33.13, sigma=18.71)
            input_soc = round(input_soc/100, 2)
        else:
            # set up the clients initial soc based on Uniform distribution (Not recommend!!!)
            input_soc = random.uniform(soc_low_limit, soc_up_limit)
            input_soc = round(input_soc, 2)
        
        # check the validity of battery initial soc value
        if input_soc > soc_up_limit:
            input_soc = soc_up_limit
        elif input_soc < soc_low_limit:
            input_soc = soc_low_limit
        else:
            pass

        self.battery = Battery(input_soc, battery_type)
        # logger.debug('One %s battery created with soc = %.2f',battery_type,self.battery.soc)
        return True

###########################################################################################
################################### END of Class ##########################################
###########################################################################################




def create_user_queue_random(BS_user_num : int, non_BS_user_num : int): 
    '''
    use the user_random_dist.dat file to generate the user arrive time distribution
    '''
    if BS_user_num <= 0:
        logger.error('should create a user queue larger than 0')
    
    # # read the dat file from data folder
    # abspath = os.getcwd()
    # abspath = os.path.join(abspath,"data")
    # file_list = os.listdir(abspath)
    # data_name = None
    # for item in file_list:
    #     if item == "user_random_dist.dat":
    #         data_name = item
    #         break
    # data_file_path = os.path.join(abspath, data_name)
    data_file_path = "data/user_random_dist.dat"
    # pack and sort the BS & non BS user queue 
    BS_user_list = get_user_distribution(data_file_path, BS_user_num)            # return timestamp list of BS user arrive time
    non_BS_user_list = get_user_distribution(data_file_path, non_BS_user_num)    # return timestamp list of non BS user arrive time

    BS_queue, non_BS_queue = label_queue(BS_user_list, non_BS_user_list)
    sorted_queue, sorted_label = sort_queue(BS_queue, non_BS_queue)

    return sorted_queue, sorted_label


def create_user_queue_random_opening(BS_user_num: int, non_BS_user_num: int):
    '''
    use the user_random_dist.dat file to generate the user arrive time distribution
    '''
    if BS_user_num <= 0:
        logger.error('should create a user queue larger than 0')

    # # read the dat file from data folder
    # abspath = os.getcwd()
    # abspath = os.path.join(abspath,"data")
    # file_list = os.listdir(abspath)
    # data_name = None
    # for item in file_list:
    #     if item == "user_random_dist.dat":
    #         data_name = item
    #         break
    # data_file_path = os.path.join(abspath, data_name)
    data_file_path_opening = "data/user_random_dist_opening.dat"
    # pack and sort the BS & non BS user queue
    BS_user_list = get_user_distribution_opening(data_file_path_opening,BS_user_num)  # return timestamp list of BS user arrive time
    non_BS_user_list = get_user_distribution_opening(data_file_path_opening,non_BS_user_num)  # return timestamp list of non BS user arrive time

    BS_queue, non_BS_queue = label_queue(BS_user_list, non_BS_user_list)
    sorted_queue, sorted_label = sort_queue(BS_queue, non_BS_queue)

    return sorted_queue, sorted_label

    ###################################################################################
    ###################################################################################
def create_user_queue_statistical(area : string, non_BS_user_num : int): 
    '''
    Queue generation mode "real data"
    Generate the user input distribution based on real data (saved under "data" folder)
    Input: 
        data file with ending "*.dat", data format: "2020-07-01 00:28:44", which recorded users arrive time within 24 hours
        area: string that indicates which area will be used for simulation, urban or suburb/highway
    Output:
        time stamp list (in sec) that refered to 00:00:00
    '''
    # Prepare the Non BS user generation file, read the file path
    # abspath = os.getcwd()
    # abspath = os.path.join(abspath,"data")
    # file_list = os.listdir(abspath)
    # data_name = None
    # for item in file_list:
    #     if item == "user_random_dist.dat":
    #         data_name = item
    #         break
    # data_file_path = os.path.join(abspath, data_name)
    data_file_path = "data/user_random_dist.dat"
    
    # use statistics to generate BS user arrive time queue
    if area == "urban":
        file_list = GC.user_dist_urban_file_list                        # get the user distribution file name list for urban
    else:
        file_list = GC.user_dist_highway_file_list                      # get the user distribution file name list for highway
    selection_flag = random.randint(0, len(file_list) - 1)              # generate a random number for selection of file
    file_address = "data/" + file_list[selection_flag]                  # select file and save the reading address

    seq = read_sequence(file_address)                                  # Read time sequence file "*.dat", return string list
    basic = get_time_stamp(seq[0].split(" ")[0]+" 00:00:00")            # Read first line date + 00:00:00 -> return in sec as start point
    for i, v in enumerate(seq):                                         # Calculate: all time stamp in queue - start point sec == sec after start point
        seq[i] = get_time_stamp(v) - basic

    del seq[0:18]

    BS_user_list = [int(c) for c in seq]                                          # return int list of all queue input time (sec relative to start point)
    non_BS_user_list = get_user_distribution(data_file_path, non_BS_user_num)    # return timestamp list of non BS user arrive time

    BS_queue, non_BS_queue = label_queue(BS_user_list, non_BS_user_list)       # return two dicts with label BS and non_BS
    sorted_queue, sorted_label = sort_queue(BS_queue, non_BS_queue)              # sort the two dict by time

    return sorted_queue, sorted_label
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
def label_queue(BS_list:list, non_BS_list:list):
    '''
    labeling and packaging the BS and non-BS queue into dict
    '''
    BS_user_num = len(BS_list)
    non_BS_user_num = len(non_BS_list)
    BS_user_label = []
    non_BS_user_label = []
    for i in range(BS_user_num):
        BS_user_label.append("BS")
    for i in range(non_BS_user_num):
        non_BS_user_label.append("non_BS")
    
    BS_queue_dict = {
        "time" : BS_list,
        "label" : BS_user_label
    }
    non_BS_queue_dict = {
        "time" : non_BS_list,
        "label" : non_BS_user_label
    }
    return BS_queue_dict, non_BS_queue_dict
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
def sort_queue(queue1:dict, queue2:dict):
    '''
    sort the two queues dict with key name: "time", "label"
    sort by ["time"]
    '''
    queue1 = pd.DataFrame(queue1)
    queue2 = pd.DataFrame(queue2)
    dt_total = [queue1, queue2]
    dt_total = pd.concat(dt_total)
    sorted_dt = dt_total.sort_values(by=["time"])
    
    # get the sorted queue and label in format list
    sorted_queue = list(sorted_dt["time"])
    sorted_label = list(sorted_dt["label"])

    return sorted_queue, sorted_label

def get_time_stamp(time_str):
    """
    Reform the datetime into sec relative to 1970.1.1 00:00:00
    Input format: "%Y-%m-%d %H:%M:%S"
    Output format: Integer in sec unit
    """
    timeArray = time.strptime(time_str, "%Y-%m-%d %H:%M:%S")            # reform the time string as time struct
    timeStamp = int(time.mktime(timeArray))                             # calculate the time stamp in sec by using given time struct
    return timeStamp

def read_sequence(file_name):
    """
    Read the "*.dat" user queue date time file, save it as string list 
    """
    if file_name is None:
        logger.error('file not specified')
        return
    with open(file_name) as f:
        lines = f.read().splitlines()
        return lines

def check_seq(tick, interval, user_dist_list, user_label):
    '''
    check how many users in the interval reached
    Argumentation:
    tick: sim_tick, number of iteration within sim_days
    interval: sim_interval in sec
    seq: user queue

    return the list of user number within the given interval, index of list = sec solution, value = number of users
    '''
    service_list = []
    service_label = []

    for i in range(tick * interval, (tick + 1) * interval):
        if user_dist_list.count(i) > 0:
            ind = [x for x,y in list(enumerate(user_dist_list)) if y==i] # return the index list of corresponding timestamp of i
            for j in range(user_dist_list.count(i)):
                service_list.append(i)                                   # load the timestamp at current iteration
            for s in range(len(ind)):
                service_label.append(user_label[ind[s]])                 # load the label at current iteration
    
    if len(service_list) != len(service_label):
        logger.error("the length of user list and label list not identical, check check_seq() function")
        return
    else:
        return service_list, service_label

def get_number_by_pro(number_list, pro_list):
    """
    定义从一个数字列表中以一定的概率取出对应区间中数字的函数
    param number_list:数字列表
    param pro_list:数字对应的概率列表
    return:按概率从数字列表中抽取的数字
    """
    # 用均匀分布中的样本值来模拟概率
    x = random.uniform(0, 1)
    num = x
    # 累积概率
    sum_pro = 0.0
     # 将可迭代对象打包成元组列表
    for number, number_pro in zip(number_list, pro_list):
        sum_pro += number_pro
        if x < sum_pro:
     # 从区间[number. number - 1]上随机抽取一个值
            num = np.random.uniform(number, number - 1)
     # 返回值
            return num
    return num
    
def get_user_distribution(file_name, daily_user):
    """
    user distribution generation -> random mode
    """

    # case of No file
    if file_name is None:
        logger.error('file not specified')
        return None
    
    with open(file_name) as f:
        lines = f.read().splitlines()
        if len(lines) != 48:
            logger.error('this is not a correct distribution data format(should be 48 float)')
            return None
        ret_i = []
        sum_i = 0
        for i in lines:
            b = float(i)
            ret_i.append(b/100.0)
            sum_i = sum_i + b

        num_list = range(1,49)
        final_list = []
        for i in range(daily_user):
            n = get_number_by_pro(number_list=num_list, pro_list=ret_i)
            n = n / 2.0 * 60.0 * 60.0
            final_list.append(int(n))
        final_list.sort()
        return final_list


# Fixed by Hao
def get_user_distribution_opening(file_name, daily_user):
    """
    user distribution generation -> random mode
    """

    # case of No file
    # if file_name is None:
    #     logger.error('file not specified')
    #     return None
    #
    with open(file_name) as f:
        lines = f.read().splitlines()
        if len(lines) != 48:
            logger.error('this is not a correct distribution data format(should be 48 float)')
            return None
        ret_i = []
        sum_i = 0
        for i in lines:
            b = float(i)
            ret_i.append(b / 100.0)
            sum_i = sum_i + b

        num_list = range(1, 49)
        final_list = []
        for i in range(daily_user):
            n = get_number_by_pro(number_list=num_list, pro_list=ret_i)
            n = n / 2.0 * 60.0 * 60.0
            final_list.append(int(n))
        final_list.sort()
        return final_list
