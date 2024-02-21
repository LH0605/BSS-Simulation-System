# -*- coding: UTF-8 -*-

##################################
######## Import packages #########
##################################
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.pyplot import MultipleLocator
import datetime
from datetime import datetime as dt
import streamlit as st
from PIL import Image
import pandas as pd
import numpy as np
import random

# import the model and global parameters
import main
import global_param
GC = global_param.Global_Constant()

##################################
##### Function Declaration #######
##################################

# function for calculating the energy consumption
# @st.cache
def energy_calc(power, time_interval):
    energy = 0
    for i in range(len(power)):
        energy += time_interval * power[i] / 3600 # kWh
    return energy

# calculate the area user number, divide them randomly to the respective stations
#@st.cache
def areaNumDivision(station_num, area_user_num):
    result = []
    remain = station_num
    max_num = int((area_user_num / station_num) * 1.5) # upper limit of each slice
    min_num = int((area_user_num / station_num) * 0.5) # lower limit of each slice
    for i in range(station_num):
        remain -= 1
        if remain > 0:
            if remain <= area_user_num: # num of area user >= num of remaining station num
                slice_num = random.randint(min_num, min(area_user_num - remain, max_num))
            else:
                slice_num = random.randint(0, area_user_num)
        else: # if all number of user divided, then rests are 0
            slice_num = area_user_num
        result.append(slice_num)
        area_user_num -= slice_num
    return result # return the sliced number list

# convert the dataframe into csv format
#@st.cache
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

##################################
######## Set up Web config #######
##################################

################################################################################
##################### Part 0: Set up Web Notation ##############################
################################################################################
st.title("BSS Interactive Tech-Platform (BIT)")
# with right_col:
#     st.image(logo)
st.markdown("This application is used to analyze the service ability of Battery Swap Station, and is used to assist clients in customizing services. \
             The current version is an initial beta version only. All simulation results are only virtual test data, and this software is not responsible for any results.")

image = Image.open('image/image.png')
st.image(image)
st.write("")
###############################################################################
######################### Part 1: Set up App Layout ###########################
###############################################################################

# for main page
st.markdown("# Step 1: BSS configuration")
tab1, tab2 = st.tabs(["Single Station", "Multiple Stations"])
with tab1:
    col_l1, col_r1 = st.columns(2)
    col_l2, col_r2 = st.columns(2)
    col_l3, col_r3 = st.columns(2)
    col_l4, col_r4 = st.columns(2)
    col_l5, col_r5 = st.columns(2)
    col_l6, col_r6 = st.columns(2)
    col_l7, col_r7 = st.columns(2)
    col_lnew, col_rnew = st.columns(2)
    
    st.markdown("# Step 2: Simulation Initiation")
    st.write("Press the button to start the simulation")
    _, col_m1, _ = st.columns(3)
    success_info_single_station = st.container()
    single_station_result = st.container()

with tab2:
    col_l8, col_r8   = st.columns(2)
    col_l9, col_r9   = st.columns(2)
    col_l10, col_r10 = st.columns(2)
    col_l11, col_r11 = st.columns(2)
    col_l12, col_r12 = st.columns(2)
    col_l13, col_r13 = st.columns(2)
    col_l14, col_r14 = st.columns(2)
    col_l15, col_r15 = st.columns(2)
    col_l16, col_r16 = st.columns(2)
    col_l17, col_r17 = st.columns(2)
    st.markdown("# Updates in the future")

    _, col_m2, _ = st.columns(3)
    success_info_multiple_station = st.container()
    multiple_station_result = st.container()


###############################################################################
######################### Part 2: Single station Set up #######################
###############################################################################
with col_l1: # BSS type
    st.write("")
    st.markdown("### BSS Type")
    bss_candidates = ["BSS Type-1 - 500kW", "BSS Type-2 V1 - 600kW", "BSS Type-2 V2 - 1200kW", "User Defined"]
    tab3, tab4, tab5 = st.tabs(["BSS Type", "Swap Time", "Power Module"])
    with tab3: # BSS Type
        type_bss = st.selectbox("Select the Battery Swapping Station(BSS) type", bss_candidates, index=0)
        if type_bss == "BSS Type-1 - 500kW":
            station_type = GC.GEN2_530kW
            default_swap_time = 6.5
        elif type_bss == "BSS Type-2 V1 - 600kW":
            station_type = GC.GEN3_600kW
            default_swap_time = 4.5
        elif type_bss == "BSS Type-2 V2 - 1200kW":
            station_type = GC.GEN3_1200kW
            default_swap_time = 4.5

        else:
            station_type = GC.User_Defined
            default_swap_time = 3.0
    with tab4: # Swap Time
        min_swap_time = 3.0
        max_swap_time = 10.0
        swap_time = st.slider("Set up the swap time of each swapping user [min]", min_value=min_swap_time, max_value=max_swap_time, value=default_swap_time, step=0.1)
    with tab5: # Power Module
        if type_bss == "User Defined":
            pm_catalog = ["20kW", "30kW", "40kW", "60kW", "80kW"]
            power_module_type = st.selectbox("Select the power module type", options=pm_catalog, index=3)
            power_module_number = st.number_input("Give the power module number (max 100)", min_value=1, max_value=100, value=10)
            # power_module_config = {"Type":power_module_type, "Number":power_module_number}
            power_module_type = GC.power_module_catalog[power_module_type] # UUxxkW dict
            station_type["max_charger_number"] = power_module_number
            station_type["power_module_type"] = power_module_type
            station_type["max_power"] = int(station_type["power_module_type"]["max_power"] * power_module_number)
        else:
            st.write("Selected the BSS type doesn't support for power modules configuration.")    
    st.write("")

