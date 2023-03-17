# ---------- DESCRIPTION ----------------
#
# This program estimates the remaining available power to be used by the heating system.
# 
# Two algorithm modes are available G or I
#    General:    based on overall house energy consumtion
#    Individual: based on non heating energy consumtion
#
# It monitors 
#    - The various meeter available in the house
#      GENERAL_METER  define the unique overall installation meeter
#      EXTRA_METERS   list the meeter attached to large non heater item
# It controls a power_saving_mode
#    The power_saving_mode is a HA numeric variable that is monitored as entry
#    by load power balancing script roundrobin.py  
# Caculation can be done with Ampere (A) or Watts (W) or kW
# You just need to be consistant and always used the same unit.

#-------------- LICENSE ---------------
# Apache V2   http://www.apache.org/licenses/

#------------- CONSTRAINT -------------
# Trip are fast and your code must react faster than the trip
# You rarelay have more than 1 or 2 seconds to correct power use before backout.
# Meters reporting value less than once a second for such use case are useless.

# ---------- CONFIGURATION ---------------
# Configuration is specific to each house and MUST be aligned with reality
#
# All CONSTANT must be declared in respect of Python3 syntax.
#              Errors will only be reported in home-assistant.log

#---------- Energy unit ---------
# The code algorithm does not change whatever is your reference unit (A/W/kW your call)
# but it must be the same for all values
# For info my config work with A, hence the default value in the code

# TEST_MODE = True the actual control the radiator is deactivated
# but reports and log remains as normal
# for normal operation TEST_MODE = False
TEST_MODE = False 

# Numeric HA state variable receiving the estimated power saving index.
# Note: the actual number of active radiator is defined in roundrobin.py
# Number of possible mode must be the same in HA, roundrobin.py and here.
POWER_SAVING_MODE='input_number.powsersavingmode'

# Time in second before we accept to decrease the power_saving_mode.
# If this time is too short, the power saving mode goes down quicker than the radiators
# are switched on and will always reach 0 to then go up again.
# It just a protection to limit relay wearing.
DAMPING_DELAY=90

# Maximum availaible power in the house (same unit as  POWER_PER_RADIATOR)
MAX_AVAILABLE_HOUSE_POWER=30

# Select the type of algorith used fo rthe estimation
# ESTIMATION_MODE='G' The remaining power available for heating is estimated using
#                     the number of active radiator
#                     That mode only required 1 meter (GENERAL_METER)
# ESTIMATION_MODE='I' The remaining power available for heating is estimated using
#                     the actual power used by not heating equipement
#                     It requires additional meter(s) (a list of list)
#                        NON_HEATING_METERS (house non heating energy use)
ESTIMATION_MODE='G'

# Estimated max energy consumtion per radiator 
POWER_PER_RADIATOR=5

# Entity measuring the over power used by the house  (same unit as  POWER_PER_RADIATOR)
# you can use a template to report the meter reading in the right unit.
# The second paramater is a conversion ratio to get all reading on the same unit.
# e.g. is reading is mA using 1000  would convert it in A
#                    kW       0.001 would convert it in W
# Format ('meter_entity','attribute', unit_convertion_ratio)
# if 'attribute' is empty data is read from entity status
GENERAL_METER=('sensor.enedis_amp','',1)

# This code is triggered each time that the house power consumsion changes which means often
# HYSTERIS_FACTOR is design to smooth down the decrease of power_saving_mode
# while leaving a fast reaction when power_saving_mode needs to be increased.
HYSTERESIS_FACTOR=1.2

# Due to embedded thermostat we cannot know if a radiator draw power when it's 'on'
# We can only guess a factor to cover that risk
# Higher accuracy requires higher target temperature on the embbeded thermostat
# Schedule starting many radiator change at the same time will reduce accuracy
SAFE_RATIO=1.3


#------- required for ESTIMATION_MODE == 'I' ----------
# list of list of on or several meter(s) reading all significant non heating equipement
# Note: MUST remain a list of list even with only one meter defined
# The first parameter is the name of entity provinding the meter reading
# The second is a conversion ratio to get all reading on the same unit.
# The reading value must be in the variable state and it expected to be a string representing a float.
# Would the reading be in an attribute a template should created externally.
# Format (('meter_entity', 'attribute', unit_convertion_ratio),(...))
# if 'attribute' is empty data is read from entity status
NON_HEATING_METERS=(('sensor.washing_machine_rms_current','',1000), ('sensor.dish_washer_rms_current','',1000))

