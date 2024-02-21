import numpy as np

class Global_Constant:
    def __init__(self) -> None:
        ####Basic parameter settings of battery swap station####
        self.GEN2_530kW = {"station_type":"GEN2_530","max_battery_number": 13,"max_charge_terminal":0,"max_power":520,"max_charger_number":13}
        self.GEN3_600kW = {"station_type":"GEN3_600","max_battery_number": 20,"max_charge_terminal":4,"max_power":600,"max_charger_number":10}
        self.GEN3_1200kW = {"station_type":"GEN3_1200","max_battery_number": 20,"max_charge_terminal":8,"max_power":1200,"max_charger_number":20}
        self.User_Defined = {"station_type":"User_Defined","max_battery_number": 0,"max_charge_terminal":0,"max_power":0,"max_charger_number":0,
                             "power_module_type":None}
        ####Charging module basic parameter settings####
        self.UU20kW = {"max_power":20,"max_current":75}
        self.UU30kW = {"max_power":30,"max_current":101}
        self.UU40kW = {"max_power":40,"max_current":134}
        self.UU60kW = {"max_power":60,"max_current":200}
        self.UU80kW = {"max_power":80,"max_current":250}
        self.power_module_catalog = {
            "20kW":self.UU20kW,
            "30kW":self.UU30kW,
            "40kW":self.UU40kW,
            "60kW":self.UU60kW,
            "80kW":self.UU80kW
        }
        ####battery capacity[Ah]####
        self.battery_capacity={  
            "70kWh": 204,
            "75kWh": 195,
            "100kWh": 280,
            "40kWh": 120,
            "60kWh": 175
        }#Battery Ah number
        #### battery open circuit voltage (for every 1% SOC)####
        ### new change: Entend the interavll from 0-95 to 0-100
        self.ocv_100 = [336,338,340,341,342,343,344,345,345,346,346,346,
        347,347,347,348,348,348,349,349,349,349,350,350,350,351,351,
        351,352,352,352,353,353,354,354,354,355,355,356,356,357,357,
        358,358,359,359,360,361,361,362,363,364,365,365,366,367,368,
        369,370,371,372,373,374,375,376,377,378,379,380,382,383,384,
        385,386,387,388,389,390,392,393,393,394,395,396,397,399,400,
        400,401,401,402,403,404,405,405,405,405,406,406,406]
        self.ocv_70 = [337,338,339,341,343,344,344,345,346,346,347,347,347,
        348,348,348,349,349,349,350,350,350,350,351,351,352,352,353,353,
        354,354,354,355,355,356,356,357,357,358,358,359,360,360,362,361,
        362,363,364,365,366,367,368,369,370,371,371,373,374,375,376,377,
        378,379,379,381,382,382,383,385,386,387,388,389,390,391,392,393,
        394,395,396,397,398,399,400,401,401,402,402,403,403,403,404,404,
        404,404]
        ####battery charging current under diff Temperatures (for SOC 5%10%20%..80%85%90%95%)###
        self.charge_limit_100= {
            -20:[26,26,21,18,16,16,13,12,10,7,5,4,3],
            -10:[82,82,73,54,52,49,45,44,39,29,25,20,15],
            0:[150,203,168,135,119,101,89,82,74,57,51,42,28],
            10:[150,250,290,249,208,167,141,126,114,90,81,69,28],
            20:[150,250,350,350,316,243,199,175,157,127,114,93,28],
            25:[150,250,350,350,350,285,230,201,179,146,131,93,28],
            30:[150,250,350,350,350,328,262,227,203,166,149,93,28],
            40:[150,250,350,350,350,350,295,254,226,187,168,93,28]
            }
        self.charge_limit_75= {
            -20:[10,10,10,10,10,8,8,8,6,6,6,6,4],
            -10:[59,59,59,39,39,29,29,20,16,16,10,10,6],
            0:[137,137,137,137,98,98,78,78,59,39,29,29,16],
            10:[250,250,250,250,195,166,146,137,98,78,59,39,25],
            20:[371,371,371,293,250,250,234,176,137,117,78,64,39],
            25:[390,390,390,390,371,293,254,250,195,156,117,78,64],
            35:[429,429,429,429,429,410,371,293,195,156,117,78,64],
            45:[429,429,429,429,429,410,371,293,195,156,117,78,64]
            }
        self.charge_limit_70= {
            -20:[10,10,10,10,10,10,10,10,10,4,4,4,4],
            -10:[20,20,20,20,20,20,20,20,20,20,20,20,10],
            0:[40,40,40,40,40,40,40,40,40,40,40,40,20],
            10:[140,140,140,140,140,100,100,100,67,67,67,67,20],
            20:[180,180,180,180,180,120,120,120,120,67,67,67,67],
            25:[240,240,240,240,240,240,160,160,160,67,67,67,67],
            30:[240,240,240,240,240,240,160,160,160,67,67,67,67],
            45:[240,240,240,240,240,240,160,160,160,67,67,67,67]
            }
        ### Annual Temperature statistics (Monthly) ###
        # with first row max Temp in the month, second row min Temp in the month
        self.temp = np.array([[5, 8, 10, 15, 20, 23, 24, 27, 20, 10, 4, 3], # max Temp
                              [-10, -12, 0, 3, 5, 8, 10, 10, 5, 0, -5, -10]]) # min Temp
        ### user come in station distribution real time statistics ###
        # case 1 for urban
        self.user_dist_urban_file_list = [
            'urban_day10_118.dat',
            'urban_day11_107.dat',
            'urban_day12_113.dat',
            'urban_day13_106.dat',
            'urban_day14_110.dat',
            'urban_day15_124.dat',
            'urban_day16_120.dat',
            'urban_day17_137.dat',
            'urban_day18_118.dat',
            'urban_day19_127.dat',
            'urban_day1_122.dat',
            'urban_day20_126.dat',
            'urban_day21_106.dat',
            'urban_day22_121.dat',
            'urban_day23_122.dat',
            'urban_day24_128.dat',
            'urban_day25_124.dat',
            'urban_day26_113.dat',
            'urban_day27_128.dat',
            'urban_day28_111.dat',
            'urban_day29_111.dat',
            'urban_day2_127.dat',
            'urban_day30_112.dat',
            'urban_day3_109.dat',
            'urban_day4_103.dat',
            'urban_day5_106.dat',
            'urban_day6_117.dat',
            'urban_day7_103.dat',
            'urban_day8_115.dat',
            'urban_day9_116.dat',]
        # case 2 for suburbs, highway
        self.user_dist_highway_file_list = [
            'highway_day10_20.dat',
            'highway_day11_44.dat',
            'highway_day12_23.dat',
            'highway_day13_28.dat',
            'highway_day14_25.dat',
            'highway_day15_46.dat',
            'highway_day16_40.dat',
            'highway_day17_44.dat',
            'highway_day18_39.dat',
            'highway_day19_45.dat',
            'highway_day1_18.dat',
            'highway_day20_50.dat',
            'highway_day21_39.dat',
            'highway_day22_46.dat',
            'highway_day23_48.dat',
            'highway_day24_44.dat',
            'highway_day25_47.dat',
            'highway_day26_45.dat',
            'highway_day27_46.dat',
            'highway_day28_42.dat',
            'highway_day29_42.dat',
            'highway_day2_30.dat',
            'highway_day30_41.dat',
            'highway_day3_55.dat',
            'highway_day4_25.dat',
            'highway_day5_15.dat',
            'highway_day6_24.dat',
            'highway_day7_14.dat',
            'highway_day8_24.dat',
            'highway_day9_23.dat',]