with col_r1: # bsc num
    # set up the number of BSC
    st.write("")
    st.markdown("### Number of BSC")
    if type_bss == "BSS Type-2 V1 - 600kW":
        bsc_num = st.number_input("Select the number of BSC equipped with BSS", min_value=0, \
            max_value=station_type["max_charge_terminal"], value=station_type["max_charge_terminal"], step=1)      
        st.write("The number of BSC is: ", bsc_num)
    elif type_bss == "BSS Type-2 V2 - 1200kW":
        bsc_num = st.number_input("Select the number of BSC equipped with BSS", min_value=0, \
            max_value=station_type["max_charge_terminal"], value=station_type["max_charge_terminal"], step=1)
        st.write("The number of BSC is: ", bsc_num)
    elif type_bss == "User Defined":
        bsc_num = st.number_input("Select the number of BSC equipped with BSS", min_value=0, \
            max_value=100, value=0, step=1)
        station_type["max_charge_terminal"] = bsc_num
    else:
        bsc_num = 0
        st.write("The selected BSS facility can not quipped with BSC, thus the number is 0.")
        st.empty()
    st.write("")

with col_l2: # user preference
    # set up the user preference
    st.write("")
    st.markdown("### User Preference")
    selection_candidates = ["markov","full_swap", "fixed_value"]
    help_descrip = "user preference mode indicates how the clients will select their service, \
        the behaviours of clients includes swap, charge, leave. In fixed_value mode, the ratio is: \
        swap : charge : leave = 70% : 30% : 0%. The preference modes can only be applied to swapping user group."
    if (type_bss == "BSS Type-1 - 500kW") or (bsc_num == 0):
        user_preference = st.radio("Select the user preference mode",options=["full_swap"], help=help_descrip)
    else:
        user_preference = st.radio("Select the user preference mode",options=selection_candidates, help=help_descrip)
    st.write("")

with col_r2: # service ratio for "fixed value" preference option
    st.write("")
    st.markdown("### Service Ratio")
    if user_preference == "fixed_value":
        user_selection_ratio = st.slider("Select the service Swap : Charge ratio", min_value=0, max_value=100, value=70)
        st.write("The Swap : Charge ratio is %d %% : %d %%" %(user_selection_ratio, 100 - user_selection_ratio))
    else:
        user_selection_ratio = -1
        st.write("Service ratio is determined by the algorithms automatically.")
    st.write("")

with col_l3: # battery config
    # Battery type:
    st.write("")
    st.markdown("### Battery Type & Number")
    battery_help = "Select the number of battery 100kWh, the rest places will be filled with 75kWh"
    
    if type_bss == "BSS Type-1 - 500kW":
        num_battery_type1 = st.slider("Select the number of 100 kWh Batteries", min_value=0,\
             max_value=station_type["max_battery_number"], value=station_type["max_battery_number"], help=battery_help)
        num_battery_type2 = station_type["max_battery_number"] - num_battery_type1
        st.write("Battery configuration for 100kWh: ", num_battery_type1, " 75kWh: ", num_battery_type2)
        battery_config = {"100kWh": num_battery_type1, "75kWh": num_battery_type2}
    
    elif type_bss == "BSS Type-2 V1 - 600kW" or type_bss == "BSS Type-2 V2 - 1200kW":
        num_battery_type1 = st.slider("Select the number of 100 kWh Batteries", min_value=0,\
             max_value=station_type["max_battery_number"], value=station_type["max_battery_number"], help=battery_help)
        num_battery_type2 = station_type["max_battery_number"] - num_battery_type1
        st.write("Battery configuration for 100kWh: ", num_battery_type1, " 75kWh: ", num_battery_type2)
        battery_config = {"100kWh": num_battery_type1, "75kWh": num_battery_type2}
    
    elif type_bss == "User Defined":
        tab6, tab7 = st.tabs(["Large battery Pack", "Small battery Pack"])
        num_small_1 = 0
        num_small_2 = 0
        num_large_type1 = 0
        num_large_type2 = 0
        num_large_type3 = 0
        with tab6: # Large
            if num_small_1 + num_small_2 == 0:
                num_large_type1 = st.number_input("Give the number of 100 kWh battery", min_value=0, max_value=int(power_module_number - num_large_type2 - num_large_type3), value=int(power_module_number))
                num_large_type2 = st.number_input("Give the number of 75 kWh battery", min_value=0, max_value=int(power_module_number - num_large_type1 - num_large_type3), value=0)
                num_large_type3 = st.number_input("Give the number of 70 kWh battery", min_value=0, max_value=int(power_module_number - num_large_type1 - num_large_type2), value=0)
                battery_config = {"100kWh": num_large_type1, "75kWh": num_large_type2, "70kWh": num_large_type3}
                station_type["max_battery_number"] = sum(battery_config.values())
            else:
                st.write("The number of battery is not 0")
        
        with tab7: # Small
            if (num_large_type1 + num_large_type2 + num_large_type3) == 0:
                num_small_1 = st.number_input("Give the number of FY 60 kWh battery", min_value=0, max_value=int(power_module_number - num_small_2), value=int(power_module_number))
                num_small_2 = st.number_input("Give the number of FY 40 kWh battery", min_value=0, max_value=int(power_module_number - num_small_1), value=0)
                battery_config = {"60kWh":num_small_1, "40kWh":num_small_2}
                station_type["max_battery_number"] = sum(battery_config.values())
            else:
                st.write("The number of Large battery Pack is not 0")
        
    else:
        battery_help2 = "Select the number of battery 60kWh, the rest places will be filled with 40kWh"
        num_battery_type1 = st.slider("Select the number of 60 kWh Batteries", min_value=0,\
             max_value=station_type["max_battery_number"], value=station_type["max_battery_number"],\
                help=battery_help2)
        num_battery_type2 = station_type["max_battery_number"] - num_battery_type1
        st.write("Battery of 60 kWh: ", num_battery_type1, " FY 40 kWh: ", num_battery_type2)
        battery_config = {"60kWh": num_battery_type1, "40kWh": num_battery_type2}
    st.write("")

with col_l4: # battery init soc
    # Battery initial soc:
    st.write("")
    st.markdown("### Battery Initial SOC")
    init_battery_soc = st.slider("Select the battery initial SOC in BSS", min_value=0.0, max_value=1.0, value=0.95, step=0.05)
    st.write("Initial battery soc: ", init_battery_soc)
    st.write("")

with col_r3: # battery target soc
    st.write("")
    # Battery target soc:
    st.markdown("### BSC Target SOC")
    help_target_soc = "User charge the vehicle battery with BSC, when the SOC reaches this target, they will leave."
    target_soc = st.slider("Select the charging target SOC for charge piles", min_value=0.5, max_value=1.0, value=0.9, step=0.05, help=help_target_soc)
    st.write("Target battery soc: ", target_soc)
    st.write("")