# Security margin to cover energy requirement not measured by EXTRA_METERS
SECURITY_MARGIN=3

#---------- IMPORT ----------
import time

#--------- IMPORTED DATA --------
# Lists reported by roudrobin.py in state variables
# Leave time to roundrobin.py to create the requered state variable on a cold boot (time in second)
while pyscript.radiator_status.radiator_live_mode == None:
    task.sleep(5)
MAX_RADIATORS_ON=float(state.get('pyscript.radiator_status.power_saving_mode_steps')[0])
ACTIVE_RADIATORS='pyscript.radiator_status.radiator_live_mode'

#---------STATE VARIABLE ---------
# data required between triggers
# EPOC unix time in second
# heating_remaining_power is provided for potential external application or autoamation
state.set(
        'pyscript.powerstate_status',
        value='none',
        new_attributes={
            'heating_remaining_power' : 0,
            'time_last_decrease': int(time.time())
        })

# extracting meter data
def read_data(sensor):
    reading=float(0)
    if sensor[1] == '':
        # data is directlty in state variable status
        reading=float(state.get(sensor[0]))
    else:
       # data is in an attribute
       reading=float(state.getattr(sensor[0],sensor[1]))
    return(reading/sensor[2])

# Adding all sensors reading only needed when ESTIMATION=='I'
def add_data(meters_list):
    data=float(0)
    for i in meters_list:
        data=data+read_data(i)
    return(data)


#--------- TRIGGER --------------
#
# Trigger each time general meeter value changes
@state_trigger(GENERAL_METER[0]+GENERAL_METER[1])
def power_meter_new_reading (value):
    # new trigger arrive before end of processing the previous one, the ignore previous value 
    task.unique("power meeter_changed_value", kill_me=False)
    log.info(f"powersavingmode.py: General power meter new_value={value}")
    estimate_power_saving_mode()

# Estimation of a new per saving mode
def estimate_power_saving_mode():
    if ESTIMATION_MODE=='G':
        heating_remaining_power=MAX_AVAILABLE_HOUSE_POWER-read_data(GENERAL_METER)+ACTIVE_RADIATORS.count('1')*POWER_PER_RADIATOR/SAFE_RATIO
    else:
        heating_remaining_power=MAX_AVAILABLE_HOUSE_POWER-add_data(NON_HEATING_METERS)-SECURITY_MARGIN
    log.debug(f"powersavingmode.py: estimated available power={heating_remaining_power:2.2f}")
    state.setattr('pyscript.powerstate_status.heating_remaining_power',heating_remaining_power)

    # power_saving_mode=0 indicates max power available for the heating system.
    # when available power is reducing, we need to be quick to increase the saving_power_mode
    if heating_remaining_power < POWER_PER_RADIATOR*SAFE_RATIO and not TEST_MODE:
        log.debug(f"powersavingmode.py: saving_power_mode +1")
        service.call('input_number','increment',blocking=False, entity_id=POWER_SAVING_MODE)
    # hysteresis is created when available power increases to reduce wear on electromagnetic relays.
    if heating_remaining_power > POWER_PER_RADIATOR*SAFE_RATIO*HYSTERESIS_FACTOR and not TEST_MODE:
        # We want to slow down powersavingmode decrease
        if int(time.time()) > int(pyscript.powerstate_status.time_last_decrease)+DAMPING_DELAY:
            log.debug(f"powersavingmode.py: saving_power_mode -1 time {int(time.time())} , {int(pyscript.powerstate_status.time_last_decrease)+DAMPING_DELAY}")
            state.setattr('pyscript.powerstate_status.time_last_decrease', int(time.time()))
            service.call('input_number','decrement',blocking=False, entity_id=POWER_SAVING_MODE)
    
    # debug only    
    log.debug(f"powersavingmode.py: saving_power_mode        ={state.get(POWER_SAVING_MODE)}")
    log.debug(f"powersavingmode.py: general_meter_reading    ={read_data(GENERAL_METER):2.2f}")