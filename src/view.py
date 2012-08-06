#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# Author: Adam Grycner (adam_gr [at] gazeta.pl)
#
# Written: 12/11/2011
#
# Released under: GNU GENERAL PUBLIC LICENSE
#
# Ver: 0.4

import ctypes
import sys
import threading
import time, math   



    

###############################################################################################################
if sys.platform.startswith('win'):
    SHORT    = ctypes.c_short
    WORD     = ctypes.c_ushort
    STD_OUTPUT_HANDLE = -11
    
    class COORD(ctypes.Structure):
        _fields_ = [('X', SHORT),('Y', SHORT)]
        
    class SMALL_RECT(ctypes.Structure):
        _fields_ = [("Left", ctypes.c_short), ("Top",ctypes.c_short), ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)]

    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [("Size", COORD), ("CursorPosition", COORD), ("Attributes", ctypes.c_short), ("Window", SMALL_RECT), ("MaximumWindowSize", COORD)]

    class CONSOLE_CURSOR_INFO(ctypes.Structure):
        _fields_ = [('dwSize',ctypes.c_ulong), ('bVisible', ctypes.c_int)]

    hconsole = ctypes.windll.kernel32.GetStdHandle(-11)
    sbinfo   = CONSOLE_SCREEN_BUFFER_INFO()
    csinfo   = CONSOLE_CURSOR_INFO()
    to_int   = lambda number, default: number and int(number) or default
    

            
    class ConsoleWin(object):
        def __init__(self):
            self.hconsole      = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            self.orig_sbinfo   = CONSOLE_SCREEN_BUFFER_INFO()
            self.orig_csinfo   = CONSOLE_CURSOR_INFO()
            ctypes.windll.kernel32.GetConsoleScreenBufferInfo(self.hconsole, ctypes.byref(self.orig_sbinfo))
            ctypes.windll.kernel32.GetConsoleCursorInfo(hconsole, ctypes.byref(self.orig_csinfo))
            
        def screen_buffer_info(self):
            sbinfo = CONSOLE_SCREEN_BUFFER_INFO()
            ctypes.windll.kernel32.GetConsoleScreenBufferInfo(self.hconsole, ctypes.byref(sbinfo))
            return sbinfo
        
        def clear_line(self, param = 2):
            #clearing line
            #param == 1: Clear from begining of line to cursor position
            #param == 2: Clear entire line
            #else: Clear from cursor position to end of line
            mode   = param and int(param) or 0
            sbinfo = self.screen_buffer_info()
            if mode == 1: # Clear from begining of line to cursor position
                line_start = COORD(0, sbinfo.CursorPosition.Y)
                line_length = sbinfo.Size.X
            elif mode == 2: # Clear entire line
                line_start = COORD(sbinfo.CursorPosition.X, sbinfo.CursorPosition.Y)
                line_length = sbinfo.Size.X - sbinfo.CursorPosition.X
            else: # Clear from cursor position to end of line
                line_start = sbinfo.CursorPosition
                line_length = sbinfo.Size.X - sbinfo.CursorPosition.X
            chars_written = ctypes.c_int()
            ctypes.windll.kernel32.FillConsoleOutputCharacterA(self.hconsole, ctypes.c_char(' '), line_length, line_start, ctypes.byref(chars_written))
            ctypes.windll.kernel32.FillConsoleOutputAttribute(self.hconsole, sbinfo.Attributes, line_length, line_start, ctypes.byref(chars_written))
            
        def move_cursor(self, x_offset=0, y_offset=0):
            #moving cursor to specific part of screen
            sbinfo = self.screen_buffer_info()
            new_pos = COORD(
                min(max(0, sbinfo.CursorPosition.X + x_offset), sbinfo.Size.X),
                min(max(0, sbinfo.CursorPosition.Y + y_offset), sbinfo.Size.Y)
            )
            ctypes.windll.kernel32.SetConsoleCursorPosition(self.hconsole, new_pos)
        
        def move_up(self, param):
            #moving up certain (param) number of lines
            self.move_cursor(y_offset = -to_int(param, 1))

        def move_down(self, param):
            #moving down certain (param) number of lines
            self.move_cursor(y_offset = to_int(param, 1))
        
        def prev_line(self):
            #moving to previous line on screen
            sbinfo = self.screen_buffer_info()
            new_pos = COORD(
                min(0, sbinfo.Size.X),
                min(max(0, sbinfo.CursorPosition.Y -1), sbinfo.Size.Y)
            )
            ctypes.windll.kernel32.SetConsoleCursorPosition(self.hconsole, new_pos)
            
        def next_line(self):
            #moving to next line on screen
            sbinfo = self.screen_buffer_info()
            new_pos = COORD(
                min(0, sbinfo.Size.X),
                min(max(0, sbinfo.CursorPosition.Y +1), sbinfo.Size.Y)
            )
            ctypes.windll.kernel32.SetConsoleCursorPosition(self.hconsole, new_pos)
