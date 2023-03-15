# ---------- DESCRIPTION ----------------
#
# This program allows to implement a power load balancing for radiator (also called energy dispatch)
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
# A 'boost_mode' is supported to ignore Thermostat input for a given radiator.
# If some rooms have multiple radiator, it might be a good idea to seprarate them in the radiator list to smooth the heating.
# The order RADIATOR_VIRTUAL_SWITCH_INV_DICT and RADIATOR_ACTUAL_SWITCH_DICT is not important but each radiator must have a unique entry
# 
# A service named 'pyscript.round_robin_boost_mode' allows to force a boost mode change on a given radiator in order to ignore Thermostat request
# It can be used to force a radiator to remain 'on' until force off again (there is no timeout)
# It takes 2 parameters (a valid radiator name and an on/off status)
#   service: pyscript.round_robin_boost_mode
#   data:
#     radiator: tv
#     state: "on"
 
#-------------- LICENSE ---------------
# Apache V2   http://www.apache.org/licenses/

# ---------- CONFIGURATION ---------------
# Configuration is specific to each house and MUST be aligned with reality
#
# All CONSTANT must be declared in respect of Python3 syntax.
#              Errors will only be reported in home-assistant.log

# TEST_MODE = True the actual control the radiator is deactivated
# but reports and log remains as normal
# for normal operation TEST_MODE = False
TEST_MODE = False 

# max activate radiator per power saving mode (no, midium, max) 
# Array representing the max number of active radiator per mode
# Note: the first entry reprensent max number of radiator supported
#       when no power saving mode is requested
#       that number must be <= to the number of radiator declated in RADIATOR_LIST
# max number of level is 10. 
RADIATOR_MAX_ACTIVE = [5,4,2,1,0]

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
#   e.g. every other minute      -> TIME_STEP = 'cron(*/2 * * * *)'
#        every 5 seconds (debug) -> TIME_STEP = 'cron(* * * * */5)'
#   Note: if your radiator control is done via electromagnetic relays
#         don't switch them to often to limit rapid wear (and noise)
TIME_STEP = 'cron(*/2 * * * *)'

#
# Radiator list by name
# Varing order allows to spread the heat around the house during high power save period
RADIATOR_LIST = [ 'tv', 'office', 'bedroom','lounge_window', 'kitchen' , 'bathroom' ,  'lounge_entrance' ]

# Link each radiator (or group of) to an input controring switch
# !!! WARNING: radiator virtual swicthes MUST also be (re)listed in the code : see TRIGGER
# When a thermostat control several radiators value must be repeated for each controlled radiator
# format Dictionary 
#    key   radiator_name
#    value virtual switch controlled by the thermostat
RADIATOR_VIRTUAL_SWITCH_DICT = {
                        'tv': 'switch.virtual_virtual_radiator_tv',
                        'office': 'switch.virtual_virtual_radiator_office',
                        'bedroom': 'switch.virtual_virtual_radiator_bedroom',
                        'lounge_window': 'switch.virtual_virtual_radiator_lounge',
                        'kitchen': 'switch.virtual_virtual_radiator_kitchen',
                        'bathroom': 'switch.virtual_virtual_radiator_bathroom',
                        'lounge_entrance': 'switch.virtual_virtual_radiator_lounge'}

# Link each radiator (or group of) to an output controring switch (often a relay controller)
# format Dictionary
#    key    radiator_name
#    value  output controling radiator switch
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
radiator_boost_mode = []
# initilisation of list to the required size
for i in range(len(RADIATOR_ACTUAL_SWITCH_DICT)):
    radiator_live_mode.append(0)
    radiator_requested_mode.append(0)
    radiator_boost_mode.append(0)

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
            'active_radiators_number':0,
            'power_saving_mode_steps': RADIATOR_MAX_ACTIVE,
            'radiator_requested_mode': radiator_live_mode,
            'radiator_boost_mode': radiator_live_mode,
            'radiator_live_mode': radiator_live_mode
        })

# !WARNING: state_trigger requires all input on the same line which then can be very long
@state_trigger("switch.virtual_virtual_radiator_lounge, switch.virtual_virtual_radiator_bedroom, switch.virtual_virtual_radiator_office, switch.virtual_virtual_radiator_tv, switch.virtual_virtual_radiator_kitchen, switch.virtual_virtual_radiator_bathroom")
# Wait (in s) to allow thermostat to switch all required virtual switches
@time_active(hold_off=1)
# Do not allow multiple run in parallel -> force a unique completion
def request_heater_change_mode(var_name, value):
    task.unique("request_heater_change_mode", kill_me=True)
    log.info(f"roundrobin.py: Radiator mode change triggered change by {var_name} new_value={value} (on:1 off: 0)")
    roundrobin_step()

@state_trigger(INPUT_POWER_SAVING_MODE_NAME)
def request_change_power_saving_mode():
    # input_number are returned as list
    log.info(f"roundrobin.py: Power Saving Mode change request->{input_power_saving_value()} -> {input_power_saving_value()[0]}")
    roundrobin_step()              
 
@time_trigger(TIME_STEP)
def request_roundrobinstep():
    log.debug(f"roundrobin.py: Timer roundrobin_step request")
    roundrobin_step()

@service
def Round_Robin_Boost_mode(radiator=None, state=None):
    global radiator_boost_mode
    log.info(f"roundrobin.py: Boost change mode  radiator={radiator} state={state}")
    # check validity of parameters
    if RADIATOR_LIST.count(radiator) and state in ('on','off'):
        if state=='on':
           radiator_boost_mode[RADIATOR_LIST.index(radiator)] = 1 
        else:
           radiator_boost_mode[RADIATOR_LIST.index(radiator)] = 0 
        roundrobin_step()
