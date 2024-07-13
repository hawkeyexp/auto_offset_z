# Perform an easy auto offset calibration with BLTouch or Probe and a pysical z endstop (cnc-style)
#
# Initially developed for use with BLTouch
#
# Copyright (C) 2022 Marc Hillesheim <marc.hillesheim@outlook.de>
#
# Version 0.0.6 / 13.07.2024
#
# This file may be distributed under the terms of the GNU GPLv3 license.

from . import probe
import math

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
        self.ignore_alignment = config.getboolean('ignore_alignment', False)
        self.ignore_endstopoffset = config.getboolean('ignore_endstopoffset', False)
        self.endstop_pin = zconfig.get('endstop_pin')
        self.speed = config.getfloat('speed', 50.0, above=0.)
        self.offsetadjust = config.getfloat('offsetadjust', 0)
        self.internalendstopoffset = config.getfloat('internalendstopoffset', 0.5)
        self.offset_min = config.getfloat('offset_min', -1)
        self.offset_max = config.getfloat('offset_max', 1)
        self.endstop_min = config.getfloat('endstop_min', 0)
        self.endstop_max = config.getfloat('endstop_max', 0)
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
        elif self.ignore_alignment == 1:
            self.adjusttype = "ignore"
        else:
            raise config.error("AutoOffsetZ: This can only be used if your config contains a section [quad_gantry_level] or [z_tilt].")

    # custom round operation based mathematically instead of python default cutting off
    def rounding(self,n, decimals=0):
        expoN = n * 10 ** decimals
        if abs(expoN) - abs(math.floor(expoN)) < 0.5:
            return math.floor(expoN) / 10 ** decimals
        return math.ceil(expoN) / 10 ** decimals

    def cmd_AUTO_OFFSET_Z(self, gcmd):
        # check if all axes are homed
        toolhead = self.printer.lookup_object('toolhead')
        curtime = self.printer.get_reactor().monotonic()
        kin_status = toolhead.get_kinematics().get_status(curtime)
        paramoffsetadjust = gcmd.get_float('OFFSETADJUST', default=0)
        probe_obj = self.printer.lookup_object('probe', None)

        # debug output start #
        # gcmd.respond_raw("AutoOffsetZ (Homeing Result): %s" % (kin_status))
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
            if alignment_status['applied'] != 1:
                raise gcmd.error("AutoOffsetZ: You have to do a quad gantry level first")

        elif self.adjusttype == "ztilt":
            # debug output start #
            #gcmd.respond_raw("AutoOffsetZ (Alignment Type): %s" % (self.adjusttype))
            # debug output end #

            # check if ztilt has applied
            alignment_status = self.printer.lookup_object('z_tilt').get_status(gcmd)
            if alignment_status['applied'] != 1:
                raise gcmd.error("AutoOffsetZ: You have to do a z tilt first")

        elif self.adjusttype == "ignore":
            gcmd.respond_info("AutoOffsetZ: Ignoring alignment as you requested by config ...")
        else:
            raise config.error("AutoOffsetZ: Your printer has no config for [quad_gantry_level] or [z_tilt] which is needed to work correctly.")

        # debug output start #
        #gcmd.respond_raw("AutoOffsetZ (Alignment Result): %s" % (alignment_status))
        # debug output end #

        gcmd_offset = self.gcode.create_gcode_command("SET_GCODE_OFFSET",
                                                      "SET_GCODE_OFFSET",
                                                      {'Z': 0})
        self.gcode_move.cmd_SET_GCODE_OFFSET(gcmd_offset)

        # Move with probe or bltouch to endstop XY position and test surface z position
        gcmd.respond_info("AutoOffsetZ: Probing endstop ...")
        toolhead.manual_move([self.endstop_x_pos - self.x_offset, self.endstop_y_pos - self.y_offset], self.speed)

        probe_session = probe_obj.start_probe_session(gcmd)
        probe_session.run_probe(gcmd)
        zendstop = probe_session.pull_probed_results()[0]
        probe_session.end_probe_session()

        # Perform Z Hop
        if self.z_hop:
            toolhead.manual_move([None, None, self.z_hop], self.z_hop_speed)

        # Move with probe or bltouch to center XY position and test surface z position
        gcmd.respond_info("AutoOffsetZ: Probing bed ...")
        toolhead.manual_move([self.center_x_pos - self.x_offset, self.center_y_pos - self.y_offset], self.speed)

        probe_session = probe_obj.start_probe_session(gcmd)
        probe_session.run_probe(gcmd)
        zbed = probe_session.pull_probed_results()[0]
        probe_session.end_probe_session()

        # Perform Z Hop
        if self.z_hop:
            toolhead.manual_move([None, None, self.z_hop], self.z_hop_speed)

        # calcualtion offset
        if self.ignore_endstopoffset == 1:
            self.internalendstopoffset = 0
            gcmd.respond_info("AutoOffsetZ: Igoring internal endstop offset as you requested by config ...")

        diffbedendstop = zendstop[2] - zbed[2]
        if paramoffsetadjust != 0:
            offset = self.rounding((0 - diffbedendstop  + self.internalendstopoffset) + paramoffsetadjust,3)
            gcmd.respond_info("AutoOffsetZ:\nBed: %.3f\nEndstop: %.3f\nDiff: %.3f\nParam Manual Adjust: %.3f\nTotal Calculated Offset: %.3f" % (zbed[2],zendstop[2],diffbedendstop,paramoffsetadjust,offset,))
        else:
            offset = self.rounding((0 - diffbedendstop  + self.internalendstopoffset) + self.offsetadjust,3)
            gcmd.respond_info("AutoOffsetZ:\nBed: %.3f\nEndstop: %.3f\nDiff: %.3f\nConfig Manual Adjust: %.3f\nTotal Calculated Offset: %.3f" % (zbed[2],zendstop[2],diffbedendstop,self.offsetadjust,offset,))

        # failsave
        if offset < self.offset_min or offset > self.offset_max:
            raise gcmd.error("AutoOffsetZ: Your calculated offset is out of config limits! (Min: %.3f mm | Max: %.3f mm) - abort..." % (self.offset_min,self.offset_max))

        if self.endstop_min != 0 and zendstop[2] < self.endstop_min:
            raise gcmd.error("AutoOffsetZ: Your endstop value is out of config limits! (Min: %.3f mm | Meassured: %.3f mm) - abort..." % (self.endstop_min,zendstop[2]))

        if self.endstop_max != 0 and zendstop[2] > self.endstop_max:
            raise gcmd.error("AutoOffsetZ: Your endstop value is out of config limits! (Max: %.3f mm | Meassured: %.3f mm) - abort..." % (self.endstop_max,zendstop[2]))

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
