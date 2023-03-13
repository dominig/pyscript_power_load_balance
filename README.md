# pyscript_power_load_balance
This is a python script for Home Automation enabling a power dispatch via power balancing\
The simple idea is to activate and deactivate radiators automatically\
Keeping the heating in all the house but not all at the time.\
The number of activate radiators is defined dynamicaly.

Configuration is simple but done directly in the code. There is NO UI.\
You will need to install pyscript before using it\
  https://hacs-pyscript.readthedocs.io/en/latest/reference.html#state-variable-functions

The base principle is that a PowerSavingMode number is set via an automation\
You can use any input number as a target. My example uses the house actual consumed power in Watts and a numeric helper\
You would be better at reading the power used by other equipement than the total value. \
What you really need to estimate is the remaining energy available for your heating system.\
I designed it for controling my heating but you could use as well starting and stopping of heavy equipements or time of the day.\
The calculation of available power assement automation is not part of the script but I provide my use case as an example.

The PowerSavingMode is monitored and any change will trigger a reduction or increase of usable ressources.\
My loads (radiators) are all of identical value.\
**It's important to realise that regular switching on/off will be done on each ressource while you play with high power.** 

## ---------- DESCRIPTION ----------------
### It monitors \
   - a list of virtual toggle switches (see HA Toogle helpers or HACS.virtual swiches)\
     defined in the list RADIATOR_VIRTUAL_SWITCH_INV_DICT\
       **AND REPEATED** in the @triggger decorator
     re-listed in TRIGGERs (on and off)\
     that can be controlled manually or more commonly automatically via thermostats
   - a power saving status mode defined as a numeric helper\
     see INPUT_POWER_SAVING_MODE\
         WARNING: (defined twice as _NAME and _VALUE)
   - a time pattern under the format of a unix cron command\
     see TIME_STEP
   - an AWAY_MODE for forcing all heaters off when abscent or during summer\
     Note: if you are using radiator control wire, most likely the off state requires a relay activation\
           You may want to avoid that useless wear during summer by adding an extra trip in your home electric pannel.
It controls on/off radiator status\
   **Note**: 'off' can be a real electric 'off' of a 'no_freeze' mode depending of how the control mode is configured/wired\
         Control harware can trigger high power cut rapidely and configuration must be electricly safe\
         My STRONG advise is to control the radiator via the control wire (or wireless)\
         rather than by directly swicthing the radiator power feed.\
   - a list of switches controling the actual radiators\
     see RADIATOR_ACTUAL_SWITCH_DICT\
   - reports current status in a state_variable+attributes \
     see pyscript.radiator_status

At each time step, power mode or radiator configuration change request it will run a round robin and limit\
the number of active radiators to respect the max number of radiator configured via the power mode.\
There is no concept of priority but a radiator can be listed twice to increase number of heating slots.\
If some rooms have multiple radiators, it might be a good idea to seprarate them in the radiator list to smooth the heating.\
The order RADIATOR_VIRTUAL_SWITCH_INV_DICT and RADIATOR_ACTUAL_SWITCH_DICT is not important but each radiator must have a unique entry

Most of electric radiator have an embedded thermostat. That later is often not very accurate due to it position (too close of the heat source). You need to remember that even if you force a radiator in 'confort mode', it will run under it's own logic and you cannot control when it will actually draw power. Trick is to put the limit high enough to let HA control the over all system while reasonable to avoid over heat in some room.


## ---------- CONFIGURATION ---------------
Configuration is specific to each house and MUST be aligned with reality\
#
All CONSTANT must be declared in respect of Python3 syntax.\
             Errors will only be reported in home-assistant.log\
#
## Detailled configuration description is in the script code
If a Thermostat need to control multiple radiator you just need to list the \
virtual switch pointed by the thermotat and monitored by roundrobin.py script several time
using one entry for each output controlled switch.\
You could use that configuration to dispatch power in all the house\
while using only one Thermostat (or a virtual switch without any external thermostat)\

In HA: You will need to create \
  - one virtual switch per thermostat.\
  - one input number for the power saving mode
  - one virtual switch for the away mode

## Installation
You need to install pyscript.\
I use HACS.virtual but default HA helpers can also provide the virtual switches\
Simply copy the file roundrobin.py in the directory config/pyscript\
First time required HA restart.\
Later modification are activated automatically when file is saved or touched.\
Debug in via the logger.\
Typo and indentiation errors when provisioning configuration are easily done.\
