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

import threading
import gobject

from seqdata import SequenceData


class VizexecGUI:
    def __init__(self):
        self.seqdata = None

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

        self.new_data()
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
        
        

    def fit_figure_size(self):
        is_max = self.vadjust.get_value() >= (self.vadjust.get_upper() - self.vadjust.get_page_size() - 32)
        
        alloc = self.drawing_area.get_allocation()
        if self.seqdata.get_width() > alloc.width:
            self.hadjust.set_upper(self.seqdata.get_width() + 60)
            self.hadjust.set_page_size(alloc.width)
        if self.seqdata.get_height() > alloc.height:
            self.vadjust.set_upper(self.seqdata.get_height() + 60)
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
        

        self.seqdata.draw(ctx, offset_x, offset_y, w, h)
        
        drawarea_ctx.set_source_surface(self.back_buffer, 0, 0)
        drawarea_ctx.paint()
        self.figure_lock.release()


    def new_data(self):
        self.seqdata = SequenceData()

    def open_new(self, filename):
        self.new_data()
        self.open_append(filename)

    def open_append(self, filename):
        read_thread = ReadThread(filename, self)
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
    def __init__(self, fn, window):
        threading.Thread.__init__(self)
        self.fn = fn
        self.window = window
        self.seqdata = window.seqdata
        self.setDaemon(True)

    def run(self):
        file = open(self.fn, 'r')
        while True:
            line = file.readline()
            if not line:
                break
            self.window.figure_lock.acquire()
            self.seqdata.add_data_line(line)
            self.window.updated = True
            self.window.figure_lock.release()


if __name__ == "__main__":
    mainwindow = VizexecGUI()
    if len(sys.argv) >= 2:
        mainwindow.open_new(sys.argv[1])
    gtk.main()


