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
    import pango
    import time
except:
    sys.exit(1)

import threading
import gobject

from seqdata import SequenceData
from vizexec_server import *


WINDOW_TITLE = "VizEXEC"

class VizexecGUI:
    def __init__(self):
        self.seqdata = None
        self.current_thread_group_id_max = 0
        self.UpdateInterval = 10
        self.seqdata_lock = threading.RLock()

        self.builder = gtk.Builder()
        self.builder.add_from_file("data/vizexec_ui.glade")
        self.builder.connect_signals(self)

        self.import_control("window")
        self.import_control("AboutDialog")
        self.import_control("drawing_scroll")
        self.import_control("drawing_area")
        self.import_control("FileChooserDialog")
        self.import_control("DlgSaveFile")
        self.import_control("TbfInfo")
        self.import_control("TvwInfo")
        self.import_control("DlgRunServer")
        self.import_control("EntPortNum")
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


        self.EntPortNum.set_text("5112")

        self.new_data()
        self.fit_figure_size()
        self.updated = False
        gobject.timeout_add(self.UpdateInterval, self.update_timeout)

        flt = gtk.FileFilter()
        flt.set_name("ログファイル")
        flt.add_pattern("*.log")
        self.FileChooserDialog.add_filter(flt)
        self.DlgSaveFile.add_filter(flt)

        flt = gtk.FileFilter()
        flt.set_name("すべてのファイル")
        flt.add_pattern("*")
        self.FileChooserDialog.add_filter(flt)
        self.DlgSaveFile.add_filter(flt)
        
        pangoFont = pango.FontDescription("monospace 9")
        self.TvwInfo.modify_font(pangoFont)

    def new_thread_group_id(self):
        self.current_thread_group_id_max += 1
        return "g" + str(self.current_thread_group_id_max)

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

    def redraw(self, check_first = False):
        with self.seqdata_lock:
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
            
            if check_first:
                self.seqdata.draw(ctx, offset_x, offset_y, w, h, True)
            self.seqdata.draw(ctx, offset_x, offset_y, w, h)
            
            drawarea_ctx.set_source_surface(self.back_buffer, 0, 0)
            drawarea_ctx.paint()


    def new_data(self):
        self.seqdata = SequenceData()
        self.redraw()

    def open_new(self, filename):
        self.new_data()
        self.open_append(filename)
        self.window.set_title(WINDOW_TITLE + " - File " + filename)

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

    def drawing_area_button_press_event_cb(self, e, data):
        self.seqdata.selected_object = None
        self.seqdata.selected_pos = (data.x,data.y)
        self.redraw(True)
        self.seqdata.selected_pos = None
        
        if self.seqdata.selected_object:
            obj = self.seqdata.selected_object
            if hasattr(obj, "get_info_text"):
                self.TbfInfo.set_text(obj.get_info_text())
            else:
                self.TbfInfo.set_text(str(obj))

    def open_server(self, portnum):
        server_thread = TCPServerThread(portnum, self)
        server_thread.start()
        
        self.window.set_title(WINDOW_TITLE + " - Server *:" + str(portnum))
        
    
    def MniRunServer_activate_cb(self, e):
        resp = self.DlgRunServer.run()
        self.DlgRunServer.hide()
        if resp == 1:
            self.new_data()
            portnum = int(self.EntPortNum.get_text())
            self.open_server(portnum)
        else:
            return
    
    def MniSaveAs_activate_cb(self, e):
        resp = self.DlgSaveFile.run()
        self.DlgSaveFile.hide()
        if resp == 1:
            with self.seqdata_lock:
                self.seqdata.save_log_to(self.DlgSaveFile.get_filename())

if __name__ == "__main__":
    mainwindow = VizexecGUI()
    if len(sys.argv) >= 2:
        if sys.argv[1] == "-s":
            mainwindow.open_server(int(sys.argv[2]))
        else:
            mainwindow.open_new(sys.argv[1])
    gtk.main()