###############################################################################################################            
else:
    #TODO: tutaj moznaby jakas nadklase tych konsol stworzyc
    class ConsoleUnix(object):
        def __init__(self):
            self.ESC = chr(27)
            
        def clear_line(self, param = 2):
            #clearing line
            #param == 1: Clear from begining of line to cursor position
            #param == 2: Clear entire line
            #else: Clear from cursor position to end of line
            mode   = param and int(param) or 0
            if mode == 1: # Clear from begining of line to cursor position
                sys.stdout.write(self.ESC + '[1K')
            elif mode == 2: # Clear entire line
                sys.stdout.write(self.ESC + '[2K')
            else: # Clear from cursor position to end of line
                sys.stdout.write(self.ESC + '[0K')
        
        def move_cursor(self, x_offset=0, y_offset=0):
            #moving cursor to specific part of screen
            if x_offset >= 0:
                sys.stdout.write(self.ESC + '[%dC' % (x_offset) )
            else:
                sys.stdout.write(self.ESC + '[%dD' % (-x_offset) )
            if y_offset >= 0:
                sys.stdout.write(self.ESC + '[%dB' % (y_offset) )    
            else:
                sys.stdout.write(self.ESC + '[%dA' % (-y_offset) )    

        def move_up(self, param):
            #moving up certain (param) number of lines
            sys.stdout.write(self.ESC + '[%dA' % (param) )

        def move_down(self, param):
            #moving down certain (param) number of lines
            sys.stdout.write(self.ESC + '[%dB' % (param) )
            
        def prev_line(self):
            #moving to previous line on screen
            sys.stdout.write(self.ESC + '[1A' )
            sys.stdout.write('\r' )
            
        def next_line(self):
            #moving to next line on screen
            sys.stdout.write(self.ESC + '[1B' )
            sys.stdout.write('\r' )
###############################################################################################################
def change_unit_bytes(value):
    if value < 1024:
        return (value, 'B')
    elif value < 1048576:
        return (value/1024., 'kB')
    elif value < 1024**3:
        return (value/1048576., 'MB')
    else:
        return (value/(1024.**3), 'GB')
    
def change_unit_time(value):
    if value < 60:
        return (value, 's.')
    elif value < 60*60:
        return (value/60., 'min')
    else:
        return (value/3600., 'h.')

class ProgressBar(object):
    def __init__(self, total = 100, rate_refresh = 0.5, count = 0, name = ""):
        """count - starting value"""
        self.name        = name
        # Number of units to process
        self.total       = total
        # Refresh rate in seconds
        self.rate_refresh = rate_refresh
        
        # dane progress bara
        self.meter_ticks    = 20
        self.meter_division = float(self.total) / self.meter_ticks
        ##############################
        self.count        = count
        #count, ktore bedzie wyswietlane na ekranie
        self.count_total  = count
        #predkosc
        self.rate_current       = 0.0
        self.rate_current_total = 0.0
        self.meter_value       = int(self.count / self.meter_division)
        self.meter_value_total = int(self.count / self.meter_division)
        #############################
        #time
        self.last_update = None
        #liczba jednostek od ostatniego odswiezenia predkosci
        self.rate_count   = 0
        #ostatnie odswiezenie
        self.last_refresh = 0
        self.history_len   = 10
        self.history       = [None]*self.history_len
        self.history_index = 0
        self.lock = threading.Lock()


    def update(self, count):
        """
        Update data of progress bar
        """
        #rate_current
        #self.count
        #

        now = time.time()
        # Caclulate rate of progress
        rate = 0.0
        # Add count to Total
        self.count += count
        self.count = min(self.count, self.total)
        if self.last_update == None:
            self.last_update = now

        # Device Total by meter division
        value = int(self.count / self.meter_division)
        if value > self.meter_value:
            self.meter_value = value
        
        self.rate_count   += count
        if now - self.last_update > 0.5: #FIXME
            self.history[self.history_index] = self.rate_count / float(now - self.last_update)
            self.history_index = (self.history_index + 1) % self.history_len
            hist = [i for i in self.history if i != None]
            self.rate_current = sum(hist)/float(len(hist))
            self.rate_count = 0
            self.last_update = now            
            ###MUTEXES
            self.update_to_display()

    
    def update_to_display(self):
        """
        Actualize data to display
        """
        #self.lock.acquire()
        #try:
        self.meter_value_total   = self.meter_value
        self.count_total         = self.count
        self.rate_current_total  = self.rate_current
        #finally:
        #    self.lock.release()

    def get_meter(self, **kw):
        """
        Creating progress bar string
        """
        #self.lock.acquire()
        #try:
        bar = '-' * self.meter_value_total
        pad = ' ' * (self.meter_ticks - self.meter_value_total)
        perc = (float(self.count_total) / self.total) * 100
        rate_current, unit =  change_unit_bytes(self.rate_current_total)
        downloaded, unit_d =  change_unit_bytes(self.count_total)
        total, unit_t      =  change_unit_bytes(self.total)
        if self.rate_current_total == 0:
            rest_time      = float("inf")
            unit_time      = ''
        else:    
            rest_time, unit_time = change_unit_time( (self.total - self.count_total)/float(self.rate_current_total) )
        
        #finally:
        #    self.lock.release()
        return '[%s>%s] %d%%  %.1f%s/sec  %.1f%s/%.1f%s  %.1f%s' % (bar, pad, perc, rate_current, unit, downloaded, unit_d, total, unit_t, rest_time, unit_time)

