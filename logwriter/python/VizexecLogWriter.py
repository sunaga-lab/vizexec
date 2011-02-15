# -*- coding: utf-8 -*-

import os
import threading

log_file = None
time_counter = 0

# for internal
def build_id(params):
    return "_".join(str(p) for p in params)


def start():
    """ Start LogWriter """
    global log_file
    
    if "VIZEXEC_LOGFILE" in os.environ:
        log_file_name = os.environ["VIZEXEC_LOGFILE"]
    else:
        log_file_name = "vizexec.log"
        
    print "VizEXEC: Wait for log writing"
    log_file = open(log_file_name, 'w')
    write_log_comment("Start VizEXEC Log")
    write_log_comment("writer: python-vlw")
    print "VizEXEC: Start"

def write_log(logtype, *params):
    global time_counter
    time_counter += 1
    write_log_notime(logtype, *((time_counter,) + params))

def write_log_comment(cmt):
    log_file.write("# "+cmt+"\n")

def write_log_notime(logtype, *params):
    global log_file
    if not log_file:
        return
    line = str(logtype) + " " + str(id(threading.currentThread()))
    for p in params:
        line += ' "{0}"'.format(str(p))
    log_file.write(line+"\n")
    log_file.flush()

def func(f):
    """ Marker for functions """
    return func_custom(f.func_name)(f)
    

def func_custom(fname):
    """ Marker for functions with custom name """
    def decorator(f):
        def decorated(*idp, **kwp):
            try:
                write_log("CAL", fname)
                return f(*idp, **kwp)
            finally:
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

def phase(pname):
    """ Phase change marker """
    write_log("PHS", pname)

