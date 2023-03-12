# ---------- DESCRIPTION ----------------
# This program allows to implement a power load balancing for radiator (also called power dispatch)
# It monitors 
#    - a list of virtual toggle switches (see HA helpers)
#      defined in the list RADIATOR_VIRTUAL_SWITCH_INV_DICT
#      re-listed in TRIGGERs (on and off)
#      that can be controlled manually or more commonly automatically via thermostats
#    - a power saving status mode defined as a numeric helper
#      see INPUT_POWER_SAVING_MODE
#          WARNING: (defined twice as _NAME and _VALUE)
#    - a time pattern under the format of a unix cron command
#      see TIME_STEP
#    - an AWAY_MODE for forcing all heaters off when abscent or during summer
#      Note: if you are using radiator control wire, most likely the off state requires relay activation
#            You may want to avoid that useless wear during summer by adding an extra trip in your home electric pannel.
# It controls on/off radiator status
#    Note: off can be a real off of no freeze mode depending of how control mode is configured/wired
#          control harware can trigger high power cut rapidely and configuration must be electricly safe
#          My STRONG advise is to control the radiator via the control wire (or wireless)
#          rather than by directly swicthing the radiator power feed.
#    - a list of switches controling the actual radiators
#      see RADIATOR_ACTUAL_SWITCH_DICT
#    - reports current status in a state_variable+attributes 
#      see pyscript.radiator_status
#
# At each time step, power mode or radiator configuration change request it will run a round robin and limit
# the number of active radiators to respect the max number of radiator configured via the power mode.
# There is no concept of priority but a radiator can be listed twice.
# If some rooms have multiple radiator, it might be a good idea to seprarate them in the radiator list to smooth the heating.
# The order RADIATOR_VIRTUAL_SWITCH_INV_DICT and RADIATOR_ACTUAL_SWITCH_DICT is not important but each radiator must have a unique entry
# 
#
# ---------- CONFIGURATION ---------------
# Configuration is specific to each house and MUST be aligned with reality
#
# All CONSTANT must be declared in respect of Python3 syntax.
#              Errors will only be reported in home-assistant.log
#
# TEST_MODE = True the actual control the radiator is deactivated
# but reports and log remains as normal
# for normal operation TEST_MODE = False
TEST_MODE = False 
# radiator list by name
# Varing order allows to spread the heat around the house
RADIATOR_LIST = [ 'tv', 'office', 'bedroom','lounge_window', 'kitchen' , 'bathroom' ,  'lounge_entrance' ]
#
# max activate radiator per power saving mode (no, midium, max) 
# Array representing the max number of active radiator per mode
# Note: the first entry reprensent max number of radiator supported
#       when no power saving mode is requested
#       that number must be <= to the number of radiator declated in RADIATOR_LIST
# max number of level is 10. 
RADIATOR_MAX_ACTIVE = [5,3,1,0]
# Power saving mode variable (a helper type input_number)
# UGLY: To avoid importing extra modules it's defined twice with different types
# the second definition is embedded in a function called by trigger
# INPUT_POWER_SAVING_MODE_NAME is a string ('numeric_helper_name')
# INPUT_POWER_SAVING_MODE_VALUE is an array( numeric_helper_name)
INPUT_POWER_SAVING_MODE_NAME  ='input_number.powsersavingmode'
def input_power_saving_value():
    INPUT_POWER_SAVING_MODE_VALUE = input_number.powsersavingmode
    return (INPUT_POWER_SAVING_MODE_VALUE)
# Away status defined by a virtual toggle
#      change activated at the next time_step (not by trigger)
def away_status():
    AWAY_STATUS=str(input_boolean.away_status)
    log.debug(f"AWAY_STATUS={AWAY_STATUS}, input_boolean.away_status")
    return (AWAY_STATUS)
