## {{{ http://code.activestate.com/recipes/473899/ (r2)
"""
Here is a silly example of its usage:

import progress
import time
import random

total = 1000
p = progress.ProgressMeter(total=total)

while total > 0:
    cnt = random.randint(1, 25)
    p.update(cnt)
    total -= cnt
    time.sleep(random.random())


Here is an example of its output:

[------------------------->                                   ] 41%  821.2/sec
"""
import time, sys, math


def change_unit_bytes(value):
    if value < 1024:
        return (value, 'B')
    elif value < 1048576:
        return (value/1024., 'kB')
    elif value < 1024**3:
        return (value/1048576., 'MB')
    else:
        return (value/(1024.**3), 'GB')


class ProgressMeter(object):
    ESC = chr(27)
    def __init__(self, total = 100, rate_refresh = 0.5):
        # Number of units to process
        self.total       = total
        # Refresh rate in seconds
        self.rate_refresh = rate_refresh
        self.count        = 0
        # dane progress bara
        self.meter_ticks    = 40
        self.meter_division = float(self.total) / self.meter_ticks
        self.meter_value    = int(self.count / self.meter_division)
        #time
        self.last_update = None
        #predkosc
        self.rate_current = 0.0
        #liczba jednostek od ostatniego odswiezenia predkosci
        self.rate_count   = 0
        #ostatnie odswiezenie
        self.last_refresh = 0
        self.history_len   = 10
        self.history       = [None]*self.history_len
        self.history_index = 0
        self._cursor = False
        self.reset_cursor()


    def reset_cursor(self, first=False):
        if self._cursor:
            sys.stdout.write(self.ESC + '[u')
        self._cursor = True
        sys.stdout.write(self.ESC + '[s')

    def update(self, count):
        now = time.time()
        # Caclulate rate of progress
        rate = 0.0
        # Add count to Total
        self.count += count
        self.count = min(self.count, self.total)
        if self.last_update == None:
            self.last_update = now
        
        self.rate_count   += count
        if now - self.last_update > 0.5: #FIXME
            self.history[self.history_index] = self.rate_count / float(now - self.last_update)
            self.history_index = (self.history_index + 1) % self.history_len
            hist = [i for i in self.history if i != None]
            self.rate_current = sum(hist)/float(len(hist))
            self.rate_count = 0
            self.last_update = now     
        
        
        # Device Total by meter division
        value = int(self.count / self.meter_division)
        if value > self.meter_value:
            self.meter_value = value
        if self.last_refresh:
            if (now - self.last_refresh) > self.rate_refresh or \
                (self.count >= self.total):
                    self.refresh()
        else:
            self.refresh()

    def get_meter(self, **kw):
        bar = '-' * self.meter_value
        pad = ' ' * (self.meter_ticks - self.meter_value)
        perc = (float(self.count) / self.total) * 100
        rate_current, unit =  change_unit_bytes(self.rate_current)
        downloaded, unit_d =  change_unit_bytes(self.count)
        total, unit_t      =  change_unit_bytes(self.total)
        return '[%s>%s] %d%%  %.1f%s/sec  %.1f%s/%.1f%s' % (bar, pad, perc, rate_current, unit, downloaded, unit_d, total, unit_t)


    def refresh(self, **kw):
        # Clear line
        if sys.platform.startswith('win'):
            sys.stdout.write('\r')
        else:
            sys.stdout.write(self.ESC + '[2K')
            self.reset_cursor()
        sys.stdout.write(self.get_meter(**kw))
        # Are we finished?
        if self.count >= self.total:
            sys.stdout.write('\r\n')
        sys.stdout.flush()
        # Timestamp
        self.last_refresh = time.time()
## end of http://code.activestate.com/recipes/473899/ }}}