with col_r4: # battery selection soc
    # Battery select soc:
    st.write("")
    st.markdown("### BSS Selection SOC")
    help5 = "The swapping service can be performed only when there are batteries reach this SOC"
    select_soc = st.slider("Select the battery output SOC from BSS", min_value=0.5, max_value=1.0, value=0.95, step=0.05, help=help5)
    st.write("Selection battery soc: ", select_soc)
    st.write("")

with col_l5: # queue mode
    # User queue generation modes selection:
    st.write("")
    st.markdown("### Queue Generation")
    user_queue_mode = st.selectbox("Select the generation mode of user queue", ("random", "statistical"), index=0)
    # st.write("The user queue generation mode is: ", user_queue_mode)
    st.write("")

with col_r5: # swapping user num
    st.write("")
    # User Queue Generation mode = "random" -> Select daily user number
    if user_queue_mode == "random":
        # Daily user:
        st.markdown("### Number of BS Clients")
        help_BS = "Select the number of Battery swappable Clients"
        swapping_user_num = st.number_input("Give the number of daily clients that will use this BSS", min_value=1, max_value=300, value=50, step=5, help = help_BS)
        # st.write("The number of daily Swapping clients are: ", swapping_user_num)
        user_area = None
    
    # User Queue Generation mode = "statistical" -> Select BSS deployment area
    else:
        # User sequence generation area:
        st.markdown("### Simulation Area")
        user_area = st.selectbox("Select the area of BSS simulation", ("urban", "suburb/highway"), index=0)
        # st.write("The simulation area is ", user_area)
        swapping_user_num = 0
    st.write("")

with col_l6: # power distribution strategy
    st.write("")
    st.markdown("### Power Distribution")
    help_power_dist = "When select 'BSS prefered', the power modules will preferentially supply the battery in the station,\
         and then the redundancy will be allocated to the BSC; otherwise the BSCs have the highest priority to use the power module."
    if type_bss == "BSS Type-1 - 500kW" or bsc_num == 0:
        st.write("This type of BSS is not equipped with BSC, only swap service avaiable.")
        power_dist_option = "BSS preferred"
    else:
        power_dist_option = st.selectbox("Select the Power distribution Strategy", ["BSS preferred", "BSC preferred"], help=help_power_dist)
    st.write("")

with col_r6: # non swapping user num
    # set up the Non Swapping user number
    st.write("")
    st.markdown("### Number of NBS Clients")
    help_NBS = "Select the number of Non-Battery swappable Clients"
    if bsc_num == 0:
        st.write("This type of BSS is not equipped with BSC, the Non Swapping users can not use this BSS facility.")
        non_swapping_user_num = 0
    else:
        help_desp = "Non-Swapping user belongs to third party, they can only use the BSC charge service of BSS."
        non_swapping_user_num = st.number_input("Give the number of Non-Swapping user", min_value=0, max_value=50, value=0, step=1, help=help_desp)
        # st.write("The number of daily Non-Swapping clients are: ", non_swapping_user_num)
    st.write("")


with col_l7: # trigger of Grid interactive
    st.markdown("### Grid Interaction")
    
    tab20, tab8, tab9 = st.tabs(["Trigger", "Time Interval", "Number of Interactions"])
    st.write("")
    with tab20:
        grid_interaction_help = "Grid Interaction is the behaviour that allows the BSS take part in the Grid \
            Frequency Balancing by discharging a small part of Energy stored in the batteries. This behaviour will be \
            initiated while a swap service is executed. By default this functionality is deactivated."
        grid_interaction_trigger = st.radio("Request for activating the grid interaction", [True, False], index=1, help=grid_interaction_help)
        
    with tab8:
        if grid_interaction_trigger == False:
                st.write("Grid interaction deactivated.")
                grid_interaction_interval_idx = -1
        else:
            timeIntervalHelp = "The Grid interaction will be executed while swap service btw the selected time interval."
            timeOption = ["0:00 - 1:00", "1:00 - 2:00", "2:00 - 3:00", "3:00 - 4:00", 
                            "4:00 - 5:00", "5:00 - 6:00", "6:00 - 7:00", "7:00 - 8:00",
                            "8:00 - 9:00", "9:00 - 10:00", "10:00 - 11:00", "11:00 - 12:00",
                            "12:00 - 13:00", "13:00 - 14:00", "14:00 - 15:00", "15:00 - 16:00",
                            "16:00 - 17:00", "17:00 - 18:00", "18:00 - 19:00", "19:00 - 20:00",
                            "20:00 - 21:00", "21:00 - 22:00", "22:00 - 23:00", "23:00 - 00:00"]
            grid_interaction_interval = st.selectbox("Select the executing time interval of Grid interaction", options=timeOption, help=timeIntervalHelp)
            grid_interaction_interval_idx = timeOption.index(grid_interaction_interval)
    
    with tab9:
        if grid_interaction_trigger == False:
                st.write("Grid interaction deactivated.")
                interaction_num = 0
        else:
            numIntervalHelp = "The number of interactions will be performed while user occupying the swap station, \
                if the number of user within selected time not sufficient, interaction behaviour will be skipped."
            interaction_num = st.slider("Select the number of interactions that will be performed within the interval", 1, 6, help=numIntervalHelp)
    st.write("")

with col_r7: # Opening hours
    #########################################################
    #########################################################
    # Requriements:
    # 1. time interval from 0:00 to 24:00 (0:00 +1 day)
    # 2. open time should not bigger than close time
    # 3. only enable this open hour configuration under 'Queue Generation' Mode 'random'
    # '''
    #########################################################
    #########################################################

    st.markdown("### Opening Hours" )

    # if user_queue_mode == "random":
    if user_queue_mode == "random":
        help_opening = "Simulate the service time, with random Queue Generation you can choose to simulate the whole day 24 hours or only during the daytime business hours 9:00 to 19:30."
        selection_time =st.radio("Select your simulation time interval",('24 hours','9:00 to 19:30'),help=help_opening)
    else: st.write("For Statistical user Queue we only support 24 hours simulation since all our statistics data was collected during 00:00 - 24:00. "
                   "Random selection of intervals will result in inaccurate simulation data generated. If you want to check the opening time please switch to random user queue.")

    st.write("")
    # else:
    #     st.write("Opening hour depends on the statistics datalog.")
    #     open_time = None
    #     close_time = None
    #########################################################
    # End of your code
    #########################################################