# Step Round Robin every xx in cron format
#   Note: if your radiator control is done via electromagnetic relays
#         don't switch them to often to limit rapid wear (and noise)
TIME_STEP = 'cron(* * * * */2)'
# link radiator_name / switch name
# WARNING: radiator virtual swicthes MUST also be (re)listed in the code : see TRIGGER
# When a thermostat control several radiators key must be repeated for each controlled radiator
# format Dictionary 
#    key   virtual switch controlled by the thermostat
#    value the radiator_name
RADIATOR_VIRTUAL_SWITCH_INV_DICT = {
                        'input_boolean.virtual_heat_tv': 'tv',
                        'input_boolean.virtual_heat_office': 'office',
                        'input_boolean.virtual_heat_bedroom':'bedroom',
                        'light.heating_lounge_group': 'lounge_window',
                        'input_boolean.virtual_heat_kitchen': 'kitchen',
                        'input_boolean.virtual_heat_bathroom': 'bathroom',
                        'light.heating_lounge_group': 'lounge_entrance'}
# format Dictionary
#    key    radiator_name
#    value  switch controling the radiator
RADIATOR_ACTUAL_SWITCH_DICT = {
                        'tv': 'light.relay2_light_5',
                        'office': 'light.tz3000_u3oupgdy_ts0004_light',
                        'bedroom': 'light.tz3000_u3oupgdy_ts0004_light_2',
                        'lounge_window': 'light.relay2_light_6',
                        'kitchen': 'light.tz3000_u3oupgdy_ts0004_light_4',
                        'bathroom': 'light.tz3000_u3oupgdy_ts0004_light_3',
                        'lounge_entrance': 'light.relay2_light_7'}
# -------- END CONFIGURATION ------------

# global vaiables (working copy of persistant state data)
power_saving_mode = 0
round_robin_index = 0
radiator_live_mode = []
radiator_requested_mode = []
for i in range(len(RADIATOR_ACTUAL_SWITCH_DICT)):
    radiator_live_mode.append(0)
    radiator_requested_mode.append(0)

# warning state variables are always read as string
# attributes can carry other types
state.set(
        'pyscript.radiator_status',
        value='none',
        new_attributes={
            'test_mode': TEST_MODE,
            'away_status': '',
            'power_saving_mode': 0,
            'round_robin_index': 0,
            'radiator_requested_mode': radiator_live_mode,
            'radiator_live_mode': radiator_live_mode
        })

# !WARNING: state_trigger requires all input on the same line which then can be very long
@state_trigger("input_boolean.virtual_heat_lounge_window, input_boolean.virtual_heat_bedroom, input_boolean.virtual_heat_office, input_boolean.virtual_heat_lounge_entrance, input_boolean.virtual_heat_tv, input_boolean.virtual_heat_kitchen, input_boolean.virtual_heat_bathroom")
def request_heater_change_on(var_name, value):
    """Thermostat has triggered a radiator off"""
    log.info(f"Radiator mode change triggered change by {var_name} new_value={value} (on:1 off: 0)")
    get_radiator_status()
    # converting status value in int
    value_number={'on':1,'off':0}
    request_heater_change (var_name, value_number[value])

# @state_trigger("input_boolean.virtual_heat_lounge_window == 'off' or input_boolean.virtual_heat_bedroom == 'off' or  input_boolean.virtual_heat_office == 'off' or input_boolean.virtual_heat_lounge_entrance == 'off' or input_boolean.virtual_heat_tv == 'off' or input_boolean.virtual_heat_kitchen == 'off' or input_boolean.virtual_heat_bathroom == 'off' ")
# def request_heater_change_off(var_name, value):
#     """Thermostat has triggered a radiator off"""
#     log.info(f"Radiator mode change triggered change by {var_name} new_value={value} (on:1 off: 0)")
#     get_radiator_status()
#     request_heater_change (var_name, 0)

@state_trigger(INPUT_POWER_SAVING_MODE_NAME)
def request_change_power_saving_mode():
    # input_number are returned as list
    log.info(f"Power Saving Mode change request->{input_power_saving_value()} -> {input_power_saving_value()[0]}")
    roundrobin_step()              
# 
@time_trigger(TIME_STEP)
def request_roundrobinstep():
    get_radiator_status()
    log.info(f"Timer roundrobin_step request")
    roundrobin_step()

# end of initialisation. Further code is only called via configured triggers
log.debug(f"end roundrobin.py intialisation is now waiting for tiggers")
# -----------------------------------------


