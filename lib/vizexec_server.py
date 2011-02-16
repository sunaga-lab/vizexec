#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import SocketServer
import StringIO
SocketServer.TCPServer.allow_reuse_address = True


class ReadThread(threading.Thread):
    def __init__(self, fn, window):
        threading.Thread.__init__(self)
        self.fn = fn
        self.window = window
        self.thread_group = self.window.new_thread_group_id()
        self.seqdata = window.seqdata
        self.setDaemon(True)

    def run(self):
        file = open(self.fn, 'r')
        while True:
            line = file.readline()
            if not line:
                break
            with self.window.seqdata_lock:
                self.seqdata.add_data_line(line, self.thread_group)
                self.window.updated = True



class TCPLogHandler(SocketServer.BaseRequestHandler):
    def setup(self):
        self.window = self.server.window
        self.thread_group = self.window.new_thread_group_id()
        self.buf = ""
        print "Connected, group = " , self.thread_group

    def handle(self):
        while True:
            idx = self.buf.find("\n")
            if idx == -1:
                recved = self.request.recv(4096)
                if not recved:
                    return
                self.buf += recved
                continue
            line = self.buf[:idx]
            self.buf = self.buf[idx + 1:]
            with self.window.seqdata_lock:
                self.window.seqdata.add_data_line(line, self.thread_group)
                self.window.updated = True

    def finish(self):
        print "Disconnected, group = " , self.thread_group
        with self.window.seqdata_lock:
            self.window.seqdata.terminated_lifeline_group(self.thread_group)
            self.window.updated = True

class TCPServerThread(threading.Thread):
    def __init__(self, port, window):
        threading.Thread.__init__(self)
        self.port = port
        self.window = window
        self.seqdata = window.seqdata
        self.setDaemon(True)

    def run(self):
        server = SocketServer.ThreadingTCPServer(('', self.port), TCPLogHandler)
        server.window = self.window
        while True:
            server.handle_request()