with col_lnew: ### Power modul self setting
    st.markdown("### Power module allocation")
    ### decide if this function supports current satstion by Hao 11.18.2022
    if type_bss == "BSS Type-1 - 500kW":
        select_module = 1.0
        st.write("This function not supports BSS Type-1 or User defined Station.")
    else:
        if user_queue_mode == "random":
            help_module = "In order to optimize the waiting time of charging users, we can flexibly allocate a certain proportion of charging modules to BSC users."
            select_module = st.slider("Select the allocation ratio", min_value=0.5, max_value=1.0, value=1.0,
                               step=0.05, help=help_module)
            st.write("The unallocated : allocated Module ratio is %d %% : %d %%" % (100*select_module, 100 - 100*select_module))
            st.write("")
        else:
            st.write("This function only supports user random queue mode")
with col_m1:
    ######################################################################
    ########### Excute the simulation if the button is pressed ###########
    ######################################################################
    st.write("===========================")
    button_flag_1 = st.button("Start Single Station Simulation")
    st.write("===========================")

if button_flag_1 == True:
    with st.spinner("simulation excuting..."):
        # Perform Simulation
        ####################################################################################################
        # collect the setup congiuration into dict "param", prepare to transport into do_simulation(param) #
        ####################################################################################################
        sim_interval = 10

        # openning hour 24 h
        # if selection_time == "24/7":

        sim_days = 1
        sim_ticks = int(sim_days * 24 * 60 * 60 / sim_interval)

        # update random user queue param generation 11.11.2022 by Hao Liu
        if user_queue_mode == "random":
            param = {
                "station_type" : station_type,                                      # set up the BSS type GEN3_600kW, GEN3_1200kW
                "psc_num" : bsc_num,                                                # set up the BSC number according to the type of BSS
                "battery_config" : battery_config,                                  # set up the battery configuration in a swap rack module
                "init_battery_soc_in_BSS" : init_battery_soc,                       # set up the initial battery soc in BSS
                "target_soc" : target_soc,                                          # set up the charge target soc
                "select_soc" : select_soc,                                          # set up the which soc of battery in BSS will be selected to swap
                "BS_user_num" : swapping_user_num,                                      # set up how many users in a day will use the BSS
                "non_BS_user_num" : non_swapping_user_num,                              # set up the number of non BS user
                "sim_days" : sim_days,                                              # set up the simulation day loop
                "sim_interval" : sim_interval,                                      # set up the simulation interval, unit: sec
                "sim_ticks" : sim_ticks,                                            # calculate how many simulation bins in a day loop
                "swap_rack_temperature" : 25,                                       # set up the rack temperature
                "user_sequence_mode" : user_queue_mode,                             # "random" for random sequence create based on distribution defined by user_sequence_random_file
                                                                                    # "statistical" generate user sequence based on real statistical data
                "user_area" : user_area,                                            # set up the simulation area for statistical mode
                "user_preference" : user_preference,                                # define the user selection preference in markov, full swap, or fixed value (70% swap, and 30% charge)
                "charge_power_redist" : False,                                      # True: modules will be redistributed after every sim interval, if there exists charging pile, they will be disconnected
                                                                                    # False: modules once be connected to outer charging piles, they are not allowed be disconnected until vehicle leaves
                "enable_me_switch" : 1,                                             # define whether the transport btw the battery rack is allowed, 1 means allowable, 0 not allowable
                "power_dist_option" : power_dist_option,                            # define which facility has higher power dist priority BSS or BSC
                "service_ratio": user_selection_ratio,                              # when select fixed ratio of service, configure the specific value
                "grid_interaction_idx" : grid_interaction_interval_idx,             # the time interval of execution of grid interaction, -1 -> service deactivated
                "interaction_num" : interaction_num,                                # define the times that interaction will perform
                "swap_time" : swap_time,                                             # configure the swap time
                "opening_hours":selection_time
            }

        else:
            param = {
                "station_type" : station_type,                                      # set up the BSS type GEN3_600kW, GEN3_1200kW
                "psc_num" : bsc_num,                                                # set up the BSC number according to the type of BSS
                "battery_config" : battery_config,                                  # set up the battery configuration in a swap rack module
                "init_battery_soc_in_BSS" : init_battery_soc,                       # set up the initial battery soc in BSS
                "target_soc" : target_soc,                                          # set up the charge target soc
                "select_soc" : select_soc,                                          # set up the which soc of battery in BSS will be selected to swap
                "BS_user_num" : swapping_user_num,                                      # set up how many users in a day will use the BSS
                "non_BS_user_num" : non_swapping_user_num,                              # set up the number of non BS user
                "sim_days" : sim_days,                                              # set up the simulation day loop
                "sim_interval" : sim_interval,                                      # set up the simulation interval, unit: sec
                "sim_ticks" : sim_ticks,                                            # calculate how many simulation bins in a day loop
                "swap_rack_temperature" : 25,                                       # set up the rack temperature
                "user_sequence_mode" : user_queue_mode,                             # "random" for random sequence create based on distribution defined by user_sequence_random_file
                                                                                    # "statistical" generate user sequence based on real statistical data
                "user_area" : user_area,                                            # set up the simulation area for statistical mode
                "user_preference" : user_preference,                                # define the user selection preference in markov, full swap, or fixed value (70% swap, and 30% charge)
                "charge_power_redist" : False,                                      # True: modules will be redistributed after every sim interval, if there exists charging pile, they will be disconnected
                                                                                    # False: modules once be connected to outer charging piles, they are not allowed be disconnected until vehicle leaves
                "enable_me_switch" : 1,                                             # define whether the transport btw the battery rack is allowed, 1 means allowable, 0 not allowable
                "power_dist_option" : power_dist_option,                            # define which facility has higher power dist priority BSS or BSC
                "service_ratio": user_selection_ratio,                              # when select fixed ratio of service, configure the specific value
                "grid_interaction_idx" : grid_interaction_interval_idx,             # the time interval of execution of grid interaction, -1 -> service deactivated
                "interaction_num" : interaction_num,                                # define the times that interaction will perform
                "swap_time" : swap_time,                                             # configure the swap time
                "opening_hours":"24h"
            }

        # container preparation
        user_dist_lst = []
        power_history = []
        residual_power = []
        swap_list = []
        swap_charge_list = []
        non_swap_charge_list = []
        power_mean_list = []
        max_power = 0
        BS_average_time_charge = 0       #BS - Battery swapping ability
        NBS_average_time_chagre = 0  #NBS - Non Battery swapping ability
        average_time_swap = 0
        swap_ratio_in_15_min = 0
        queue_length_swap = []
        queue_length_charge = []
        queue_overflow_number = []
        queue_overflow_ratio = 0

        # perform simulation 
        swap_user_wait_time, charge_user_wait_time, queue_length_swap, queue_length_charge, user_dist_lst, max_power, power_history, residual_power, swap_list, \
        swap_charge_list, non_swap_charge_list, average_time_swap, BS_average_time_charge, non_BS_average_time_chagre, swap_ratio_in_15_min = main.do_simulation(param = param)

        ### New fixed" add power module allocation factor"


        # 1. calculate time step
        day_step = sim_days + 1
        date1 = datetime.date(2022,1,1)
        date2 = datetime.date(2022,1,day_step)
        delta = datetime.timedelta(seconds = sim_interval)
        dates = mdates.drange(date1, date2, delta)
        
        # 2. success ratio within 15 min
        ratio_persentage = swap_ratio_in_15_min * 100

        # 3. energy consumption
        y_func = []
        y_grid_func = []
        for pw in power_history:
            # collect the power distribution pro sim interval
            if pw[1] >= 0:
                y_func.append(pw[1])
                y_grid_func.append(0)
            else:
                y_func.append(0)
                y_grid_func.append(pw[1])
            
        
        power_mean = np.mean(y_func)
        for i in range(len(dates)):
            # collect the mean value of the power distribution
            power_mean_list.append(power_mean)      
        total_energy = energy_calc(y_func, sim_interval)
        grid_interaction_energy = abs(energy_calc(y_grid_func, sim_interval))

        # 4. total average charge time and charge rate calculation
        if BS_average_time_charge!=0 and non_BS_average_time_chagre!=0:
            total_average_charge_time = (BS_average_time_charge * len(swap_charge_list) + non_BS_average_time_chagre * len(non_swap_charge_list)) / (len(swap_charge_list) + len(non_swap_charge_list))
            total_charge_rate = 60 / total_average_charge_time
            BS_charge_rate = 60 / BS_average_time_charge
            non_BS_charge_rate = 60 / non_BS_average_time_chagre
        else:
            total_average_charge_time = 0
            total_charge_rate = 0
            BS_charge_rate = 0
            non_BS_charge_rate = 0
            
        if average_time_swap != 0:
            swap_rate = 60 / average_time_swap
        else:
            swap_rate = 0
        
        # 5. overflow of service user
        queue_overflow_number.append(queue_length_swap[-1])
        queue_overflow_number.append(queue_length_charge[-1])
        if len(user_dist_lst) != 0:
            queue_overflow_ratio = round((sum(queue_overflow_number) / len(user_dist_lst)) * 100, 2)
        else:
            queue_overflow_ratio = 0
        # ====================== summary the result in a table =============================
        ### show Power module allocation result
        if user_queue_mode == "random":
            result_data = {
                "Total Number of Serviced Swap Clients": len(swap_list) * select_module,
                "Total Number of Serviced Charge Clients": (len(swap_charge_list) + len(non_swap_charge_list))* (2-select_module),
                "Number of Serviced BS Charge Clients": len(swap_charge_list) * (2-select_module),
                "Number of Serviced NBS Charge Clients": len(non_swap_charge_list) * (2-select_module),
                "Overflow Number of Swap Queue": queue_overflow_number[0] * (2-select_module),
                "Overflow Number of Charge Queue": queue_overflow_number[1] * select_module,
                "Total Overflow Ratio [%]": queue_overflow_ratio,
                "Total Energy [kWh]": total_energy,
                "Grid Interaction Energy [kWh]": grid_interaction_energy,
                "Swap Ratio in 15 Minutes [%]": ratio_persentage * select_module,
                "Average Swap Time [minutes]": average_time_swap * (2-select_module),
                "Average Swap Rate [1/hours]": swap_rate * select_module,
                "Average Charge Time for All Clients Group [minutes]": total_average_charge_time * select_module,
                "Average Total Charge Rate [1/hours]": total_charge_rate * (2-select_module),
                "Average Charge Time for BS Group [minutes]": BS_average_time_charge * select_module,
                "Average Charge Rate for BS Group [1/hours]": BS_charge_rate * (2-select_module),
                "Average Charge Time for NBS Group [minutes]": non_BS_average_time_chagre * select_module,
                "Average Charge Time for NBS Group [1/hours]": non_BS_charge_rate * (2-select_module)
            }
        else:
            result_data = {
                "Total Number of Serviced Swap Clients" : len(swap_list),
                "Total Number of Serviced Charge Clients" : len(swap_charge_list) + len(non_swap_charge_list),
                "Number of Serviced Swapping Charge Clients" : len(swap_charge_list),
                "Number of Serviced Non Swapping Charge Clients" : len(non_swap_charge_list),
                "Overflow Number of Swap Queue" : queue_overflow_number[0],
                "Overflow Number of Charge Queue" : queue_overflow_number[1],
                "Total Overflow Ratio [%]" : queue_overflow_ratio,
                "Total Energy [kWh]" : total_energy,
                "Grid Interaction Energy [kWh]" : grid_interaction_energy,
                "Swap Ratio in 15 Minutes [%]" : ratio_persentage,
                "Average Swap Time [minutes]" : average_time_swap,
                "Average Swap Rate [1/hours]" : swap_rate,
                "Average Charge Time for All Clients Group [minutes]" : total_average_charge_time,
                "Average Total Charge Rate [1/hours]" : total_charge_rate,
                "Average Charge Time for BS Group [minutes]" : BS_average_time_charge,
                "Average Charge Rate for BS Group [1/hours]" : BS_charge_rate,
                "Average Charge Time for NBS Group [minutes]" : non_BS_average_time_chagre,
                "Average Charge Time for NBS Group [1/hours]" : non_BS_charge_rate
            }

        result_data = pd.DataFrame.from_dict(result_data, orient='index', columns=['Values'])
        result_data = result_data.reset_index().rename(columns={'index': 'Key Characteristics'})
    success_info_single_station.success("simulation successfully excuted.")
