import math
from time import time, sleep
from db import db
from net import get_targets


class ClimateChamber:
    def __init__(self, initial_data):
        self.red = 1
        self.blue = 1
        self.white = 1
        self.initial_volume = initial_data["initial_volume"]
        self.temperature_celsius = initial_data["initial_temperature_celsius"]
        self.relative_humidity = initial_data["initial_relative_humidity"]
        self.balast = 200 #kg 
        self.ballast_heat_capacity = 2500 #Heat capacity of ballast. J/(kg·K)
        self.air_specific_heat_cp = 1005 #Constant heat capacity of air. J/(kg·K)
        self.water_vapor_specific_heat_cp = 2051 #Constant heat capacity of water vapor. J/(kg·K)
        self.ambient_temperature = 5 + 273.15 #Ambient temperature in kelvins.
        self.heat_loss_coefficient = 0.5 # W/(m²·K)
        self.rib_width = 2 # meters
        self.rib_height = 2 # meters
        self.rib_length = self.initial_volume / (self.rib_width*self.rib_height) #Calculating the length of the greenhouse, given the volume and assuming a height and width of 2 meters each.
        self.square = 2*(self.rib_length*self.rib_width + self.rib_length*self.rib_height + self.rib_width*self.rib_height) + self.rib_length*self.rib_width
        self.temperature_kelvins = self.temperature_celsius + 273.15
        self.standard_atmospheric_pressure = 101325 #Constant - atmospheric pressure is assumed to be 101325 Pa.
        self.constant_steam = 461.495 #Constant - specific gas constant for steam (461.495 J/kg·K).
        self.heater = 500 #J
        self.steam_generator = 0.0001 #kg
        self.air_density = self.get_density_humid_air(self.temperature_kelvins, self.relative_humidity)
        self.dry_air_mass, self.steam_mass = self.get_air_and_water_vapor_mass(self.initial_volume, self.relative_humidity, self.air_density, self.temperature_kelvins)
        self.air_thermal_energy = self.get_substance_thermal_energy(self.dry_air_mass, self.air_specific_heat_cp, 0, self.temperature_kelvins)
        self.steam_thermal_energy = self.get_substance_thermal_energy(self.steam_mass, self.water_vapor_specific_heat_cp, 0, self.temperature_kelvins)
        self.system_thermal_energy =  self.air_thermal_energy + self.steam_thermal_energy
        self.target_temperature_kelvins = self.temperature_kelvins
        self.target_relative_humidity = self.relative_humidity
        
    #Displaying the initial parameters of the system.    
    def get_system_state(self):
        return_str =\
        f"initial_volume = {self.initial_volume} m³\n" \
        f"square = {self.square} m²\n" \
        f"initial_temperature = {self.temperature_celsius} °C\n" \
        f"temperature_kelvins = {self.temperature_kelvins} K\n" \
        f"relative_humidity = {self.relative_humidity} %\n" \
        f"calculated_air_density = {self.air_density} kg/m³\n" \
        f"dry_air_mass = {self.dry_air_mass} kg\n" \
        f"steam_mass = {self.steam_mass} kg\n" \
        f"air_thermal_energy = {self.air_thermal_energy/1000:.3f} kJ\n" \
        f"steam_thermal_energy = {self.steam_thermal_energy/1000:.3f} kJ\n" \
        f"system_thermal_energy = {self.system_thermal_energy/1000:.3f} kJ\n"
        return return_str

    def gey_heat_loss(self):
        return self.heat_loss_coefficient * self.square * (self.temperature_kelvins - self.ambient_temperature)
    
    #Calculating the air density at a given temperature and relative humidity.
    #https://courses.lumenlearning.com/suny-physics/chapter/13-6-humidity-evaporation-and-boiling/
    def get_density_humid_air(self, temperature_kelvins, relative_humidity):
        gas_constant = 287.058
        partial_pressure_saturated_vapor = 1.84*10**11*math.exp(-5330/temperature_kelvins)
        water_vapor_pressure = (relative_humidity/100)*partial_pressure_saturated_vapor
        partial_pressure = self.standard_atmospheric_pressure - water_vapor_pressure
        p_humid_air = partial_pressure/(gas_constant*temperature_kelvins) + (water_vapor_pressure/(self.constant_steam * temperature_kelvins))
        return p_humid_air
    
    #Calculating the mass fractions of dry air and water vapor in a given volume of air, with a specified density
    # and specified relative humidity.
    #https://courses.lumenlearning.com/suny-physics/chapter/13-6-humidity-evaporation-and-boiling/
    def get_air_and_water_vapor_mass(self, volume, relative_humidity, air_density, temperature_kelvins):
        air_mass = volume * air_density
        partial_pressure_saturated_vapor = 1.84*10**11*math.exp(-5330/temperature_kelvins)
        water_vapor_pressure = (relative_humidity/100)*partial_pressure_saturated_vapor
        steam_mass = (water_vapor_pressure * volume) / (self.constant_steam*temperature_kelvins)
        dry_air_mass = air_mass - steam_mass
        return [dry_air_mass, steam_mass]

    # Q = m * C * ΔT
    def get_substance_thermal_energy (self, mass, heat_capacity, T0, T1):
        return  mass * heat_capacity * (T1 - T0)
    
    # ΔT = Q / m * C
    def get_substance_delta_t (self, energy, mass, heat_capacity):
        return energy / (mass * heat_capacity)

    def set_target(self, temperature, relative_humidity, red, blue, white):
        self.target_temperature_kelvins = temperature + 273.15
        self.target_relative_humidity = relative_humidity
        self.red = red
        self.blue = blue
        self.white = white

    def get_relative_humidity(self, temperature_kelvins, system_mass, volume):
        partial_pressure_saturated_vapor = 1.84*10**11*math.exp(-5330/temperature_kelvins)
        nv = partial_pressure_saturated_vapor / (8.314*temperature_kelvins)
        p = nv*0.018
        relative_humidity = ((system_mass/volume)/p)*100
        return relative_humidity

    def calc_system_parms_energy(self):
        system_heat_capacity_mass = self.dry_air_mass*self.air_specific_heat_cp + self.steam_mass*self.water_vapor_specific_heat_cp + self.balast*self.ballast_heat_capacity
        dry_air_mass_percent = (100 * self.dry_air_mass * self.air_specific_heat_cp ) / system_heat_capacity_mass
        if (self.temperature_kelvins < self.target_temperature_kelvins):
            self.air_thermal_energy += (dry_air_mass_percent*(self.heater - self.gey_heat_loss())) / 100
        else:
            self.air_thermal_energy += (dry_air_mass_percent*(- self.gey_heat_loss())) / 100
        self.temperature_kelvins = self.get_substance_delta_t(self.air_thermal_energy, self.dry_air_mass, self.air_specific_heat_cp)
        if (self.relative_humidity < self.target_relative_humidity):
            self.steam_mass += self.steam_generator
        self.relative_humidity = self.get_relative_humidity(self.temperature_kelvins, self.steam_mass, self.initial_volume)
        self.air_density = self.get_density_humid_air(self.temperature_kelvins, self.relative_humidity)
        new_mass = self.air_density*self.initial_volume
        old_mass = self.dry_air_mass + self.steam_mass
        mass_coeficient = new_mass / old_mass
        self.dry_air_mass = self.dry_air_mass * mass_coeficient
        self.steam_mass = self.steam_mass * mass_coeficient

        self.air_thermal_energy = self.get_substance_thermal_energy(self.dry_air_mass, self.air_specific_heat_cp, 0, self.temperature_kelvins)
        self.steam_thermal_energy = self.get_substance_thermal_energy(self.steam_mass, self.water_vapor_specific_heat_cp, 0, self.temperature_kelvins)
        self.system_thermal_energy =  self.air_thermal_energy + self.steam_thermal_energy

    def system_parms_checker(self):
        self.calc_system_parms_energy()
        
initial_data = {
    "initial_volume": 10,
    "initial_temperature_celsius": 12.6968,
    "initial_relative_humidity": 70
}

chamber = ClimateChamber(initial_data)
print(chamber.get_system_state().encode('utf-8').decode('cp1251'))
targets = get_targets()
chamber.set_target(targets['temperature_celsius'], targets['relative_humidity'], targets['red'], targets['blue'], targets['white'])
db_conection = db()
db_conection.incert_data((chamber.temperature_kelvins - 273.15), chamber.relative_humidity, chamber.red, chamber.blue, chamber.white)
start_time = time()
db_start_time = time()
counter = 0
chamber.system_parms_checker()
while True:
    if (start_time + counter < time()):
        chamber.system_parms_checker()
        counter += 1
    else:
        sleep(0.001)
    if db_start_time + 10 < time():
        db_conection = db()
        db_conection.incert_data((chamber.temperature_kelvins - 273.15), chamber.relative_humidity, chamber.red, chamber.blue, chamber.white)
        targets = get_targets()
        chamber.set_target(targets['temperature_celsius'], targets['relative_humidity'], targets['red'], targets['blue'], targets['white'])
        print(targets)
        db_start_time = time()



        