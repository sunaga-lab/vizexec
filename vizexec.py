#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append("./lib")

try:
    import pygtk
    pygtk.require("2.8")
except:
    pass
try:
    import gtk
    import gtk.glade
    import cairo
    import time
except:
    sys.exit(1)

import figure_data
import threading
import gobject

from sequence_data_compiler_realtime import *

class VizexecGUI:
    def __init__(self):
        self.compiler = None
        self.figure = None
        self.UpdateInterval = 10
        self.builder = gtk.Builder()
        self.builder.add_from_file("data/vizexec_ui.glade")
        self.builder.connect_signals(self)

        self.import_control("window")
        self.import_control("AboutDialog")
        self.import_control("drawing_scroll")
        self.import_control("drawing_area")
        self.import_control("FileChooserDialog")
        self.window.show()
        
        self.hadjust = gtk.Adjustment()
        self.adjustment_default_setup(self.hadjust)
        self.hadjust.connect("value-changed", self.hadjust_value_changed)
        self.vadjust = gtk.Adjustment()
        self.adjustment_default_setup(self.vadjust)
        self.vadjust.connect("value-changed", self.vadjust_value_changed)
        
        self.drawing_scroll.set_hadjustment(self.hadjust)
        self.drawing_scroll.set_vadjustment(self.vadjust)

        self.back_buffer = None
        self.update_back_buffer()

        self.figure = figure_data.FigureData()
        self.figure_lock = threading.RLock()
        self.fit_figure_size()
        self.updated = False
        gobject.timeout_add(self.UpdateInterval, self.update_timeout)

        flt = gtk.FileFilter()
        flt.set_name("ログファイル")
        flt.add_pattern("*.log")
        self.FileChooserDialog.add_filter(flt)

        flt = gtk.FileFilter()
        flt.set_name("すべてのファイル")
        flt.add_pattern("*")
        self.FileChooserDialog.add_filter(flt)


    def update_back_buffer(self):
        alloc = self.drawing_area.get_allocation()
        
        if (self.back_buffer
            and self.back_buffer.get_width() == alloc.width
            and self.back_buffer.get_height() == alloc.height):
            return

        self.back_buffer = cairo.ImageSurface(cairo.FORMAT_RGB24, alloc.width, alloc.height)
        


    def set_figure(self, fig):
        self.figure = fig
        self.fit_figure_size()

    def fit_figure_size(self):
        is_max = self.vadjust.get_value() >= (self.vadjust.get_upper() - self.vadjust.get_page_size() - 32)
        
        alloc = self.drawing_area.get_allocation()
        if self.figure.get_width() > alloc.width:
            self.hadjust.set_upper(self.figure.get_width() + 60)
            self.hadjust.set_page_size(alloc.width)
        if self.figure.get_height() > alloc.height:
            self.vadjust.set_upper(self.figure.get_height() + 60)
            self.vadjust.set_page_size(alloc.height)

        if is_max:
            self.vadjust.set_value(self.vadjust.get_upper() - self.vadjust.get_page_size())

    def adjustment_default_setup(self, adj):
        adj.set_lower(0)
        adj.set_upper(0)
        adj.set_page_size(100)
        adj.set_step_increment(10)

    def import_control(self, name):
        setattr(self, name, self.builder.get_object(name))


    def btn_clicked(self, w):
        print "Btn Clicked."
    
    def window_hide(self, widget):
        gtk.main_quit()

    def hadjust_value_changed(self, w):
        self.redraw()

    def vadjust_value_changed(self, w):
        self.redraw()

    def drawing_area_expose_event_cb(self, w, e):
        self.redraw()
    
    def update_timeout(self):
        time.sleep(0.001)
        if self.updated:
            self.redraw()
            self.updated = False
        gobject.timeout_add(self.UpdateInterval, self.update_timeout)

    def redraw(self):
        self.figure_lock.acquire()
        self.update_back_buffer()
        self.fit_figure_size()
        offset_x = self.hadjust.get_value()
        offset_y = self.vadjust.get_value()


        alloc = self.drawing_area.get_allocation()
        w,h = alloc.width, alloc.height

        ctx = cairo.Context(self.back_buffer)
        drawarea_ctx = self.drawing_area.window.cairo_create()
        # ctx = self.drawing_area.window.cairo_create()
        ctx.set_source_rgb(1.0,1.0,1.0)
        ctx.rectangle(0,0, w,h)
        ctx.fill()
        
        for node in self.figure.get_node_in_rect(offset_x, offset_y, offset_x+w, offset_y+h):
            node.draw(ctx, offset_x, offset_y)
        
        drawarea_ctx.set_source_surface(self.back_buffer, 0, 0)
        drawarea_ctx.paint()
        self.figure_lock.release()


    def new_figure(self):
        fig = figure_data.FigureData()
        self.set_figure(fig)
        self.compiler = SequenceCompiler()
        # compiler.set_data(sample_data)
        self.compiler.fig = self.figure

    def open_new(self, filename):
        self.new_figure()
        self.open_append(filename)

    def open_append(self, filename):
        read_thread = ReadThread(filename, self.compiler)
        read_thread.start()


    def file_choose(self):
        resp = self.FileChooserDialog.run()
        self.FileChooserDialog.hide()
        if resp == 1:
            return "open", self.FileChooserDialog.get_filename()
        elif resp == 2:
            return "append", self.FileChooserDialog.get_filename()
        else:
            return "cancel", ""
        

    def MniOpen_activate_cb(self, e):
        mode, fn = self.file_choose()
        if mode == "open":
            self.open_new(fn)
        elif mode == "append":
            self.open_append(fn)

    def MniOpenAppend_activate_cb(self, e):
        fn = self.file_choose()
        if fn:
            self.open_new(fn)
        

    def MniExit_activate_cb(self, e):
        gtk.main_quit()

    def MniAbout_activate_cb(self, e):
        self.AboutDialog.run()
        self.AboutDialog.hide()

class ReadThread(threading.Thread):
    def __init__(self, fn, compiler):
        threading.Thread.__init__(self)
        self.fn = fn
        self.compiler = compiler
        self.setDaemon(True)

    def run(self):
        file = open(self.fn, 'r')
        while True:
            line = file.readline()
            if not line:
                break
            gWnd.figure_lock.acquire()
            self.compiler.add_data_line(line)
            self.compiler.ybase_increased()
            gWnd.updated = True
            gWnd.figure_lock.release()
        print "ReadThread: exit for ", self.fn


gWnd = None
if __name__ == "__main__":
    gWnd = VizexecGUI()
    if len(sys.argv) > 2:
        gWnd.open_new(sys.argv[1])
    gtk.main()