st.write("")
st.write("")

#####################################################################################
######################### Part 3: Multiple Station Configurations ###################
#####################################################################################

###Coming soon

#####################################################################################
######################### Part 4: Display Simulation results ########################
#####################################################################################

#########################
# for single station case:
#########################

with single_station_result:
    # Set up the text and statistics results for single station
    if button_flag_1 == False:
        # by default the subplot results don't show in the panel
        pass
    else:
        st.markdown("# Step 3: Results Display")
        st.write("")
        st.write("")
        ################################################################
        ############ 0. show the key text results ######################
        ################################################################
        _, col_m3, _ = st.columns([1,10,1])
        col_m3.table(result_data.style.format(precision=2, na_rep='MISSING', thousands=" ",formatter={("Values"):"{:.2f}"}))
        st.write("")
        st.write("")

        # devide the plots into 2 columns
        col1, col2 = st.columns(2)
        col3, col4 = st.columns(2)
        col5, col6 = st.columns(2)
        col7, col8 = st.columns(2) 
        # Set the plot diagram into black background and white font
        plt.style.use('dark_background')

        with col1: # arrvie time dist
            ################################################################
            ############## 1. show the user distribution ###################
            ################################################################
            fig1, ax1 = plt.subplots(figsize=(7, 5))
            ###fixed by Hao

            time_dist = [dt.fromtimestamp(s) for s in user_dist_lst]
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax1.tick_params(axis="both",direction = "out", labelsize= 10)
            ax1.hist(x = time_dist, bins = 48, color = "#005293", edgecolor = "black")
            #原 1969 12 31 23 和 1971 1 2 1
            plt.xlim([dt(1969, 12, 31, 23),dt(1970, 1, 2, 0)]) # 日期上下限
            plt.xlabel("Time ticks")
            plt.ylabel("User number in half hour, user total number = " + '%d' %len(user_dist_lst))
            plt.title("User vehicles reach time distribution")
            plt.grid(True, linestyle=":")
            # fig1.autofmt_xdate()
            st.pyplot(fig1)

        with col3: # charge service time dist
            ################################################################
            ############## 3. show the charge time in sim ticks ############
            ################################################################
            fig3, ax3 = plt.subplots(figsize=(7, 5))
            BS_charge_dist = []
            non_BS_charge_dist = []
            for i in range(sim_ticks):
                for user in swap_charge_list:
                    if user.sequence == i:
                        # mode = 1 wait time + charge time; mode = 0 only charge time
                        BS_charge_dist.append(user.charge_service_time() * sim_interval / 60.0)
                        break
                for user in non_swap_charge_list:
                    if user.sequence == i:
                        non_BS_charge_dist.append(user.charge_service_time() * sim_interval / 60.0)
            
            ax3.hist([BS_charge_dist, non_BS_charge_dist], bins=15, color = ["#005293", "#98C6EA"],\
                edgecolor = "black", label=['BS user', 'NBS user'])
            plt.xlabel("Charge service time in [min]")
            plt.ylabel("Counts")
            plt.title("Charge service time (Charge + Wait) distribution in 24 hours")
            plt.grid(True, linestyle=":")
            plt.legend(loc='upper right')
            st.pyplot(fig3)

        with col5: # charge time (No wait time)
            ################################################################
            ############## 5. show the charge time in sim ticks ############
            ################################################################
            fig5, ax5 = plt.subplots(figsize=(7, 5))
            BS_charge_dist = []
            non_BS_charge_dist = []
            for i in range(sim_ticks):
                for user in swap_charge_list:
                    if user.sequence == i:
                        # mode = 1 wait time + charge time; mode = 0 only charge time
                        BS_charge_dist.append(user.charge_service_time(mode=0) * sim_interval / 60.0)
                        break
                for user in non_swap_charge_list:
                    if user.sequence == i:
                        non_BS_charge_dist.append(user.charge_service_time(mode=0) * sim_interval / 60.0)
            
            ax5.hist([BS_charge_dist, non_BS_charge_dist], bins=15, color = ["#005293", "#98C6EA"],\
                edgecolor = "black", label=['BS user', 'NBS user'])
            plt.xlabel("Charge time distribution in [min]")
            plt.ylabel("Counts")
            plt.title("Charge time (without Wait) distribution in 24 hours")
            plt.grid(True, linestyle=":")
            plt.legend(loc='upper right')
            st.pyplot(fig5)

        with col7: # user num ratio
            # ################################################################
            # ############## 5. show the clients ratio #######################
            # ################################################################
            fig7, ax7 = plt.subplots(figsize=(7, 5), subplot_kw=dict(aspect="equal"))
            label = ["swap", "charge(BS)", "charge(NBS)"]
            data = [len(swap_list), len(swap_charge_list), len(non_swap_charge_list)]
            colors = ["#005293", "#64A0C8", "#98C6EA"]
            wedges, texts, persent = ax7.pie(data, wedgeprops=dict(width=0.7), startangle=45, colors=colors, autopct="%.2f%%")
            bbox_props = dict(boxstyle="square,pad=0.3", fc="k", ec="k", lw=0.72) # fc=facecolor, ec=edgecolor
            kw = dict(arrowprops=dict(arrowstyle="-"), bbox=bbox_props, zorder=0, va="center")

            for i, p in enumerate(wedges):
                ang = (p.theta2 - p.theta1)/2. + p.theta1
                y = np.sin(np.deg2rad(ang))
                x = np.cos(np.deg2rad(ang))
                horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
                connectionstyle = "angle,angleA=0,angleB={}".format(ang)
                kw["arrowprops"].update({"connectionstyle": connectionstyle})
                ax7.annotate(label[i], xy=(x, y), xytext=(1.35*np.sign(x), 1.4*y),
                            horizontalalignment=horizontalalignment, **kw)
            ax7.set_title("Clients Ratio")
            st.pyplot(fig7)

        with col2: # power dist
            ################################################################
            ############## 2. show the max power distribution ##############
            ################################################################
            fig2, ax2 = plt.subplots(figsize=(7, 5))
            y_plot1 = y_func
            y_plot2 = y_grid_func
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax2.tick_params(axis="both",direction = "out", labelsize= 10)
            ax2.plot_date(dates, y_plot1, "#64A0C8", label="Power Distribution")
            ax2.plot_date(dates, y_plot2, "red",":", alpha=0.5, label="Grid Interaction")
            ax2.plot_date(dates, power_mean_list, '--', color="#98C6EA")
            ax2.text(x=dates[0], y=power_mean+10, s="Mean %.2f [kW]"%round(power_mean,2))
            plt.xlim([dt(2021, 12, 31, 23),dt(2022, 1, 2, 1)]) 
            plt.xlabel("Time series")
            plt.ylabel("BSS total power, max power = " + '%.0f kW' %max_power)
            plt.title("BSS Power distribution")
            plt.grid(True, linestyle=":")
            plt.legend()
            st.pyplot(fig2)

        with col4: # swap time dist
            ################################################################
            ############## 4. show the swap time in sim ticks ##############
            ################################################################
            fig4, ax4 = plt.subplots(figsize=(7, 5))
            y_plot = []
            recorded = 0
            for i in range(sim_ticks):
                for user in swap_list:
                    if user.sequence == i:
                        y_plot.append(user.swap_service_time * sim_interval / 60.0)
                        break
            ax4.hist(y_plot, bins=30, color = "#005293", edgecolor = "black")
            plt.xlabel("Swap service time in [min]")
            plt.ylabel("Counts")
            plt.title("Swap service time (Swap + Wait) distribution in 24 hours")
            plt.grid(True, linestyle=":")
            st.pyplot(fig4)

        with col6: # wait time distribution

            ################################################################
            ############## 6. show the wait time distribution ##############
            ################################################################
            fig6, ax6 = plt.subplots(figsize=(7, 5))
            ax6.hist([swap_user_wait_time, charge_user_wait_time], bins=15, color = ["#005293", "#64A0C8"],\
                edgecolor = "black", label=["Swap Group Wait Time", "Charge Group Wait Time"])
            plt.xlabel("Wait time distribution [min]")
            # set the interval btw 2 ticks of y axis
            x_major_locator = MultipleLocator(10)
            y_major_locator = MultipleLocator(5)
            ax6.yaxis.set_major_locator(y_major_locator)
            ax6.xaxis.set_major_locator(x_major_locator)
            plt.ylabel("Counts")
            plt.title("Wait time distribution")
            plt.grid(True, linestyle=":")
            plt.legend()
            st.pyplot(fig6)
    
        with col8: # queue length
            ################################################################
            ############## 8. show the Queue length distribution ###########
            ################################################################
            fig8, ax8 = plt.subplots(figsize=(7, 5))
            ax8.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax8.tick_params(axis="both",direction = "out", labelsize= 10)
            ax8.plot_date(dates, queue_length_swap, "#005293", label="Swap Queue")
            ax8.plot_date(dates, queue_length_charge, "#64A0C8", label="Charge Queue")
            plt.xlim([dt(2021, 12, 31, 23),dt(2022, 1, 2, 1)]) # 日期上下限
            # set the interval btw 2 ticks of y axis
            y_major_locator = MultipleLocator(2)
            ax8.yaxis.set_major_locator(y_major_locator)
            plt.xlabel("Time series")
            plt.ylabel("Queue length")
            plt.title("Queue length distribution")
            plt.grid(True, linestyle=":")
            plt.legend()
            st.pyplot(fig8)


            

    ################################################################
    #################### Download Config ###########################
    ################################################################

    if button_flag_1 == False:
        st.empty()
    else:
        st.markdown("# Step 4: Results Download")
        st.write("Press the button to download the datalog")
        st.markdown("# ")
        param = {
        "station_type" : type_bss,                                          # set up the BSS type GEN3_600kW, GEN3_1200kW
        "psc_num" : bsc_num,
        "battery_type1" : list(battery_config.keys())[0],                   # set up the battery configuration in a swap rack module
        "num_battery_type1" : list(battery_config.values())[0],
        "battery_type2" : list(battery_config.keys())[1],  
        "num_battery_type2" : list(battery_config.values())[1],
        "init_battery_soc_in_BSS" : init_battery_soc,                       # set up the initial battery soc in BSS
        "target_soc" : target_soc,                                          # set up the charge target soc
        "select_soc" : select_soc,                                          # set up the which soc of battery in BSS will be selected to swap
        "BS_user_num" : swapping_user_num,                                      # set up how many users in a day will use the BSS
        "non_BS_user_num" : non_swapping_user_num,                              # set up the number of non BS user
        "sim_days" : sim_days,                                              # set up the simulation day loop
        "sim_interval" : sim_interval,                                      # set up the simulation interval, unit: sec
        "sim_ticks" : sim_ticks,                                            # calculate how many simulation bins in a day loop
        "swap_rack_temperature" : 25,                                       # set up the rack temperature
        "user_sequence_mode" : user_queue_mode,                             # "random" for random sequence create based on distribution defined by user_sequence_random_file
                                                                            # "statistical" generate user sequence based on real statistical data
        "user_area" : user_area,                                            # set up the simulation area for statistical mode
        "user_preference" : user_preference,                                # define the user selection preference in markov, full swap, or fixed value (70% swap, and 30% charge)
        "charge_power_redist" : False,                                      # True: modules will be redistributed after every sim interval, if there exists charging pile, they will be disconnected
                                                                            # False: modules once be connected to outer charging piles, they are not allowed be disconnected until vehicle leaves
        "enable_me_switch" : 1                                              # define whether the transport btw the battery rack is allowed, 1 means allowable, 0 not allowable
    }
        param_df = pd.DataFrame.from_dict(param, orient='index', columns=['Values'])
        param_df = param_df.reset_index().rename(columns={'index': 'Parameters'})
        frames = [param_df, result_data]
        result = pd.concat(frames,axis=1)
        csv = convert_df(result)

        _, col_m4, _ = st.columns([5,3,5])
        with col_m4:

            st.write("================")
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name='datalog.csv',
                mime='text/csv',
            )
            st.write("================")

