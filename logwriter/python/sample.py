#!/usr/bin/env python
# -*- coding: utf-8 -*-

import VizexecLogWriter as vze
import threading
import time

gMessageBuf = None
gAckBuf = None
#------------------------------------------------------------------------------
# Functions for ProcessThread
#------------------------------------------------------------------------------
@vze.func
def WaitForMessage():
    global gMessageBuf
    while not gMessageBuf:
        time.sleep(1.0)
    msg = gMessageBuf
    gMessageBuf = None
    vze.recv(msg)
    return msg

@vze.func
def ProcessMessage(msg):
    time.sleep(1.0)
    vze.event("MessageProcessEvent")
    # do something
    time.sleep(2.0)
    return "<ackmessage>"

@vze.func
def SendAck(msg):
    global gAckBuf
    vze.send(msg)
    gAckBuf = msg

@vze.func_custom("ThreadMain")
def process_thread():
    vze.thread_name("ProcessThread")
    while True:
        msg = WaitForMessage()
        vze.phase("Process phase")
        result = ProcessMessage(msg)
        SendAck(result)

#------------------------------------------------------------------------------
# Functions for MainThread
#------------------------------------------------------------------------------
@vze.func
def CreateThread():
    t = threading.Thread(target = process_thread)
    t.setDaemon(True)
    t.start()
    time.sleep(1.0)


@vze.func
def SendMessage(msg):
    global gMessageBuf
    vze.send(msg)
    gMessageBuf = msg

@vze.func
def WaitForAck():
    global gAckBuf
    while not gAckBuf:
        time.sleep(1.0)
    vze.recv(gAckBuf)
    return gAckBuf

@vze.func
def ShowResult(result):
    print "Result: ", result;
    vze.event("DrawEvent")

@vze.func
def main():
    vze.thread_name("MainThread")
    CreateThread()
    SendMessage("testmessage")
    result = WaitForAck()
    ShowResult(result)

vze.start()
main()


