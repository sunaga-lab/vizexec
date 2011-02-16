# -*- coding: utf-8 -*-

import os
import threading
import socket

time_counter = 0

# for internal
def build_id(params):
    return "_".join(str(p) for p in params)

write_log_raw = None
flash_log_raw = None

def DoNothing(*prms):
    pass

def start():
    """ Start LogWriter """
    global log_file
    global write_log_raw, flush_log_raw

    if "VIZEXEC_LOGFILE" in os.environ:
        log_file_name = os.environ["VIZEXEC_LOGFILE"]
    else:
        log_file_name = "vizexec.log"
    
    
    print "VizEXEC: Wait for log writing"
    if log_file_name.startswith("tcp:"):
        scheme, host, port = log_file_name.split(':')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host.strip(), int(port.strip())))
        write_log_raw = sock.send
        flush_log_raw = DoNothing
    else:
        log_file = open(log_file_name, 'w')
        write_log_raw = log_file.write
        flush_log_raw = log_file.flush
        write_log_comment("Start VizEXEC Log")
        write_log_comment("writer: python-vlw")
    print "VizEXEC: Start"




def write_log(logtype, *params):
    global time_counter
    time_counter += 1
    write_log_notime(logtype, *((time_counter,) + params))

def write_log_comment(cmt):
    write_log_raw("# "+cmt+"\n")
    flush_log_raw()

def write_log_notime(logtype, *params):
    if not write_log_raw:
        return
    line = str(logtype) + " " + str(id(threading.currentThread()))
    for p in params:
        line += ' "{0}"'.format(str(p))
    write_log_raw(line+"\n")
    flush_log_raw()

def func(f):
    """ Marker for functions """
    return func_custom(f.func_name)(f)
    

def func_custom(fname):
    """ Marker for functions with custom name """
    def decorator(f):
        def decorated(*idp, **kwp):
            try:
                if write_log:
                    write_log("CAL", fname)
                return f(*idp, **kwp)
            finally:
                if write_log:
                    write_log("RET", fname)
        return decorated
    return decorator


def send(*msgobj):
    """ Sending marker """
    write_log("SND", build_id(msgobj))

def recv(*msgobj):
    """ Receiving marker """
    write_log("RCV", build_id(msgobj))

def thread_name(name):
    """ Thread naming marker """
    write_log_notime("TNM", name)

def event(ename):
    """ Event marker """
    write_log("EVT", ename)

def info(infostr):
    """ Additional information marker """
    write_log("EVT", infostr)

def phase(pname):
    """ Phase change marker """
    write_log("PHS", pname)