###########################
# for multiple station case:  TODO:
###########################




################################################################
#################### Sidebar Notation ##########################
################################################################
# ========= Set up the BSS selection Recommendation (sidebar) =======
st.sidebar.markdown("# BSS Power Assistant")
st.sidebar.write("")
st.sidebar.markdown("## Set up your BSS proporties:")
BSS_type = ["BSS Type-1 - 500kW", "BSS Type-2 V1 - 600kW", "BSS Type-2 V2 - 1200kW"]
power_level = [100, 200, 300, 550, 630, 1250]
BSS_select = None
power_select = 0

# Peak swap number
help1 = "BSC not included"
st.sidebar.write("")
st.sidebar.markdown("### Peak Swapping Number (Morning)")
ans1 = st.sidebar.slider("Select the expected peak swapping number (morning)/hour", min_value=0, max_value=20, help=help1)

# Peak charge number
st.sidebar.write("")
st.sidebar.markdown("### Peak Charging Number")
ans2 = st.sidebar.slider("Select the expected peak charging number/hour", min_value=0, max_value=18, help=help1)

# Peak swap day time
st.sidebar.write("")
st.sidebar.markdown("### Peak Swapping Number (Day time)")
ans3 = st.sidebar.slider("Select the expected peak swapping number (day time)/hour", min_value=0, max_value=13, help=help1)

