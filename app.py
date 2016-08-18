#!/usr/bin/env python
# -*- coding: utf-8 -*-
# from __future__ import unicode_literals
import locale
import time
import random
import sys
import curses
import cv2
import os
import numpy
from instabot import InstaBot
from PIL import Image

PYTHON2 = sys.version_info.major < 3
locale.setlocale(locale.LC_ALL, '')
encoding = locale.getpreferredencoding()

########################################################################
# TUNABLES

DROPPING_CHARS = 50
MIN_SPEED = 1
MAX_SPEED = 7
RANDOM_CLEANUP = 100
WINDOW_CHANCE = 50
WINDOW_SIZE = 25
WINDOW_ANIMATION_SPEED = 3
FPS = 25
SLEEP_MILLIS = 1.0/FPS
USE_COLORS = True
SCREENSAVER_MODE = True
#MATRIX_CODE_CHARS = "ɀɁɂŧϢϣϤϥϦϧϨϫϬϭϮϯϰϱϢϣϤϥϦϧϨϩϪϫϬϭϮϯϰ߃߄༣༤༥༦༧༩༪༫༬༭༮༯༰༱༲༳༶"
MATRIX_CODE_CHARS = '!@#$%^&*()~{}|?><'
########################################################################
# CODE

COLOR_CHAR_NORMAL = 2
COLOR_CHAR_HIGHLIGHT = 3


class FallingChar(object):
    matrixchr = list(MATRIX_CODE_CHARS)
    normal_attr = curses.A_NORMAL
    highlight_attr = curses.A_REVERSE

    def __init__(self, width, MIN_SPEED, MAX_SPEED):
        self.x = 0
        self.y = 0
        self.speed = 1
        self.char = ' '
        self.reset(width, MIN_SPEED, MAX_SPEED)

    def reset(self, width, MIN_SPEED, MAX_SPEED):
        self.char = random.choice(FallingChar.matrixchr).encode(encoding)
        self.x = randint(1, width - 1)
        self.y = 0
        self.speed = randint(MIN_SPEED, MAX_SPEED)
        # offset makes sure that chars with same speed don't move all in same frame
        self.offset = randint(0, self.speed)

    def tick(self, scr, steps, padding_rows, padding_cols, output_rows, output_cols):
        height, width = scr.getmaxyx()
        in_picture_frame = self.y >= padding_rows and self.y <= padding_rows + output_rows and self.x >= padding_cols and self.x <= padding_cols + output_cols
        if self.advances(steps):
            # if window was resized and char is out of bounds, reset
            self.out_of_bounds_reset(width, height)
            # make previous char curses.A_NORMAL
            if not in_picture_frame:
                if USE_COLORS:
                    scr.addstr(self.y, self.x, self.char, curses.color_pair(COLOR_CHAR_NORMAL))
                else:
                    scr.addstr(self.y, self.x, self.char, curses.A_NORMAL)
            # choose new char and draw it A_REVERSE if not out of bounds
            self.char = random.choice(FallingChar.matrixchr).encode(encoding)
            self.y += 1
            in_picture_frame = self.y >= padding_rows and self.y <= padding_rows + output_rows and self.x >= padding_cols and self.x <= padding_cols + output_cols
            if not self.out_of_bounds_reset(width, height) and not in_picture_frame:
                if USE_COLORS:
                    scr.addstr(self.y, self.x, self.char, curses.color_pair(COLOR_CHAR_HIGHLIGHT))
                else:
                    scr.addstr(self.y, self.x, self.char, curses.A_REVERSE)

    def out_of_bounds_reset(self, width, height):
        if self.x > width-2:
            self.reset(width, MIN_SPEED, MAX_SPEED)
            return True
        if self.y > height-2:
            self.reset(width, MIN_SPEED, MAX_SPEED)
            return True
        return False

    def advances(self, steps):
        if steps % (self.speed + self.offset) == 0:
            return True
        return False

    def step(self, steps, scr):
        return -1, -1, None


# we don't need a good PRNG, just something that looks a bit random.
def rand():
    # ~ 2 x as fast as random.randint
    a = 9328475634
    while True:
        a ^= (a << 21) & 0xffffffffffffffff;
        a ^= (a >> 35);
        a ^= (a << 4) & 0xffffffffffffffff;
        yield a


r = rand()


def randint(_min, _max):
    if PYTHON2:
        n = r.next()
    else:
        n = r.__next__()
    return (n % (_max - _min)) + _min


# Returns the number of rows and columns of characters
def get_winsize():
    rows, columns = os.popen('stty size', 'r').read().split()
    return int(rows), int(columns)


def pixel_to_char(pixel):
    ramp = '  .:-=+*#%@'
    brightness = pixel/255.0
    ramp_index = int(len(ramp)*brightness)
    return ramp[ramp_index]


def curses_raw_input(stdscr, r, c, prompt_string):
    curses.echo()
    stdscr.addstr(r, c, prompt_string)
    stdscr.refresh()
    ret = stdscr.getstr(r, c + len(prompt_string))
    return ret


