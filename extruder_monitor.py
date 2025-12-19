import logging
import threading
import time
from collections import deque


class ExtruderMonitor:
    """Monitor extruder load and accept simple lookahead segments.

    This module provides a small lookahead buffer that can be fed with
    upcoming extrusion segments (E delta in mm and duration in seconds).
    It exposes G-code commands to add/clear segments and to query the
    predicted extrusion rate and an estimated load based on current SG.
    """

    def __init__(self, config):
        self.printer = config.get_printer()
        config.get("stepper", "extruder")
        self.driver_name = config.get("driver_name", "tmc2209 extruder")
        self.printer.register_event_handler("klippy:connect", self.handle_connect)

        # lookahead buffer and bookkeeping
        self._lookahead_lock = threading.Lock()
        self._lookahead = deque()  # entries are (e_delta_mm, duration_s, timestamp)

        # keep a tiny history of recent extrusion rates (mm/s) to allow basic
        # normalization when estimating future load
        self._recent_rates = deque(maxlen=20)
        # state for live parsing of incoming G-code
        self._gcode_pos = {'X': None, 'Y': None, 'Z': None}
        self._gcode_last_e = None
        self._gcode_last_f = None

    def handle_connect(self):
        try:
            self.tmc = self.printer.lookup_object(self.driver_name)
        except Exception as e:
            raise self.printer.config_error(f"ExtruderMonitor: Driver '{self.driver_name}' not found.")

        gcode = self.printer.lookup_object('gcode')
        gcode.register_command("GET_EXTRUDER_LOAD", self.cmd_GET_EXTRUDER_LOAD,
                               desc="Get current extruder load")
        gcode.register_command("SET_LOOKAHEAD", self.cmd_SET_LOOKAHEAD,
                               desc="Add upcoming extrusion segment: SET_LOOKAHEAD E=<mm> D=<s> or SET_LOOKAHEAD CLEAR")
        gcode.register_command("GET_PREDICTED_LOAD", self.cmd_GET_PREDICTED_LOAD,
                               desc="Get predicted extrusion rate and estimated load using lookahead")

        # Attempt to attach a live G-code listener. Klipper exposes different
        # event registration APIs across versions; try a few common ones and
        # fail gracefully if not available.
        hook_installed = False
        try:
            # preferred: gcode.register_event_handler(event_name, callback)
            if hasattr(gcode, 'register_event_handler'):
                try:
                    gcode.register_event_handler('gcode:received', self._on_gcode_event)
                    hook_installed = True
                except Exception:
                    # try without namespace
                    try:
                        gcode.register_event_handler('received', self._on_gcode_event)
                        hook_installed = True
                    except Exception:
                        pass

            # alternate: printer-level event
            if not hook_installed and hasattr(self.printer, 'register_event_handler'):
                try:
                    self.printer.register_event_handler('gcode:received', self._on_gcode_event)
                    hook_installed = True
                except Exception:
                    pass
        except Exception:
            hook_installed = False

        if not hook_installed:
            logging.getLogger('ExtruderMonitor').info('Live G-code lookahead hook not installed (API unavailable).')
        else:
            logging.getLogger('ExtruderMonitor').info('Live G-code lookahead hook installed.')


    # Public lookahead API (can be called from other modules)
    def add_lookahead_segment(self, e_delta_mm, duration_s):
        if duration_s <= 0:
            return
        with self._lookahead_lock:
            self._lookahead.append((float(e_delta_mm), float(duration_s), time.time()))

    def clear_lookahead(self):
        with self._lookahead_lock:
            self._lookahead.clear()

    def _on_gcode_event(self, *args, **kwargs):
        """Try to extract raw G-code line from event and parse G0/G1 moves.

        The event API varies; we defensively look through args/kwargs for
        something resembling the raw command string.
        """
        raw = None
        # Look in positional args
        for a in args:
            if isinstance(a, str):
                raw = a
                break
            # some klippy objects may provide .command or .gcode
            if hasattr(a, 'command'):
                try:
                    raw = str(a.command)
                    break
                except Exception:
                    pass
            if hasattr(a, 'gcode'):
                try:
                    raw = str(a.gcode)
                    break
                except Exception:
                    pass

        # Look in kwargs
        if raw is None:
            for k, v in kwargs.items():
                if isinstance(v, str):
                    raw = v
                    break
                if hasattr(v, 'command'):
                    try:
                        raw = str(v.command)
                        break
                    except Exception:
                        pass

        if not raw:
            return

        line = raw.strip()
        if not line:
            return
        up = line.upper()
        if not (up.startswith('G0') or up.startswith('G1')):
            return

        # parse parameters (simple regex)
        import re
        param_re = re.compile(r'([A-Za-z])([-+]?[0-9]*\.?[0-9]+)')
        params = {}
        for m in param_re.finditer(line):
            params[m.group(1).upper()] = float(m.group(2))

        cur_e = params.get('E', None)
        cur_f = params.get('F', None)

        # compute Euclidean distance if coordinates available
        dist = 0.0
        coords = {}
        for axis in ('X', 'Y', 'Z'):
            coords[axis] = params.get(axis, self._gcode_pos.get(axis))

        if coords['X'] is not None and coords['Y'] is not None and coords['Z'] is not None:
            try:
                dx = coords['X'] - (self._gcode_pos['X'] if self._gcode_pos['X'] is not None else coords['X'])
                dy = coords['Y'] - (self._gcode_pos['Y'] if self._gcode_pos['Y'] is not None else coords['Y'])
                dz = coords['Z'] - (self._gcode_pos['Z'] if self._gcode_pos['Z'] is not None else coords['Z'])
                dist = (dx*dx + dy*dy + dz*dz) ** 0.5
            except Exception:
                dist = 0.0

        # if extrusion present, compute delta
        if cur_e is not None:
            if self._gcode_last_e is None:
                delta_e = cur_e
            else:
                delta_e = cur_e - self._gcode_last_e

            # estimate duration
            duration = None
            feed = cur_f if cur_f is not None else self._gcode_last_f
            if feed and dist > 0.0:
                try:
                    duration = dist * 60.0 / float(feed)
                except Exception:
                    duration = None
            if duration is None:
                duration = max(0.001, abs(delta_e) / 1.0)

            if delta_e > 0:
                try:
                    self.add_lookahead_segment(delta_e, duration)
                    # record recent rate
                    rate = abs(delta_e) / max(1e-6, float(duration))
                    try:
                        self._recent_rates.append(rate)
                    except Exception:
                        pass
                except Exception:
                    pass

        # update stored state
        if cur_e is not None:
            self._gcode_last_e = cur_e
        if cur_f is not None:
            self._gcode_last_f = cur_f
        for axis in ('X','Y','Z'):
            if axis in params:
                self._gcode_pos[axis] = params[axis]

    def _predicted_extrusion_rate(self):
        """Return predicted extrusion rate in mm/s computed from current lookahead."""
        with self._lookahead_lock:
            total_e = 0.0
            total_t = 0.0
            for e, d, _ in self._lookahead:
                total_e += abs(e)
                total_t += max(1e-6, float(d))
        if total_t <= 0:
            return 0.0
        return total_e / total_t

    def _read_current_load(self):
        try:
            if hasattr(self, 'tmc'):
                mcu_tmc = self.tmc.mcu_tmc
                val = mcu_tmc.get_register('SG_RESULT')
                if not isinstance(val, int):
                    val = int(val)
                return int(val)
        except Exception:
            try:
                val = self.tmc.get_register('SG_RESULT')
                return int(val)
            except Exception:
                pass
        return -1

    def cmd_SET_LOOKAHEAD(self, gcmd):
        # Basic and defensive parameter parsing. Klipper gcmd typically provides
        # get_float, but we attempt to be permissive if not present.
        try:
            # try Klipper-style parsing
            e = None
            d = None
            if hasattr(gcmd, 'get_float'):
                try:
                    e = gcmd.get_float('E')
                except Exception:
                    e = None
                try:
                    d = gcmd.get_float('D')
                except Exception:
                    d = None

            # fallback: parse remaining command string
            if (e is None or d is None) and hasattr(gcmd, 'command'):
                raw = str(gcmd.command).upper()
                if 'CLEAR' in raw:
                    self.clear_lookahead()
                    gcmd.respond_info('Lookahead cleared')
                    return
                # naive parse of tokens like E=1.23 D=0.5
                for token in raw.replace(',', ' ').split():
                    if token.startswith('E='):
                        try:
                            e = float(token.split('=', 1)[1])
                        except Exception:
                            pass
                    if token.startswith('D='):
                        try:
                            d = float(token.split('=', 1)[1])
                        except Exception:
                            pass

            if e is None and d is None:
                gcmd.respond_info('Usage: SET_LOOKAHEAD E=<mm> D=<s> | SET_LOOKAHEAD CLEAR')
                return

            if e is None or d is None:
                gcmd.respond_info('Both E and D are required (unless CLEAR)')
                return

            self.add_lookahead_segment(e, d)
            gcmd.respond_info(f'Added lookahead segment E={e} D={d}')
        except Exception as exc:
            gcmd.respond_info(f'Error in SET_LOOKAHEAD: {str(exc)}')

    def cmd_GET_PREDICTED_LOAD(self, gcmd):
        try:
            pred_rate = self._predicted_extrusion_rate()
            cur_load = self._read_current_load()

            # Estimate future load by scaling current load by rate ratio using
            # a recent-rate baseline (fallback to pred_rate if no history).
            baseline = None
            if len(self._recent_rates) > 0:
                baseline = sum(self._recent_rates) / len(self._recent_rates)
            else:
                baseline = pred_rate if pred_rate > 0 else 1.0

            est_load = -1
            if cur_load >= 0 and baseline > 0:
                try:
                    est_load = int(cur_load * (pred_rate / float(baseline)))
                except Exception:
                    est_load = cur_load

            gcmd.respond_info(f'Predicted rate: {pred_rate:.3f} mm/s, Estimated load: {est_load}')
        except Exception as exc:
            gcmd.respond_info(f'Error computing predicted load: {str(exc)}')

    def cmd_GET_EXTRUDER_LOAD(self, gcmd):
        try:
            val = self._read_current_load()
            gcmd.respond_info(f"Extruder Load (SG_RESULT): {val}")
        except Exception as e:
            gcmd.respond_info(f"Error reading TMC: {str(e)}")

    def get_status(self, eventtime):
        # Called by Klippy status updates; include predicted rate if available
        status = {'load': -1}
        try:
            status['load'] = self._read_current_load()
        except:
            status['load'] = -1

        pred_rate = self._predicted_extrusion_rate()
        status['predicted_extrusion_rate'] = pred_rate
        return status


def load_config(config):
    return ExtruderMonitor(config)
