## This is a Klipper plugin for an auto calibration Z offset with a BLTouch (or possible inductive probe - check hints first!)

## Why:<br>

I was inspired to make this possible since i build my Voron V2.4 and wanted the ability to change my print surfaces without
recalibrate my z offset for every surface and possible temp cause i'm also printing more than abs and didn't want to switch
to a klicky probe for example :-) (yes - the way how the klicky probe handles the z offset is the same idea behind)

## Requirements:<br>

1) Physical Z-Endstop - it is our reference point and is always Z 0.0 for calculations.
2) BLTouch as probe - the sensor to check the distance between endstop and bed to calc the offset
3) QUAD_GANTRY_LEVEL or Z_TILT used (the plugin checks if qgl or z-tilt is applied to ensure gantry and bed are parallel for correct values)
4) Ensure you set you x and y offset correct cause the plugin usses this offsets to move the bltouch over the endstop pin!

## How it works:<br>

The bltouch will probe two points - top of endstop and surface of your bed to messure the distance. Now we have one problem:
the nozzle triggers the endstop the bltouch can only touch the top surface - to ensure a correct offset the plugin includes a move distance
of 0.5mm (spec value from omron switches used in voron builts) which is the way the microsowitch in the endstop needs to trigger BUT:
ususally a bit more than 0.5mm is needed to trigger correctly (~0.1x till ~0.2x in most cases depending on the used microswitch).
This last bit can be set manually during a print probe by adjusting with babysteps until offset is correct and adding this to the 
config section of the plugin.
<pre><code>

                                                    | |
                                      Nozzle        | |  BLTouch
                                      |_   _|        -
                                        \_/               

Bed                                      _ 
--------------------------------------- | | Endstop Pin
</code></pre>

## Configuration for klipper:

<pre><code>
[auto_offset_z]
center_xy_position:175,175      # Center of bed for example
endstop_xy_position:233.5,358   # Physical endstop nozzle over pin
speed: 100                      # X/Y travel speed between the two points
z_hop: 10                       # Lift nozzle to this value after probing and for move
z_hop_speed: 20                 # Hop speed of probe
offsetadjust: 0.0               # Manual offset correction option - start with zero and optimize during print with babysteps
                                  1) If you need to lower the nozzle from -0.71 to -0.92 for example your value is -0.21.
                                  2) If you need to move more away from bed add a positive value.
</code></pre>
## Installation:

Login to your pi by ssh. Clone the repo to your homefolder with this command:

<pre><code>
git clone https://github.com/hawkeyexp/auto_offset_z.git<br>
cd ~/auto_offset_z<br>
./instal.sh<br>
</code></pre>

For further updates you can add it to moonraker's updated manager:

<pre><code>
[update_manager auto_offset_z]
type: git_repo
path: ~/auto_offset_z
origin: https://github.com/hawkeyexp/auto_offset_z.git
install_script: install.sh
</code></pre>

## Hints for use with an inductive probe:

in general an inductive probe should also work this way if it is able to detect the endstop pin but it is not tested and you have to
ensure the probe is really detecting the endstop pin and not the bed surface which is possible really close to the pin.

## Last words:

I'm not a software developer, only a guy which is playing arround to solve his problems or needs :-)
The code - i'm really sure - can be improved but it is running without problems for me now since some weeks.
If you wan't to give it a try have fun but note: if something is going wrong i'm not responsible for it!
