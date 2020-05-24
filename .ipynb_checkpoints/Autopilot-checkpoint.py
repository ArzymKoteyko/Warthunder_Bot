import pycurl
from io import BytesIO
import json
import math
import time
from multiprocessing.pool import ThreadPool
import ctypes
import scipy.interpolate
import numpy as np
import win32api

SendInput = ctypes.windll.user32.SendInput

W = 0x11
A = 0x1E
S = 0x1F
D = 0x20


KeyCodes = {'W'    : 0x11,
            'A'    : 0x1E,
            'S'    : 0x1F,
            'D'    : 0x20,
            'Q'    : 0x10,
            'E'    : 0x12,
            'F'    : 0x21,
            'G'    : 0x22,
            '['    : 0x1A,
            ']'    : 0x1B,
            'SPACE': 0x00}

# C struct redefinitions 
PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time",ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                 ("mi", MouseInput),
                 ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

# Actuals Functions

def PressKey(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput( 0, hexKeyCode, 0x0008, 0, ctypes.pointer(extra) )
    x = Input( ctypes.c_ulong(1), ii_ )
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def ReleaseKey(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput( 0, hexKeyCode, 0x0008 | 0x0002, 0, ctypes.pointer(extra) )
    x = Input( ctypes.c_ulong(1), ii_ )
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
    
def MoveMouse(x, y):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    x = int(x*(65536/ctypes.windll.user32.GetSystemMetrics(0))+1)
    y = int(y*(65536/ctypes.windll.user32.GetSystemMetrics(1))+1)
    ii_.mi = MouseInput(x, y, 0, 0x0001 | 0x8000, 1, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(0), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def _to_windows_coordinates(x=0, y=0):
    display_width = win32api.GetSystemMetrics(0)
    display_height = win32api.GetSystemMetrics(1)

    windows_x = (x * 65535) // display_width
    windows_y = (y * 65535) // display_height
    return windows_x, windows_y

def _interpolate_mouse_movement(start_windows_coordinates, end_windows_coordinates, steps=20):
    x_coordinates = [start_windows_coordinates[0], end_windows_coordinates[0]]
    y_coordinates = [start_windows_coordinates[1], end_windows_coordinates[1]]

    if x_coordinates[0] == x_coordinates[1]:
        x_coordinates[1] += 1

    if y_coordinates[0] == y_coordinates[1]:
        y_coordinates[1] += 1

    interpolation_func = scipy.interpolate.interp1d(x_coordinates, y_coordinates)

    intermediate_x_coordinates = np.linspace(start_windows_coordinates[0], end_windows_coordinates[0], steps + 1)[1:]
    coordinates = list(map(lambda x: (int(round(x)), int(interpolation_func(x))), intermediate_x_coordinates))
    
    return coordinates
    
def move(x=None, y=None, duration=0.25, absolute=True, interpolate=False, **kwargs):

    if (interpolate):
        
        #print("mouse move {}".format(interpolate))
        
        current_pixel_coordinates = win32api.GetCursorPos()
        if interpolate:
            current_pixel_coordinates = win32api.GetCursorPos()
            start_coordinates = _to_windows_coordinates(*current_pixel_coordinates)
            
            end_coordinates = _to_windows_coordinates(x, y)
                  
            coordinates = _interpolate_mouse_movement(
                start_windows_coordinates=start_coordinates,
                end_windows_coordinates=end_coordinates
            )
        else:
            coordinates = [end_coordinates]
        
        for x, y in coordinates:
            extra = ctypes.c_ulong(0)
            ii_ = Input_I()
            ii_.mi = MouseInput(x, y, 0, (0x0001 | 0x8000), 0, ctypes.pointer(extra))
            x = Input(ctypes.c_ulong(0), ii_)
            ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

            time.sleep(duration / len(coordinates))
    else:
        x = int(x)
        y = int(y)

        coordinates = _interpolate_mouse_movement(
            start_windows_coordinates=(0, 0),
            end_windows_coordinates=(x, y)
        )
        
        for x, y in coordinates:
            extra = ctypes.c_ulong(0)
            ii_ = Input_I()
            ii_.mi = MouseInput(x, y, 0, 0x0001, 0, ctypes.pointer(extra))
            x = Input(ctypes.c_ulong(0), ii_)
            ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

            time.sleep(duration / len(coordinates))
            

#========================================================================================================#

#
# Server_reader
# класс создающий инстанс который получает информацию с локльного сервера игры
# инстанс привязывается лишь к одной ссылке
# 

class Server_Reader:
    
    def __init__(self, URL):
        self.URL = URL
        self.CURL = pycurl.Curl()
        self.last_data = BytesIO()
      
    # функция get_data получает информацию с сервера
    # и возвращает запарсенный json
    def get_data(self, timeout = 1):
        buffer = BytesIO()
        
        self.CURL.setopt(self.CURL.URL, self.URL)
        self.CURL.setopt(pycurl.TIMEOUT, timeout)
        self.CURL.setopt(self.CURL.WRITEDATA, buffer)
        
        try:
            self.CURL.perform()
            self.last_data = buffer
            return json.loads((buffer.getvalue()).decode('iso-8859-1'))
            
        except:
            return json.loads((self.last_data.getvalue()).decode('iso-8859-1'))

    def __str__(self):
        return self.URL
    
    def __del__(self):
        self.CURL.close()
        del(self.CURL)

#
# Server_Reader_Controller
# класс отвечающий за возможность поралельного использования Server_Reader
# 

class Server_Reader_Controller:
    
    def __init__(self):
        self.server_readers = []
        self.pool = ThreadPool(processes=4)
    
    def add_server_reader(self, url):
        self.server_readers.append(Server_Reader(url))
        
        
    def perform(self):
        async_result = [0 for i in range(len(self.server_readers))]
        self.results = [0 for i in range(len(self.server_readers))]
        
        for i in range(len(self.server_readers)):
            async_result[i] = self.pool.apply_async(self.server_readers[i].get_data)
        for i in range(len(self.server_readers)):
            self.results[i] = async_result[i].get()
        return self.results
    
    def __str__(self):
        string = ''
        for i in self.server_readers:
            string += str(i) + '\n'
        return string
    
    def __del__(self):
        for reader in self.server_readers:
            del(reader)
            

#========================================================================================================#        

def sigmoid(x, cof):
    return 1 / (1 + math.exp(-cof * x))

#
#
#
#

class Axese_Controller:
   
    def __init__(self, possitive_button, negative_button, time_per_cycle = 0.03125, cycle_ammount = 8):
        self.possitive_button = possitive_button
        self.negative_button  = negative_button
        self.time_per_cycle   = time_per_cycle
        self.cycle_ammount    = cycle_ammount
    
    def _Pulse_Width_Modulation(self, power):
        for cycle in range(self.cycle_ammount):
            tick = self.time_per_cycle / 100
            if power > 0:
                PressKey(KeyCodes[self.possitive_button])
                #print(tick * power, tick * (100 - power))
                time.sleep(math.fabs(tick * power))
                ReleaseKey(KeyCodes[self.possitive_button])
                time.sleep(math.fabs(tick * (100 - power)))
            elif power < 0:
                PressKey(KeyCodes[self.negative_button])
                time.sleep(math.fabs(tick * power))
                ReleaseKey(KeyCodes[self.negative_button])
                time.sleep(math.fabs(tick * (100 - power)))
            else:
                time.sleep(self.time_per_cycle)

#
#
#
#

class Pitch_Controller(Axese_Controller):
    def __init__(self):
        Axese_Controller.__init__(self, possitive_button = 'S', negative_button = 'W')
    
    def perform(self, mode = 'angle', **kwargs):
        
        #print('Pitch')
        if mode == 'angle':
            for key, value in kwargs.items(): 
                if key == 'target_angle':
                    target_angle= value
                if key == 'current_angle':
                    current_angle = value
                    
            delta_angle = target_angle - current_angle
            power = int((sigmoid(delta_angle, 0.03125)-0.5)*200)
            
            #print('delta_angle :', delta_angle)    
            #print('power :', power)
            
        
            
        if mode == 'climb':
            for key, value in kwargs.items(): 
                if key == 'target_climb':
                    target_climb = value
                if key == 'current_climb':
                    current_climb = value
                    
            delta_climb = target_climb - current_climb
            delta_climb *= 4
            power = int((sigmoid(delta_climb, 0.015625)-0.5)*200)
        
            #print('delta_climb :', delta_climb)    
            #print('power :', power)
        
        if mode == 'power':
            for key, value in kwargs.items():
                if key == 'power':
                    power = int(value)
            #print('power', power)
        
        self._Pulse_Width_Modulation(power)
        
        return 1
        
#
#
#
#
    
class Roll_Controller(Axese_Controller):

    def __init__(self):
        Axese_Controller.__init__(self, possitive_button = 'A', negative_button = 'D')
    
    def perform(self, **kwargs):
        
        for key, value in kwargs.items(): 
            if key == 'target_angle':
                target_angle = value 
            if key == 'current_angle':
                current_angle = value 
                    
        delta_angle = target_angle - current_angle
        power = int((sigmoid(delta_angle, 0.5)-0.5)*200)
            
        #print('Roll')
        print('delta_angle :', delta_angle)    
        #print('power :', power)
        
        self._Pulse_Width_Modulation(power)
        
        return 1
        
#
#
#
#
    
class Yaw_Controller(Axese_Controller):
    def __init__(self):
        Axese_Controller.__init__(self, possitive_button = 'Q', negative_button = 'E')
        
    def perform(self, **kwargs):
        
        for key, value in kwargs.items(): 
            if key == 'power':
                power = value 
        
        self._Pulse_Width_Modulation(power)
        
        return 1
    
#
# 
#
#

class Mechanisation_Controller:
    
    def __init__(self):
        self.Pitch = Pitch_Controller()
        self.Roll  = Roll_Controller()
        self.Yaw   = Yaw_Controller()
        self.pool = ThreadPool(processes=3)
        
    def perform(self, current_roll, target_roll, pitch_mode = 'climb', **kwargs):
        
        async_result = [0 for i in range(3)]
        
        if pitch_mode == 'angle':
            for key, value in kwargs.items(): 
                if key == 'target_angle':
                    target_angle = value
                if key == 'current_angle':
                    current_angle = value
            async_result[0] = self.pool.apply_async(self.Pitch.perform, [], {'mode': 'angle', 'current_angle': current_angle, 'target_angle': target_angle})
                
        elif pitch_mode == 'climb':
            for key, value in kwargs.items():
                if key == 'target_climb':
                    target_climb = value
                if key == 'current_climb':
                    current_climb = value
            async_result[0] = self.pool.apply_async(self.Pitch.perform, [], {'mode': 'climb', 'current_climb': current_climb, 'target_climb': target_climb})
                
        elif pitch_mode == 'power':
            for key, value in kwargs.items(): 
                if key == 'power':
                    power = value 
            async_result[0] = self.pool.apply_async(self.Pitch.perform, [], {'mode': 'power', 'power': power})
        
        for key, value in kwargs.items():
            if key == 'yaw_power':
                yaw_power = value
        
        async_result[1] = self.pool.apply_async(self.Roll.perform, [], {'current_angle': current_roll, 'target_angle': target_roll})
        async_result[2] = self.pool.apply_async(self.Yaw.perform, [], {'power': yaw_power})
        
        for i in range(2):
            async_result[i].get()
               
#========================================================================================================#

#
#
#
#

class Autopilot:
    
    x = 0.5
    y = 0.5
    azimuth = 0
    
    pitch = 0
    climb = 0
    roll  = 0
    
    route = []
    current_checkpoint_id = 0
    
    def __init__(self):
        
        self.mechanisation = Mechanisation_Controller()
        self.server = Server_Reader_Controller()
        self.server.add_server_reader('http://localhost:8111/indicators')
        self.server.add_server_reader('http://localhost:8111/state')
        self.server.add_server_reader('http://localhost:8111/map_obj.json')
        self.server.add_server_reader('http://localhost:8111/map_info.json')
        
    def _update_info(self):
        info = self.server.perform()
        for entity in info[2]:
            if entity['icon'] == 'Player':
                self.x = entity['x']
                self.y = entity['y']
        
        self.azimuth = info[0]['compass']
        self.pitch   = info[0]['aviahorizon_pitch']
        self.climb   = info[1]['Vy, m/s']
        self.roll    = info[0]['aviahorizon_roll']
        
        
    def add_checkpoint_to_route(self, target_x, target_y):
        self.route.append([target_x, target_y])
        
    def remove_checkpoint_from_route(self, checkpoint_id):
        self.route.pop(checkpoint_id)
    
    def _distance_to_next_checkpoint(self):
        return ((self.x - self.route[self.current_checkpoint_id][0])**2 + (self.y - self.route[self.current_checkpoint_id][1])**2)**0.5
    
    def _angle_to_next_checkpoint(self):
        delta_x = self.x - self.route[self.current_checkpoint_id][0]
        delta_y = self.y - self.route[self.current_checkpoint_id][1]
    
        if delta_x == 0:
            delta_x = 0.000001
    
        tan_betta = delta_y/delta_x
        betta = np.arctan(tan_betta) * 57.2958
    
        #DEBUG
        #print('tan_betta:', tan_betta, '\t\tbetta:', betta)
    
        if delta_x > 0:
            if delta_y > 0:
                target_azimuth = 270 + math.fabs(betta)
            else:
                target_azimuth = 270 - math.fabs(betta)
        else:
            if delta_y > 0:
                target_azimuth = 90 - math.fabs(betta)
            else:
                target_azimuth = 90 + math.fabs(betta)
    
        difference_1 = self.azimuth - target_azimuth
        if difference_1 >= 0:
            difference_2 = (360 - difference_1) * -1
        else:
            difference_2 = (360 + difference_1) 
            
        print('angle_1 :', difference_1)
        print('angle_2 :', difference_2)
        
        if math.fabs(difference_1) < math.fabs(difference_2):
            difference = difference_1
        else:
            difference = difference_2
            
    
        return difference
    
    def _chose_climb_rate(self):
        return climb_rate
    
    def _chose_angle(self):
        return angle
    
    def _chose_flaps_state(self):
        return flaps_state
    
    def _chose_gears(self):
        return gears
    
    def move_to_next_check_point(self):
        start_time = time.time()
        while time.time() - start_time < 60:
            #self.mechanisation.perform(pitch_mode = 'power', current_roll=self.roll, target_roll=-40, power = 50)
            
            angle = self._angle_to_next_checkpoint()
            print('roll: ', self.roll)
            print('angle:', angle)
            print('distance to point:', self._distance_to_next_checkpoint())
            print('-'*44)
            if angle > -360 and angle < -50:
                self.mechanisation.perform(pitch_mode = 'power', current_roll=self.roll, target_roll=-90, power = 100, yaw_power = 0)
            if angle > -50 and angle < -20:
                self.mechanisation.perform(pitch_mode = 'power', current_roll=self.roll, target_roll=-30, power = 20, yaw_power = 0)
            if angle > -20 and angle < -5:
                self.mechanisation.perform(pitch_mode = 'power', current_roll=self.roll, target_roll=0, power = 0, yaw_power = -20)
            if angle > -5 and angle < -0.1:
                self.mechanisation.perform(pitch_mode = 'power', current_roll=self.roll, target_roll=0, power = 0, yaw_power = -5)
            if angle > -0.5 and angle < 0.1:
                pass
            if angle > 0.5 and angle < 5:
                self.mechanisation.perform(pitch_mode = 'power', current_roll=self.roll, target_roll=0, power = 0, yaw_power = 5)
            if angle > 5 and angle <20:
                self.mechanisation.perform(pitch_mode = 'power', current_roll=self.roll, target_roll=0, power = 0, yaw_power = 20)
            if angle > 20 and angle < 50:
                self.mechanisation.perform(pitch_mode = 'power', current_roll=self.roll, target_roll=30, power = 20, yaw_power = 0)
            if angle > 50 and angle < 360:
                self.mechanisation.perform(pitch_mode = 'power', current_roll=self.roll, target_roll=90, power = 100, yaw_power = 0)
            
            self._update_info()
            

                
    
    def fly_straight(self):
        pass
    
    def perfome_takeoff(self):
        pass
    
    def perfome_landing(self):
        pass
    
    def run(self, working_time = 60):
        
        start_time = time.time()
        
        while time.time - start_time < working_time:
            pass
      
    def __del__(self):
        pass
    
    
AI = Autopilot()

AI.add_checkpoint_to_route(0.402030, 0.575304)
#AI.add_checkpoint_to_route(0.475565, 0.495412)
AI.add_checkpoint_to_route(0.5, 0.3)
AI.add_checkpoint_to_route(0.6, 0.4)
AI.add_checkpoint_to_route(0.6, 0.6)
AI.add_checkpoint_to_route(0.4, 0.6)

AI._update_info()

AI.move_to_next_check_point()