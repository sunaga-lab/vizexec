# -*- coding: utf-8 -*-

import os
import threading

log_file = None
time_counter = 0

def start():
    global log_file
    
    if "VIZEXEC_LOGFILE" in os.environ:
        log_file_name = os.environ["VIZEXEC_LOGFILE"]
    else:
        log_file_name = "vizexec.log"
        
    log_file = open(log_file_name, 'w')


def write_log(logtype, *params):
    time_counter += 1
    write_log_notime(logtype, *((time_counter,) + params))


def write_log_notime(logtype, *params):
    global log_file
    if not log_file:
        return
    line = str(logtype) + " " + id(threading.currentThread())
    for p in params:
        line += ' "{0}"'.format(str(p))
    log_file.write(line+"\n")

def func(f):
    return func_custom(f.func_name)(f)
    

def func_custom(name):
    def decorator(f):
        def decorated(*idp, **kwp):
            try:
                write_log("CAL", fname)
                return f(*idp, **kwp)
            finally:
                write_log("RET", fname)
        return decorated
    return decorator

def build_id(params):
    return "_".join(str(p) for p in params)

def send(*msgobj):
    write_log("SND", build_id(msgobj))

def recv(*msgobj):
    write_log("RCV", build_id(msgobj))

def thread_name(name):
    write_log_notime("TNM", name)

def event(ename):
    write_log("EVT", ename)

