# ---------- DESCRIPTION ----------------
#
# This program estimates the remaining available power to be used by the heating system.
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

# TEST_MODE = True the actual control the radiator is deactivated
# but reports and log remains as normal
# for normal operation TEST_MODE = False
TEST_MODE = False 

# Numeric HA state variable receiving the estimated power saving index.
# Note: the actual number of active radiator is defined in roundrobin.py
# Number of possible mode must be the same in HA, roundrobin.py and here.
POWER_SAVING_MODE='input_number.powsersavingmode'

# Estimated max energy consumtion per radiator (A/W/kW your call) my config work with A
POWER_PER_RADIATOR=5

# Due to embedded thermostat we cannot know if a radiator draw power when it's 'on'
# We can only guess a factor to cover that risk
# Higher accuracy requires higher target temperature on the embbeded thermostat
# Schedule starting many radiator change at the same time will reduce accuracy
SAFE_RATIO=2

# This code is triggered each time that the house power consumsion changes which means often
# HYSTERIS_FACTOR is design to smooth down the decrease of power_saving_mode
# while leaving a fast reaction when power_saving_mode needs to be increased.
HYSTERESIS_FACTOR=1.2

# Time in second before we accept to decrease the power_saving_mode.
# If this time is too short, the power saving mode goes down quicker than the radiators
# are switched on and will always reach 0 to then go up again.
# It just a protection to limit relay wearing.
DAMPING_DELAY=90

# Maximum availaible power in the house (same unit as  POWER_PER_RADIATOR)
MAX_AVAILABLE_HOUSE_POWER=30

# Entity measuring the over power used by the house  (same unit as  POWER_PER_RADIATOR)
# you can use a template to report the meter reading in the right unit.
# The second paramater is a conversion ratio to get all reading on the same unit.
GENERAL_METER=('sensor.enedis_amp',1)

# list of meters placed on energy hungry non heating equipement (e.g. washing machine)
# The first parameter is the name of entity provinding the meter reading
# The second is a conversion ratio to get all reading on the same unit. 
EXTRA_METERS=(('sensor.washing_machine_rms_current',1000), ('sensor.dish_washer_rms_current',1000))

# Step Round Robin every xx in cron format
#   e.g. every second      -> TIME_STEP = 'cron(* * * * *)'
#   Note: It must be fast enough to not blackout
TIME_STEP = 'cron(* * * * *)'

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


#--------- TRIGGER --------------
#
# Trigger each time general meeter value changes
@state_trigger(GENERAL_METER[0])
def power_meter_new_reading (value):
    # new trigger arrive before end of processing the previous one, the ignore previous value 
    task.unique("power meeter_changed_value", kill_me=False)
    log.info(f"powersavingmode.py: General power meter new_value={value}")
    estimate_power_saving_mode(float(value))

# Estimation of a new per saving mode
def estimate_power_saving_mode(general_meter_reading):
    # TODO Summing all available large metered equipement (if any)
    # extra_total_power=0
    # for i in range(len(EXTRA_METERS)):
    #     # reading meeter and applying ratio correction to unify units
    #     log.debug(f"powersavingmode.py: reading extra meter -> {EXTRA_METERS[i]} ")
    #     extra_total_power=extra_total_power+float(eval(EXTRA_METERS[i][0]))/EXTRA_METERS[i][1]
    # estimating the remaining available heating power
    heating_remaining_power=MAX_AVAILABLE_HOUSE_POWER-general_meter_reading+ACTIVE_RADIATORS.count('1')*POWER_PER_RADIATOR/SAFE_RATIO
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
    log.debug(f"powersavingmode.py: general_meter_reading    ={general_meter_reading:2.2f}")