def curses_get_password(stdscr, r, c, prompt_string):
    curses.noecho()
    stdscr.addstr(r, c, prompt_string)
    stdscr.refresh()
    ret = stdscr.getstr(r, c + len(prompt_string))
    return ret


def main(arg):
    # Initialize curses
    steps = 0
    curses.initscr()
    curses.echo()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    # Create the window
    rows, columns = get_winsize()
    win = curses.newwin(rows, columns, 0, 0)
    win.bkgdset(curses.color_pair(1))
    if USE_COLORS:
        curses.init_pair(COLOR_CHAR_NORMAL, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(COLOR_CHAR_HIGHLIGHT, curses.COLOR_WHITE, curses.COLOR_GREEN)
    win.refresh()

    usr = curses_raw_input(win, 0, 0, "username: ")
    pw = curses_get_password(win, 1, 0, "password: ")
    win.erase()
    win.nodelay(1)
    curses.curs_set(0)
    curses.noecho()
    loading_string = "Loading simulation..."
    win.addstr(rows/2, columns/2 - len(loading_string)/2, loading_string)
    win.refresh()
    bot = InstaBot(login=usr, password=pw)
    win.erase()
    urls = bot.get_images()
    max_images = len(urls)
    highest_loaded = 3
    bot.save_images(urls[:highest_loaded], 0)
    files = os.listdir('cache')
    lines = []
    for i in range(DROPPING_CHARS):
        l = FallingChar(columns, MIN_SPEED, MAX_SPEED)
        l.y = randint(0, rows-2)
        lines.append(l)
    win.refresh()

    # Get the initial compression_factor
    img = numpy.array(Image.open('cache/' + files[0]))
    compression_factor = max(len(img)/rows, len(img[0])/columns)
    compression_factor_x = compression_factor
    row_compressed = compression_factor == len(img)/rows
    if row_compressed:
        compression_factor_x = 2 * compression_factor_x / 3
        if len(img[0]) / compression_factor_x > columns:
            compression_factor_x = len(img[0]) / columns

    # Function for drawing the image as characters
    def draw(img):
        for col in range(output_cols):
            for row in range(output_rows):
                if curses.is_term_resized(rows, columns):
                    return
                try:
                    pixel = img[row * compression_factor][col * compression_factor_x]
                    char = pixel_to_char(pixel)
                    win.addch(row + padding_rows, col + padding_cols, char)
                    win.refresh()
                except:
                    # win.addch() causes an exception if we try to draw beyond
                    # the boundaries of the window. We can just ignore it.
                    pass

    # Loop forever, handling terminal resizes
    i = 0
    while True:
        if(i == max_images - 1):
            msg = "Signal terminated."
            win.addstr(rows/2, columns/2 - len(msg)/2, msg)
            padding_rows = rows/2
            padding_cols = columns/2 - len(msg)/2
            output_rows = 1
            output_cols = len(msg)
            win.refresh()
        else:
            img = Image.open('cache/' + files[i])
            img = numpy.array(img)
            if curses.is_term_resized(rows, columns):
                rows, columns = get_winsize()
                win = curses.newwin(rows, columns, 0, 0)
                win.bkgdset(curses.color_pair(1))
            compression_factor = max(len(img)/rows, len(img[0])/columns)
            compression_factor_x = compression_factor
            row_compressed = compression_factor == len(img)/rows
            if row_compressed:
                compression_factor_x = 2 * compression_factor_x / 3
                if len(img[0]) / compression_factor_x > columns:
                    compression_factor_x = len(img[0]) / columns
            output_rows = len(img)/compression_factor
            output_cols = len(img[0])/compression_factor_x
            padding_rows = (rows - output_rows) / 2
            padding_cols = (columns - output_cols) / 2
            draw(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        if(highest_loaded < max_images):
            bot.save_images(urls[highest_loaded:highest_loaded+1], highest_loaded)
            highest_loaded += 1
            files = os.listdir('cache')
        inp = ''
        repeat = True
        while(repeat):
            time.sleep(SLEEP_MILLIS)
            inp = win.getch()
            if inp == ord('j'):
                if i < highest_loaded - 1:
                    i += 1
                    repeat = False
            elif inp == ord('k'):
                if i > 0:
                    i -= 1
                    repeat = False
            for line in lines:
                line.tick(win, steps, padding_rows, padding_cols, output_rows, output_cols)
            for _ in range(RANDOM_CLEANUP):
                x = randint(0, columns-1)
                y = randint(0, rows-1)
                if not (y > padding_rows and y < padding_rows + output_rows
                        and x > padding_cols and x < padding_cols + output_cols):
                    win.addstr(y, x, ' ')
            steps += 1
            if(i == max_images - 1):
                msg = "Signal terminated."
                win.addstr(rows/2, columns/2 - len(msg)/2, msg)
            win.refresh()

# Ensure curses is cleaned up correctly
try:
    curses.wrapper(main)
except:
    print("Program terminated.")
