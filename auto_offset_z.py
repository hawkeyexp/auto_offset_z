# Perform an easy auto offset calibration with BLTouch or Probe and a pysical z endstop (cnc-style)
#
# Initially developed for use with BLTouch
#
# Copyright (C) 2022 Marc Hillesheim <marc.hillesheim@outlook.de>
#
# Version 0.0.1 / 25.01.2022
#
# This file may be distributed under the terms of the GNU GPLv3 license.

from . import probe

class AutoOffsetZCalibration:
    def __init__(self, config):
        self.printer = config.get_printer()
        x_pos_center, y_pos_center = config.getfloatlist("center_xy_position", count=2)
        x_pos_endstop, y_pos_endstop = config.getfloatlist("endstop_xy_position", count=2)
        self.center_x_pos, self.center_y_pos = x_pos_center, y_pos_center
        self.endstop_x_pos, self.endstop_y_pos = x_pos_endstop, y_pos_endstop
        self.z_hop = config.getfloat("z_hop", default=10.0)
        self.z_hop_speed = config.getfloat('z_hop_speed', 15., above=0.)
        zconfig = config.getsection('stepper_z')
        self.max_z = zconfig.getfloat('position_max', note_valid=False)
        self.endstop_pin = zconfig.get('endstop_pin')
        self.speed = config.getfloat('speed', 50.0, above=0.)
        self.offsetadjust = config.getfloat('offsetadjust', 0.0)
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode_move = self.printer.lookup_object('gcode_move')
        self.gcode.register_command("AUTO_OFFSET_Z", self.cmd_AUTO_OFFSET_Z, desc=self.cmd_AUTO_OFFSET_Z_help)

        # check if a bltouch is installed
        if config.has_section("bltouch"):
            bltouch = config.getsection('bltouch')
            self.x_offset = bltouch.getfloat('x_offset', note_valid=False)
            self.y_offset = bltouch.getfloat('y_offset', note_valid=False)
            # check if a possible valid offset is set for bltouch
            if ((self.x_offset == 0) and (self.y_offset == 0)):
                raise config.error("AutoOffsetZ: Check the x and y offset [bltouch] - it seems both are zero and the BLTouch can't be at the same position as the nozzle :-)")
            # check if bltouch is set as endstop
            if ('virtual_endstop' in self.endstop_pin):
                raise config.error("AutoOffsetZ: BLTouch can't be used as z endstop with this command - use a physical endstop instead.")

        # check if a probe is installed
        elif config.has_section("probe"):
            probe = config.getsection('probe')
            self.x_offset = probe.getfloat('x_offset', note_valid=False)
            self.y_offset = probe.getfloat('y_offset', note_valid=False)
            # check if a possible valid offset is set for probe
            if ((self.x_offset == 0) and (self.y_offset == 0)):
                raise config.error("AutoOffsetZ: Check the x and y offset from [probe] - it seems both are 0 and the Probe can't be at the same position as the nozzle :-)")
            # check if probe is set as endstop
            if ('virtual_endstop' in self.endstop_pin):
                raise config.error("AutoOffsetZ: Probe can't be used as z endstop - use a physical endstop instead.")
        else:
            raise config.error("AutoOffsetZ: No bltouch or probe in configured in your system - check your setup.")

        # check if qgl or ztilt is available
        if config.has_section("quad_gantry_level"):
            self.adjusttype = "qgl"
        elif config.has_section("z_tilt"):
            self.adjusttype = "ztilt"
        else:
            raise config.error("AutoOffsetZ: This can only be used if your config contains a section [quad_gantry_level] or [z_tilt].")

    def cmd_AUTO_OFFSET_Z(self, gcmd):
        # check if all axes are homed
        toolhead = self.printer.lookup_object('toolhead')
        curtime = self.printer.get_reactor().monotonic()
        kin_status = toolhead.get_kinematics().get_status(curtime)

        # debug output start #
        #gcmd.respond_raw("AutoOffsetZ (Homeing Result): %s" % (kin_status))
        # debug output end #

        if ('x' not in kin_status['homed_axes'] or
            'y' not in kin_status['homed_axes'] or
            'z' not in kin_status['homed_axes']):
            raise gcmd.error("You must home X, Y and Z axes first")

        if self.adjusttype == "qgl":
            # debug output start #
            #gcmd.respond_raw("AutoOffsetZ (Alignment Type): %s" % (self.adjusttype))
            # debug output end #

            # check if qgl has applied
            alignment_status = self.printer.lookup_object('quad_gantry_level').get_status(gcmd)
        elif self.adjusttype == "ztilt":
            # debug output start #
            #gcmd.respond_raw("AutoOffsetZ (Alignment Type): %s" % (self.adjusttype))
            # debug output end #

            # check if ztilt has applied
            alignment_status = self.printer.lookup_object('z_tilt').get_status(gcmd)
        else:
            raise config.error("AutoOffsetZ: Your printer has no config for [quad_gantry_level] or [z_tilt] which is needed to work correctly.")

        # debug output start #
        #gcmd.respond_raw("AutoOffsetZ (Alignment Result): %s" % (alignment_status))
        # debug output end #

        if (alignment_status['applied'] != 1):
            if self.adjusttype == "qgl":
                raise gcmd.error("AutoOffsetZ: You have to do a quad gantry level first")
            elif self.adjusttype == "ztilt":
                raise gcmd.error("AutoOffsetZ: You have to do a z tilt first")
            else:
                raise config.error("AutoOffsetZ: Your printer has no config section for [quad_gantry_level] or [z_tilt] which is required for auto_offset_z to work correctly.")

        # reset z offset to zero
        gcmd_offset = self.gcode.create_gcode_command("SET_GCODE_OFFSET",
                                                      "SET_GCODE_OFFSET",
                                                      {'Z': 0})
        self.gcode_move.cmd_SET_GCODE_OFFSET(gcmd_offset)

        # Move with probe or bltouch to endstop XY position and test surface z position
        gcmd.respond_info("AutoOffsetZ: Probing endstop ...")
        toolhead.manual_move([self.endstop_x_pos - self.x_offset, self.endstop_y_pos - self.y_offset], self.speed)
        zendstop = self.printer.lookup_object('probe').run_probe(gcmd)
        # Perform Z Hop
        if self.z_hop:
            toolhead.manual_move([None, None, self.z_hop], self.z_hop_speed)

        # Move with probe or bltouch to center XY position and test surface z position
        gcmd.respond_info("AutoOffsetZ: Probing bed ...")
        toolhead.manual_move([self.center_x_pos - self.x_offset, self.center_y_pos - self.y_offset], self.speed)
        zbed = self.printer.lookup_object('probe').run_probe(gcmd)
        # Perform Z Hop
        if self.z_hop:
            toolhead.manual_move([None, None, self.z_hop], self.z_hop_speed)

        # calcualtion offset
        endstopswitch = 0.5
        diffbedendstop = zendstop[2] - zbed[2]
        offset = (0 - diffbedendstop  + endstopswitch) + self.offsetadjust

        gcmd.respond_info("AutoOffsetZ:\nBed: %.6f\nEndstop: %.6f\nDiff: %.6f\nManual Adjust: %.6f\nTotal Calculated Offset: %.6f" % (zbed[2],zendstop[2],diffbedendstop,self.offsetadjust,offset,))
        self.set_offset(offset)

    cmd_AUTO_OFFSET_Z_help = "Test endstop and bed surface to calcualte g-code offset for Z"

    def set_offset(self, offset):
        # reset pssible existing offset to zero
        gcmd_offset = self.gcode.create_gcode_command("SET_GCODE_OFFSET",
                                                      "SET_GCODE_OFFSET",
                                                      {'Z': 0})
        self.gcode_move.cmd_SET_GCODE_OFFSET(gcmd_offset)
        # set new offset
        gcmd_offset = self.gcode.create_gcode_command("SET_GCODE_OFFSET",
                                                      "SET_GCODE_OFFSET",
                                                      {'Z': offset})
        self.gcode_move.cmd_SET_GCODE_OFFSET(gcmd_offset)

def load_config(config):
    return AutoOffsetZCalibration(config)
