import RPi.GPIO as GPIO
import itertools
import time

# WARNING: EARLY ALPHA!!

#upper pins
PINS =  (14, 15, 18, 23, 24, 25, 8, 7)#, 12, 16, 20, 21)
PATTERN = (0,1,1,0,0,1,1,1,0,1,0,0,1,1,0,1,1,0,1,0,0,0,0,1,0,1,1,1,0,0,1,0,0,1)
TAP_RESET = (1,1,1,1,1)
TAP_SHIFTDR = (1,1,1,1,1,0,1,0,0)
TAP_SHIFTIR = (1,1,1,1,1,0,1,1,0,0)
DELAY = 0.00005
MAX_DEV_NR = 8
ICODE_LEN = 32
IGNORE_PIN = -1
ACTIVE_TOGGLE_THRESHOLD = 1

VERBOSE_LEVEL = 0

def scan_active_pins(timespan, count):
    active_pins = []
    last_data = [0]*len(PINS)
    toggle_count = [0]*len(PINS)
    i = 0
    print 'Starting scan for active pins'
    for pin in PINS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        last_data[i] = GPIO.input(pin)
        i+=1
    t = 0
    while t < timespan:
        i = 0
        for pin in PINS:
            d = GPIO.input(pin)
            if last_data[i] != d:
                toggle_count[i] += 1
                last_data[i] = d
            if VERBOSE_LEVEL >= 1:
                print pin, '=>', d,
            i += 1
        if VERBOSE_LEVEL >= 1:
            print ' '
        time.sleep(timespan / count)
        t += timespan / count
    print 'Active Pins '
    i = 0
    for pin in PINS:
        if toggle_count[i] >= ACTIVE_TOGGLE_THRESHOLD:
            print 'Pin', pin, '=>', toggle_count[i], 'edge(s)'
            active_pins.append(pin)
        i += 1
    if len(active_pins) <= 0:
        print 'None'
    return active_pins
        

def tap_state(tap_state_pattern, tck, tms):
    if VERBOSE_LEVEL >= 2:
        print 'tap_state: tms set to:',
    for ts in tap_state_pattern:
        if DELAY > 0:
            time.sleep(DELAY)
        GPIO.output(tck, GPIO.LOW)
        if VERBOSE_LEVEL >= 2:
            print ts,
        GPIO.output(tms, ts)
        GPIO.output(tck, GPIO.HIGH)
    if VERBOSE_LEVEL >= 2:
        print ' '

def init_pins(tck, tms, tdi, ntrst):
    for pin in PINS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    if tck != IGNORE_PIN:
        GPIO.setup(tck, GPIO.OUT)
    if tms != IGNORE_PIN:
        GPIO.setup(tms, GPIO.OUT)
    if tdi != IGNORE_PIN:
        GPIO.setup(tdi, GPIO.OUT)
    if ntrst != IGNORE_PIN:
        GPIO.setup(ntrst, GPIO.OUT)
        GPIO.output(ntrst, GPIO.HIGH)

def check_data(pattern, iteration, tck, tdi, tdo):
    tdo_prev = GPIO.input(tdo)
    nr_toggle = 0
    rcv = [0]*len(pattern)
    w = 0
    for i in xrange(iteration):
        pulse_tdi(tck, tdi, pattern[i%len(pattern)])
        tdo_read = GPIO.input(tdo)
        if tdo_read != tdo_prev:
            nr_toggle += 1
        tdo_prev = tdo_read
        if i < len(pattern):
            rcv[i] = tdo_read
        else:
            rcv = rcv[1:]
            rcv.append(tdo_read)

        if i >= (len(pattern)-1):
            if rcv == pattern: 
                return (1, i + 1 - len(pattern))
    if nr_toggle > 1:
        return (nr_toggle, 0)
    return (0, 0)

def pulse_tdo(tck, tdo):
    if DELAY > 0:
        time.sleep(DELAY)
    GPIO.output(tck, GPIO.LOW)
    tdo_read = GPIO.input(tdo)
    GPIO.output(tck, GPIO.HIGH)
    return tdo_read

