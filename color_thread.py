#!/usr/bin/env python
# coding=utf-8
import logging
import threading
from statistics import mode
from time import sleep

from PIL import Image
from desktopmagic.screengrab_win32 import *
from lifxlan import LifxLAN, utils

from utils import get_primary_monitor
from settings import config


def avg_screen_color(initial_color):
    monitor = config["AverageColor"]["DefaultMonitor"]
    if monitor == "all":
        im = getScreenAsImage()
    else:
        im = getRectAsImage(eval(monitor))
    color = im.resize((1, 1), Image.HAMMING).getpixel((0, 0))
    color_hsbk = utils.RGBtoHSBK(color, temperature=initial_color[3])
    # return tuple((val1+val2)/2 for (val1, val2) in zip(initial_color, color_hsbk))
    return utils.RGBtoHSBK(color, temperature=initial_color[3])


def mode_screen_color(initial_color):
    """ Probably a more accurate way to get screen color, but is incredibly slow. """
    im = getRectAsImage(getDisplayRects()[1]).resize((500, 500))
    color = mode(im.load()[x, y] for x in range(im.width) for y in range(im.height) if
                 im.load()[x, y] != (255, 255, 255) and im.load()[x, y] != (0, 0, 0))
    return utils.RGBtoHSBK(color, temperature=initial_color[3])


class ColorThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


class ColorThreadRunner:
    def __init__(self, bulb, color_function, parent, continuous=True):
        self.bulb = bulb
        self.color_function = color_function
        self.parent = parent  # couple to parent frame
        self.logger = logging.getLogger(parent.logger.name + '.Thread({})'.format(color_function.__name__))
        self.prev_color = parent.get_color_values_hsbk()
        self.continuous = continuous
        self.t = ColorThread(target=self.match_color, args=(self.bulb,))
        try:
            label = self.bulb.get_label()
        except Exception:
            label = "<LABEL-ERR>"
        self.logger.info(
            'Initialized Thread: Bulb: {} // Continuous: {}'.format(label, self.continuous))

    def match_color(self, bulb):
        self.logger.debug('Starting color match.')
        self.prev_color = self.parent.get_color_values_hsbk()  # coupling to LightFrame from gui.py here
        duration_secs = 1 / 15
        transition_time_ms = duration_secs * 1000
        while not self.t.stopped():
            try:
                color = self.color_function(initial_color=self.prev_color)
                bulb.set_color(color, 0,
                               True if duration_secs < 1 else False)
                self.prev_color = color
            except OSError:
                # This is dirty, but we really don't care, just keep going
                self.logger.info("Hit an os error")
                continue
            sleep(duration_secs)
            if not self.continuous:
                self.stop()
        self.logger.debug('Color match finished.')

    def start(self):
        if self.t.stopped():
            self.t = ColorThread(target=self.match_color, args=(self.bulb,))
            self.t.setDaemon(True)
        try:
            self.t.start()
            self.logger.debug('Thread started.')
        except RuntimeError:
            self.logger.error('Tried to start ColorThread again.')

    def stop(self):
        self.t.stop()


def install_thread_excepthook():
    """
    Workaround for sys.excepthook thread bug
    (https://sourceforge.net/tracker/?func=detail&atid=105470&aid=1230540&group_label=5470).
    Call once from __main__ before creating any threads.
    If using psyco, call psycho.cannotcompile(threading.Thread.run)
    since this replaces a new-style class method.
    """
    import sys
    run_old = threading.Thread.run

    def run(*args, **kwargs):
        try:
            run_old(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            sys.excepthook(*sys.exc_info())

    threading.Thread.run = run


install_thread_excepthook()