###############################################################################################################
def create_console():
    """Creating console object depending on operating system"""
    if sys.platform.startswith('win'):
        return ConsoleWin()
    else:
        return ConsoleUnix()    

def change_print_coding(text):
    if sys.platform.startswith('win'):
        try:
            text = text.decode('utf-8')
        except Exception:
            try:
                text = text.decode('cp1250')
            except Exception, e:
                pass
    return text

def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance


#@singleton
class View(object):
    """
    View object (displaying informations)
    """
    def __init__(self):
        self.lock          = threading.Lock()
        self.progress_bars = []
        self.console       = create_console()
        self.last_update   = time.time()
    
    def print_(self, *args):
        """
        Print something on screen
        """
        self.lock.acquire()
        try:
            self.last_update   = time.time()
            self._wipe_progress_bars()
            for i in args: print change_print_coding(i),
            print
            self._show_progress_bars()
            sys.stdout.flush()
        finally:
            self.lock.release()
    
    def _wipe_progress_bars(self):
        """
        Remove progress bar objects from screen
        """
        for progress_bar in self.progress_bars:
            #TODO: kodowanie
            self.console.prev_line()
            self.console.clear_line(2)
            self.console.prev_line()
            self.console.clear_line(2)
        sys.stdout.flush()
    

    def _show_progress_bars(self):
        """
        Show progress bar objects on screen
        """
        for progress_bar in self.progress_bars:
            #TODO: kodowanie
            #sys.stdout.write( change_print_coding(progress_bar.name) )
            print change_print_coding(progress_bar.name[-80:]),
            sys.stdout.write('\r\n')
            sys.stdout.write(progress_bar.get_meter())
            sys.stdout.write('\r\n')
        sys.stdout.flush()

    
    def update_progress_bars(self):
        """
        Redisplay progress bar objects
        """
        #sprawdzic kiedy ostatnio byl aktualizowany ekran
        self.lock.acquire()
        try:
            now = time.time()
            if now - self.last_update > 0.5:
                self._wipe_progress_bars()
                self._show_progress_bars()
                sys.stdout.flush()
                self.last_update   = time.time()
        finally:
            self.lock.release()

    
    def add_progress_bar(self, progress_bar_object):
        """
        Add progress bar object on list
        """
        self.lock.acquire()
        try:
            #sys.stdout.write( change_print_coding(progress_bar_object.name) )
            print change_print_coding(progress_bar_object.name),
            sys.stdout.write('\r\n')
            sys.stdout.write(progress_bar_object.get_meter())
            sys.stdout.write('\r\n')        
            self.progress_bars.append(progress_bar_object)
        finally:
            self.lock.release()

    
    def delete_progress_bar(self, progress_bar_object):
        """
        Delete progress bar object from list
        """
        self.lock.acquire()
        try:
            #sys.stdout.write( change_print_coding(progress_bar_object.name) )
            self._wipe_progress_bars()
            print change_print_coding(progress_bar_object.name),
            sys.stdout.write('\r\n')
            progress_bar_object.update_to_display()
            sys.stdout.write(progress_bar_object.get_meter())
            sys.stdout.write('\r\n')        
            self.progress_bars.remove(progress_bar_object)
            self._show_progress_bars()
        finally:
            self.lock.release()
        

if __name__ == '__main__':
    v = View()
    pr = [ ProgressBar(total = 100, name = "probś" + str(i) ) for i in range(1,5)  ]
    for p in pr:
        v.add_progress_bar(p)
    for i in range(100):
        for p in pr:
            p.update(1)
        v.update_progress_bars()
        time.sleep(0.1)
        if i % 2 == 0:
            v.print_("Infośćł", i)
        if i == 25:
            p = ProgressBar(total = 100, name = "tmp1" )
            v.add_progress_bar( p )
            pr.append(p)
        if i == 50:
            v.delete_progress_bar( pr[0] )
        if i == 75:
            p = ProgressBar(total = 100, name = "tmp2" )
            v.add_progress_bar( p )
            pr.append( p )
