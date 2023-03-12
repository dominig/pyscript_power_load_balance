# pyscript_power_load_balance
This is a python script for Home Automation enabling a power dispatch via power balancing\
The simple idea is to activate and deactivate radiators automatically\
Keeping the heating in all the house but not all at the time.\
The number of activate radiators is defined dynamicaly.\

Configuration is simple but done directly in the code. There is NO UI.\
You will need to install pyscript before using it\
  https://hacs-pyscript.readthedocs.io/en/latest/reference.html#state-variable-functions

The base principle is that a PowerSavingMode number is set an automation\
You can use any input number for doing do. My example uses the house actual consumed power in Watts and a numeric helper\
You could use as well starting and stopping of heavy equipements or time of the day.\
That automation is not part of the script but I provide my use case as example.

The PowerSavingMode is monitored and any change will trigger a reduction or increase of usable ressources.\
My ressources are all of identical value.\
**It's important to realase that regular switch on/off will be done on each ressource.** 

## ---------- DESCRIPTION ----------------
### It monitors \
   - a list of virtual toggle switches (see HA helpers)\
     defined in the list RADIATOR_VIRTUAL_SWITCH_INV_DICT\
     re-listed in TRIGGERs (on and off)\
     that can be controlled manually or more commonly automatically via thermostats\
   - a power saving status mode defined as a numeric helper\
     see INPUT_POWER_SAVING_MODE\
         WARNING: (defined twice as _NAME and _VALUE)\
   - a time pattern under the format of a unix cron command\
     see TIME_STEP\
   - an AWAY_MODE for forcing all heaters off when abscent or during summer\
     Note: if you are using radiator control wire, most likely the off state requires relay activation\
           You may want to avoid that useless wear during summer by adding an extra trip in your home electric pannel.\
It controls on/off radiator status\
   Note: off can be a real off of no freeze mode depending of how control mode is configured/wired\
         control harware can trigger high power cut rapidely and configuration must be electricly safe\
         My STRONG advise is to control the radiator via the control wire (or wireless)\
         rather than by directly swicthing the radiator power feed.\
   - a list of switches controling the actual radiators\
     see RADIATOR_ACTUAL_SWITCH_DICT\
   - reports current status in a state_variable+attributes \
     see pyscript.radiator_status\

At each time step, power mode or radiator configuration change request it will run a round robin and limit\
the number of active radiators to respect the max number of radiator configured via the power mode.\
There is no concept of priority but a radiator can be listed twice to increase number of heating slots.\
If some rooms have multiple radiators, it might be a good idea to seprarate them in the radiator list to smooth the heating.\
The order RADIATOR_VIRTUAL_SWITCH_INV_DICT and RADIATOR_ACTUAL_SWITCH_DICT is not important but each radiator must have a unique entry\


## ---------- CONFIGURATION ---------------
Configuration is specific to each house and MUST be aligned with reality\
#
All CONSTANT must be declared in respect of Python3 syntax.\
             Errors will only be reported in home-assistant.log\
#
TEST_MODE = True the actual control the radiator is deactivated\
but reports and log remains as normal\
for normal operation TEST_MODE = False\
TEST_MODE = False\
radiator list by name\
Varing order allows to spread the heat around the house\
RADIATOR_LIST = [ 'tv', 'office', 'bedroom','lounge_window', 'kitchen' , 'bathroom' ,  'lounge_entrance' ]\
#
max activate radiator per power saving mode (no, medium, hight,max)\
Array representing the max number of active radiator per mode\
Note: the first entry reprensents max number of radiator supported \
      when no power saving mode is requested\
      that number must be <= to the number of radiator declated in RADIATOR_LIST\
max number of level is 10.\
RADIATOR_MAX_ACTIVE = [5,3,1,0]\
Power saving mode variable (a helper type input_number)\
UGLY: To avoid importing extra modules it's defined twice with different types\
the second definition is embedded in a function called by trigger\
INPUT_POWER_SAVING_MODE_NAME is a string ('numeric_helper_name')\
INPUT_POWER_SAVING_MODE_VALUE is an array( numeric_helper_name)\
INPUT_POWER_SAVING_MODE_NAME  ='input_number.powsersavingmode'\
def input_power_saving_value():\
    INPUT_POWER_SAVING_MODE_VALUE = input_number.powsersavingmode\
    return (INPUT_POWER_SAVING_MODE_VALUE)\
Away status defined by a virtual toggle\
     change activated at the next time_step (not by trigger)\
def away_status():\
    AWAY_STATUS=str(input_boolean.away_status)\
    log.debug(f"AWAY_STATUS={AWAY_STATUS}, input_boolean.away_status")\
    return (AWAY_STATUS)\
Step Round Robin every xx in cron format\
  Note: if your radiator control is done via electromagnetic relays\
        don't switch them to often to limit rapid wear (and noise)\
TIME_STEP = 'cron(* * * * */2)'\
link radiator_name / switch name\
WARNING: radiator virtual swicthes MUST also be (re)listed in the code : see TRIGGER\
When a thermostat control several radiators key must be repeated for each controlled radiator\
format Dictionary \
   key   virtual switch controlled by the thermostat\
   value the radiator_name\
RADIATOR_VIRTUAL_SWITCH_INV_DICT = {\
                        'input_boolean.virtual_heat_tv': 'tv',\
                        'input_boolean.virtual_heat_office': 'office',\
                        'input_boolean.virtual_heat_bedroom':'bedroom',\
                        'light.heating_lounge_group': 'lounge_window',\
                        'input_boolean.virtual_heat_kitchen': 'kitchen',\
                        'input_boolean.virtual_heat_bathroom': 'bathroom',\
                        'light.heating_lounge_group': 'lounge_entrance'}\
format Dictionary\
   key    radiator_name\
   value  switch controling the radiator\
RADIATOR_ACTUAL_SWITCH_DICT = {\
                        'tv': 'light.relay2_light_5',\
                        'office': 'light.tz3000_u3oupgdy_ts0004_light',\
                        'bedroom': 'light.tz3000_u3oupgdy_ts0004_light_2',\
                        'lounge_window': 'light.relay2_light_6',\
                        'kitchen': 'light.tz3000_u3oupgdy_ts0004_light_4',\
                        'bathroom': 'light.tz3000_u3oupgdy_ts0004_light_3',\
                        'lounge_entrance': 'light.relay2_light_7'}`\
## -------- END CONFIGURATION ------------ --