def pulse_tdi(tck, tdi, data):
    if tck == IGNORE_PIN:
        return
    if DELAY > 0:
        time.sleep(DELAY)
    GPIO.output(tck, GPIO.LOW)
    GPIO.output(tdi, data)
    GPIO.output(tck, GPIO.HIGH)
    
def scan():
    print 'Starting scan for pattern', PATTERN
    for comb in itertools.permutations(PINS, 5):
        ntrst, tck, tms, tdo, tdi = comb
        if VERBOSE_LEVEL >= 1:
            print 'ntrst:', ntrst, 'tck:', tck, 'tms:', tms, 'tdo:', tdo, 'tdi:', tdi
        init_pins(tck, tms, tdi, ntrst)
        tap_state(TAP_SHIFTIR, tck, tms)
        checkdataret, reg_len = check_data(PATTERN, 128, tck, tdi, tdo)
        if checkdataret == 1:
            print 'FOUND!', 'TCK:',tck, 'TMS:', tms, 'TDO:', tdo, 'TDI:', tdi, 'NTRST:', ntrst, 'IR length', reg_len
        elif checkdataret > 1:
            print 'active', 'TCK:',tck, 'TMS:', tms, 'TDO:', tdo, 'TDI:', tdi, 'NTRST:', ntrst, 'bits toggled', checkdataret
    

def scan_idcode():
    print 'Starting scan for idcode'
    idcodes = []
    for comb in itertools.permutations(PINS, 5):
        ntrst, tck, tms, tdo, tdi = comb
        if VERBOSE_LEVEL >= 1:
            print 'ntrst:', ntrst, 'tck:', tck, 'tms:', tms, 'tdo:', tdo, 'tdi:', tdi
        init_pins(tck, tms, tdi, ntrst)
        tap_state(TAP_RESET, tck, tms)
        tap_state(TAP_SHIFTDR, tck, tms)
        for i in xrange(MAX_DEV_NR):
            idcodes.append(0)
            for j in xrange(ICODE_LEN):
                pulse_tdi(tck, tdi, 0)
                tdo_read = GPIO.input(tdo)
                if tdo_read == GPIO.HIGH:
                    idcodes[i] |= (1 << j)

                if VERBOSE_LEVEL >= 2:
                    print 'tdo_read:', tdo_read
            if VERBOSE_LEVEL >= 1:
                print 'IDCODE:', hex(idcodes[i])

            if idcodes[i]%2 == 0 or idcodes[i] == 0xffffffff:
                break
        if i > 0:
            print 'TCK:',tck, 'TMS:', tms, 'TDO:', tdo, 'TDI:', tdi, 'NTRST:', ntrst, 'devices:', i, [hex(x) for x in idcodes]

def loopback_check():
    print 'Starting loopback check'
    for comb in itertools.permutations(PINS, 2):
        tdo, tdi = comb
        if VERBOSE_LEVEL >= 1:
            print 'tdo:', tdo, 'tdi:', tdi
        init_pins(IGNORE_PIN, IGNORE_PIN, tdi, IGNORE_PIN)
        checkdataret, reg_len = check_data(PATTERN, 128, IGNORE_PIN, tdi, tdo)
        if checkdataret == 1:
            print 'FOUND! tdo:', tdo, 'tdi:', tdi, 'reglen:', reglen
        if checkdataret > 1:
            print 'active tdo:', tdo, 'tdi:', tdi, 'bits toggled:', checkdataret
        
        
def main():
    GPIO.setmode(GPIO.BCM)
    try:
        print '=============================='
        #scan_active_pins(10.0, 1000)
        #loopback_check()
        #print '=============================='
        scan()
        print '=============================='
        scan_idcode()
        print '=============================='
    except KeyboardInterrupt:
        print 'teh end!'
    finally:
        GPIO.cleanup()

main()