def get_radiator_status():
    global power_saving_mode, round_robin_index,radiator_live_mode,radiator_requested_mode
    # read status directly from virtual radiator state
    for virtual_radiator in RADIATOR_VIRTUAL_SWITCH_INV_DICT:
        if state.get(virtual_radiator) == 'on':
            radiator_requested_mode[list(RADIATOR_VIRTUAL_SWITCH_INV_DICT.keys()).index(virtual_radiator)] = 1
        else:
            radiator_requested_mode[list(RADIATOR_VIRTUAL_SWITCH_INV_DICT.keys()).index(virtual_radiator)] = 0
        #log.debug(f"virtual_radiator={list(RADIATOR_VIRTUAL_SWITCH_INV_DICT.keys()).index(virtual_radiator)}-> {virtual_radiator}")
    log.debug(f"got_status radiator_requested_mode={radiator_requested_mode}")

def request_heater_change (trigger_name,state):
    global power_saving_mode, round_robin_index,radiator_live_mode,radiator_requested_mode
    radiator_requested_mode [RADIATOR_LIST.index(RADIATOR_VIRTUAL_SWITCH_INV_DICT[trigger_name])] = state
    roundrobin_step()
  
def roundrobin_step():
    global power_saving_mode, round_robin_index,radiator_live_mode,radiator_requested_mode
    log.debug(f"Before round robin stepping")
    log.debug(f"    radiator_requested_mode = {radiator_requested_mode}")
    log.debug(f"    radiator_live_mode      = {radiator_live_mode}")
    # get latest power saving mode
    power_saving_mode=int(input_power_saving_value()[0])
    get_radiator_status()
    round_robin_index = int(pyscript.radiator_status.round_robin_index)
    heater_activation_count=0
    for i in range(len(RADIATOR_LIST)):
        radiator_live_mode[i]=0
    # when house is empty, all heating is forced to off
    if away_status() == 'off':
        for i in range(len(RADIATOR_LIST)):
            if radiator_requested_mode[(i+round_robin_index)%len(RADIATOR_LIST)] == 1:
                heater_activation_count += 1
                # when powersaving_mode is max we stop all heating whatever is requested
                if heater_activation_count > RADIATOR_MAX_ACTIVE[power_saving_mode]:
                    break
                radiator_live_mode[(i+round_robin_index)%len(RADIATOR_LIST)] = 1
        # save roundrbin new index for futher run
        round_robin_index=(i+round_robin_index)%len(RADIATOR_LIST)
    # switch on/off actual heaters starting by off to avoid power surge
    for i in range(len(RADIATOR_LIST)):
        if radiator_live_mode[i] == 0 and not TEST_MODE:
            log.debug(f"Switching actual radiator {RADIATOR_LIST[i]} index {i} 'off' -> {RADIATOR_ACTUAL_SWITCH_DICT[RADIATOR_LIST[i]]}")
            state.set(RADIATOR_ACTUAL_SWITCH_DICT[RADIATOR_LIST[i]], value='off')
        if radiator_live_mode[i] == 1 and not TEST_MODE:
            log.debug(f"Switching actual radiator {RADIATOR_LIST[i]} index {i} 'on' -> {RADIATOR_ACTUAL_SWITCH_DICT[RADIATOR_LIST[i]]}")
            state.set(RADIATOR_ACTUAL_SWITCH_DICT[RADIATOR_LIST[i]], value='on')
        
     # save new state for reuse(roundrobin_index)/info/tracking/debug
    log.info(f"End roundrobin stepping radiator_requested_mode = {radiator_requested_mode}")
    log.info(f"                        radiator_live_mode      = {radiator_live_mode}")
    log.info(f"                        round_robin_index={round_robin_index}")
    log.info(f"                        power_saving_mode={power_saving_mode}->{RADIATOR_MAX_ACTIVE[power_saving_mode]} max")
    log.info(f"                        away_status      ={away_status()}")
    if TEST_MODE:
        log.info(f"                        WARNING TEST_MODE active NO actual radiator control")

    pyscript.radiator_status.test_mode=TEST_MODE
    pyscript.radiator_status.away_status=away_status()
    pyscript.radiator_status.round_robin_index=round_robin_index
    pyscript.radiator_status.power_saving_mode=power_saving_mode
    pyscript.radiator_status.radiator_live_mode=radiator_live_mode
    pyscript.radiator_status.radiator_requested_mode=radiator_requested_mode

