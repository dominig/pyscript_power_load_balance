# pyscript_power_load_balance
This is a set of two python scripts for Home Automation enabling a power dispatch via power balancing\
The simple idea is to activate and deactivate radiators automatically\
Keeping the heating in all the house but not all at the time.\
The number of activate radiators is defined dynamicaly.

A demo video can be viewed here:\
 https://vimeo.com/dominig/homeassistant-power-load-balancing \

Configuration is simple but done directly in the code. There is NO UI.\
You will need to install pyscript before using it\
  https://hacs-pyscript.readthedocs.io/en/latest/reference.html#state-variable-functions

The base principle of the load balancing is that a PowerSavingMode number is set via an automation\
You can use any input number as a target. My example uses the house actual consumed power in Watts and a numeric helper\
You would be better at reading the power used by other equipement than the total value. \
What you really need to estimate is the remaining energy available for your heating system.\
I designed it for controling my heating but you could use as well starting and stopping of heavy equipements or time of the day.\
The calculation of available power assement automation is not part of the round robin script but I provide a simple automation use case as an example in the config directory.

The script powersavemode.py implement a more sofisticated management of the power saving status.\
It uses of few information reported by roundrobin.py to simplify the configuration. \

The PowerSavingMode is monitored and any change will trigger a reduction or increase of usable ressources.\
My loads (radiators) are all of identical value.\
**It's important to realise that regular switching on/off will be done on each ressource while you play with high power.**

# ---------- DESCRIPTION  roundrobin.py----------------
### It monitors
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

## ----- Behaviour -----------
As home hardware is not a reliable and as quick as industrial products, you need to add some delays.\
Some are commented out waiting to be activated.\
When several virtual switches are going on or off at a short interval, some can/will be ignored until the next roudrbin step.
It's a normal side effet of running the trigger task as unique to protect relay controlling middleware from crashes.

### Power saving mode change
The trigger is (and must be) instant but real corrective actions may still take a bit of time.\
Must be triggered early enough and executed fast enough to avoid a general trip blackout.

### Radiator Trigger
A single virtual radiator trigger change will happen almost instantaneously.\
Multiple change request will only pickup one trigger, the other ones will be executed at the next roundrobin step (a few minutes?)\
While this is no issue with a real heating use case, it can be looking strange when debugging.\
Running multiple triggers in parallel can crash your hardware (at least it does with mine). Hence the **task.unique** command in the code.

### Away mode
It will only be activated or deactivated at the next round robin step. May take some time (a few minutes?).

### Boost mode
Boost mode will force a radiator 'on' what ever says the controling thermostat.\
Like away mode, it is activated at the next round robin step.\
I use it for my towel dryer in my bathroom.\
Boost mode is still affected by round robin stepping, power saving mode and away mode and the local thermostat on the radiator itself.\
There is no time out on boost mode. **Your duty to take care of switching it off**.

### Real hardware control issue
I had statibility issues with the use of **state.set** to control my relays. Relays would set for about 40s and then unset. 
Most likely it's a fault in my relay firmware, so I changed my code and used **service.call**\
The 2 old calls are still commented out in the script source code would you need it.\
I use as little time delay that I can. It's a compromise to find between your hardware performance\
and the need to reduce power quickly enough to avoid a blackout when power saving mode changes.

### Single phase and 3phases wiring support
My script has been written for a single phase installation.\
In a multiphases installation, you would need to run 3 independant scripts. One per phase\
Just copy, change the file name, configure one script per phase.\
**Don't forget** to give a different name to the reporting state variable pyscript.radiator_status (one name per script).

# ---------- DESCRIPTION powersavemode.py ----------------

 This program estimates the remaining available power that can be used by the heating system.
 
 It monitors
    - The various meeter available in the house\
      GENERAL_METER  define the unique overall installation meeter\
      EXTRA_METERS   Optional list of meeter attached to large non heater item\
                     covering all the non heating consumtion.
 It controls a power_saving_mode variable\
    The power_saving_mode is a HA numeric variable that is monitored as entry\
    by load power balancing script roundrobin.py  \
 Caculation can be done with Ampere (A) or Watts (W) or kW\
 You just need to be consistant and always used the same unit.

 ## Power Saving Mode management
Different methods can be used to estimate the available power, depending how many meters you have and where they are:
  - Individual mode 'I'.\
    heating_available_A = max_available_A - non_heating_use_A\
    most accurate method as independant from embedded radiator thermostats side effet

  - Global mode 'G'\
    heating_available_A = max_available_A - global_meter_A + single_radiator_power_A\*active_radiators_number\/thermostat_factor\
    Requires only 1 global meter and works fine enough in most cases.

State variables are reported by roundrobin.py and powersavingmode.py in the state variables pyscript.roundrobin.py and pyscript.powersavingmode.py\

Depending of electric provider trip you may have up to 1 may be 2 seconds to react before blacking out.\
As most radiators are equipped with an internal thermostat, your measurements might be different than your calculations. Hence a thermostat_factor.\
You still need to assume the worse case, or a blackout will most likely happen rather soon than later.\
**Note:** Announced power on radiator documentation should not be fully trusted. Take it as an indication. Often they can take up to 15 to 20% more than indicated. This is particularly true in Europe where the voltage is assummed to be 220V but is often closer to 240V.
Nothing is better than a measurement with a Clamp-on Amp Meeter.

# -------------- LICENSE ---------------
Apache V2   http://www.apache.org/licenses/

# ------------- CONSTRAINT -------------
 Trip are fast and your code must react faster than the trip\
 You rarelay have more than 1 or 2 seconds to correct power use before backout.\
 Meters reporting value less than once a second for such use case are useless.\

# ---------- CONFIGURATION ---------------
Configuration is specific to each house and MUST be aligned with reality\
All CONSTANT must be declared in respect of Python3 syntax.\
             Errors will only be reported in home-assistant.log\
#
## Detailled configuration description is in each script code
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
Simply copy the file roundrobin.py and/or powersavemode.py in the directory config/pyscript\
First time requires HA cold restart.\
Later modification are activated automatically when file is saved or touched.\
Debug in via the logger.\
Typo and indentiation errors when provisioning configuration are easily done.\
config/home-assistant.log will help you to spot them if any.

You will need to create virtual switches.\
I used HACS.Virtual switches but HA group Toogle also works.

Enjoy\
Dominig
