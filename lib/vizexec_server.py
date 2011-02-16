#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading


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