# Swap service capacity
help2 = "The number of daily swapping clients"
st.sidebar.write("")
st.sidebar.markdown("### Daily Swapping Capacity")
ans4 = st.sidebar.number_input("Give the daily swapping number capacity", min_value=0, max_value=150, step=5, value=50, help=help2)

# BSC required
st.sidebar.write("")
st.sidebar.markdown("### Is Battery Station Charger(BSC) Required?")
ans5 = st.sidebar.checkbox("BSC required")

##########################################
############ Logic inference #############
##########################################
# first for BSS Type - 1
if ans1 <= 13 and ans2 <= 8 and ans3 <= 8 and ans4 <= 93 and ans5 == False:
    BSS_select = BSS_type[0]
    if ans2 <= 2 and ans3 <=2 and ans4 <= 33:
        power_select = power_level[0]
    elif (ans2 == 3 or ans3 == 3 or ans4 > 33) and ans4 <= 43:
        power_select = power_level[1]
    elif (ans2 > 3 or ans3 > 3 or ans4 > 43) and ans2 <= 5 and ans3 <= 5 and ans4 <= 63:
        power_select = power_level[2]
    else:
        power_select = power_level[3]
# second for BSS Type - 2
else:
    if ans2 <= 3 and ans3 <= 3 and ans4 <= 50 and ans5 == False:
        BSS_select = BSS_type[1]
        power_select = power_level[1]
    elif (ans2 > 3 or ans3 > 3 or ans4 > 50) and ans2 <=5 and ans3 <= 5 and ans4 <= 70 and ans5 == False:
        BSS_select = BSS_type[1]
        power_select = power_level[2]
    elif (ans2 > 5 or ans3 > 5 or ans4 > 70) and ans2 <=9 and ans3 <= 9 and ans4 <= 110:
        BSS_select = BSS_type[1]
        power_select = power_level[4]
    else:
        BSS_select = BSS_type[2]
        power_select = power_level[5]