# Checking service availability for listed control device
log.debug(f"roundrobin.py: end roundrobin.py intialisation done. Now waiting for tiggers")
# -----------------------------------------

# Read the radiators requested status directly from the Thermostat controlled virtual switches
def get_radiator_status():
    global radiator_requested_mode
    # read status directly from virtual radiator state
    for radiator in RADIATOR_VIRTUAL_SWITCH_DICT:
        if state.get(RADIATOR_VIRTUAL_SWITCH_DICT[radiator]) == 'on':
            radiator_requested_mode[list(RADIATOR_VIRTUAL_SWITCH_DICT.keys()).index(radiator)] = 1
        else:
            radiator_requested_mode[list(RADIATOR_VIRTUAL_SWITCH_DICT.keys()).index(radiator)] = 0
        log.debug(f"roundrobin.py: read status virtual_radiator={list(RADIATOR_VIRTUAL_SWITCH_DICT.keys()).index(radiator)}-> {RADIATOR_VIRTUAL_SWITCH_DICT[radiator]}")
    log.debug(f"roundrobin.py: got_status radiator_requested_mode={radiator_requested_mode}")

def roundrobin_step():
    global power_saving_mode, round_robin_index,radiator_live_mode,radiator_requested_mode
    task.unique("roundrobin_step", kill_me=True)
    log.debug(f"roundrobin.py: Before round robin stepping")
    log.debug(f"roundrobin.py:     radiator_requested_mode = {radiator_requested_mode}")
    log.debug(f"roundrobin.py:     radiator_live_mode      = {radiator_live_mode}")
    # get latest power saving mode
    power_saving_mode=int(input_power_saving_value()[0])
    get_radiator_status()
    round_robin_index = int(pyscript.radiator_status.round_robin_index)
    heater_activation_count=0
    # starting with a clean list (all off) saving previous value
    for i in range(len(RADIATOR_LIST)):
        radiator_live_mode[i]=0
    # when house is empty, all heating remain forced to off
    if away_status() != 'on':
        # setting radiators in boost mode first
        for i in range(len(RADIATOR_LIST)):
            if radiator_boost_mode[(i+round_robin_index)%len(RADIATOR_LIST)] == 1:
                heater_activation_count += 1
                # when powersaving_mode is max we stop all heating whatever is requested
                if heater_activation_count > RADIATOR_MAX_ACTIVE[power_saving_mode]:
                    break
                radiator_live_mode[(i+round_robin_index)%len(RADIATOR_LIST)] = 1
        # we set other radiators second
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
        # we avoid redoing unrequired action on control relays and do nothin in test mode
        log.debug(f"roundrobin.py: about Switching actual radiator {RADIATOR_LIST[i]} index {i} actual mode {RADIATOR_ACTUAL_SWITCH_DICT[RADIATOR_LIST[i]]}")
        if radiator_live_mode[i] != RADIATOR_ACTUAL_SWITCH_DICT[RADIATOR_LIST[i]] and not TEST_MODE:
            # may need to let time for relay to settle (in second) before changing the next one.
            # task.sleep(1)
            if radiator_live_mode[i] == 0:
                log.debug(f"roundrobin.py: Switching actual radiator {RADIATOR_LIST[i]} index {i} 'off'")
                # service call seems more stable than state.set (may depend on target hardware use one or the other)
                #state.set(RADIATOR_ACTUAL_SWITCH_DICT[RADIATOR_LIST[i]], value='off')
                service.call('light','turn_off',blocking=True, limit=1,entity_id=RADIATOR_ACTUAL_SWITCH_DICT[RADIATOR_LIST[i]])
            if radiator_live_mode[i] == 1 :
                log.debug(f"roundrobin.py: Switching actual radiator {RADIATOR_LIST[i]} index {i} 'on'")
                #state.set(RADIATOR_ACTUAL_SWITCH_DICT[RADIATOR_LIST[i]], value='on')
                service.call('light','turn_on',blocking=True, limit=1,entity_id=RADIATOR_ACTUAL_SWITCH_DICT[RADIATOR_LIST[i]])
        
     # save new state for reuse(roundrobin_index)/info/tracking/debug
    log.info(f"roundrobin.py: End roundrobin stepping radiator_requested_mode = {radiator_requested_mode}")
    log.info(f"roundrobin.py:                         radiator_boost_mode     = {radiator_boost_mode}")
    log.info(f"roundrobin.py:                         radiator_live_mode      = {radiator_live_mode}")
    log.info(f"roundrobin.py:                         round_robin_index={round_robin_index}")
    log.info(f"roundrobin.py:                         power_saving_mode={power_saving_mode}->{RADIATOR_MAX_ACTIVE[power_saving_mode]} max")
    log.info(f"roundrobin.py:                         away_status      ={away_status()}")
    if TEST_MODE:
        log.info(f"roundrobin.py:                         WARNING TEST_MODE active NO actual radiator control")
    # count number of active radiator for reporting
    # a valuable helper for an external power_saving_mode estimation
    active_radiators_number=0
    for i in range(len(RADIATOR_LIST)):
        if radiator_live_mode[i] == 1:
            active_radiators_number+=1
    state.set(
            'pyscript.radiator_status',
            value='none',
            new_attributes={
                'test_mode': TEST_MODE,
                'away_status': away_status(),
                'power_saving_mode': power_saving_mode,
                'round_robin_index': round_robin_index,
                'active_radiators_number': active_radiators_number,
                'power_saving_mode_steps': RADIATOR_MAX_ACTIVE,
                'radiator_requested_mode': radiator_requested_mode,
                'radiator_boost_mode': radiator_boost_mode,
                'radiator_live_mode': radiator_live_mode
            })