##########################################
############ Data Collection #############
##########################################
# Summary of BSS configurations
BSS_data = {"station_type":         None, 
            "num_battery":          0, 
            "BSC":                  None, 
            "num_charge_piles":     0, 
            "transformer_power":    0       
            }
BSS_data["station_type"] = BSS_select
BSS_data["transformer_power"] = power_select

# BSS Type-1
if BSS_data["station_type"] == "BSS Type-1 - 500kW": 
    BSS_data["station_type"] = "BSS Type-1 or above"
    BSS_data["num_battery"] = 13
    BSS_data["bsc"] = "No BSC"
    BSS_data["num_charge_piles"] = 0
# BSS Type-2
elif BSS_data["station_type"] == "BSS Type-2 V1 - 600kW": 
    BSS_data["num_battery"] = 10
    if ans5:
        BSS_data["BSC"] = "BSC equipped"
    else:
        BSS_data["BSC"] = "No BSC"
    
    if BSS_data["transformer_power"] <= 300:
        BSS_data["num_charge_piles"] = 0
    else:
        BSS_data["num_charge_piles"] = 4
# BSS 3.0 PUS B
else:
    BSS_data["num_battery"] = 20
    BSS_data["BSC"] = "BSC equipped"
    BSS_data["num_charge_piles"] = 8

##########################################
############ Suggestion ##################
##########################################

st.sidebar.write("")
st.sidebar.write("")
st.sidebar.markdown("## Suggestion:")
st.sidebar.write("Press the button to get advice")
_, col_m, _ = st.sidebar.columns([1,2,1])
trigger_btn = col_m.button("Suggestion")

col21, col22 = st.sidebar.columns([2,1])
col23, col24 = st.sidebar.columns([2,1])
col25, col26 = st.sidebar.columns([2,1])
col27, col28 = st.sidebar.columns([2,1])
col29, col30 = st.sidebar.columns([2,1])

if trigger_btn == False:
    st.empty()
else:
    col21.info("BSS Type: ")
    col22.markdown("### %s" %BSS_data["station_type"])
    st.write("")
    col23.info("Maximal allowable number of Battery Racks: ")
    col24.markdown("### %d" %BSS_data["num_battery"])
    st.write("")
    col25.info("Maximal allowable number of Charge Terminals: ")
    col26.markdown("### %d" %BSS_data["num_charge_piles"])
    st.write("")
    col27.info("BSC state: ")
    col28.markdown("### %s" %BSS_data["BSC"])
    st.write("")
    col29.info("Recommended transformer power: ")
    col30.markdown("### %d" %BSS_data["transformer_power"] + " [kVA]")
    st.write("")

# set up the Notation and contact information
st.sidebar.write("")
st.sidebar.write("")
st.sidebar.write("")
st.sidebar.write("")
