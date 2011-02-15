# -*- coding: utf-8 -*-

import bisect
import shlex
import gtk
import gtk.glade
import cairo
import traceback


def StrToColor(s):
    col = gtk.gdk.Color(s)
    return (col.red / 65535.0, col.green / 65535.0, col.blue / 65535.0)



class LifelineEntity:
    def __init__(self, ypos, event_type, stack):
        self.ypos = ypos
        self.event_type = event_type
        self.stack = stack


class Lifeline:
    def __init__(self, lifeline_id, start_ypos):
        self.lifeline_id = lifeline_id
        self.entity_list = []
        self.start_ypos = start_ypos
        self.current_ypos = start_ypos
        self.current_stack = []

    def new_entity(self, event_type, add_ypos = 20):
        entity = LifelineEntity(self.current_ypos, event_type, self.current_stack)
        self.entity_list.append(entity)
        self.current_ypos += add_ypos

    def stack_push(self, name):
        self.current_stack = self.current_stack[:]
        self.current_stack.append(name)

    def stack_pop(self, name):
        self.current_stack = self.current_stack[:]
        self.current_stack.pop()

    def put_call(self, func_name):
        self.stack_push(func_name)
        entity = self.new_entity("call")
        entity.func_name = func_name

    def put_return(self, func_name):
        self.stack_pop(func_name)
        entity = self.new_entity("return")

    def draw(self, ctx, offset_x, offset_y, w, h):
        drawer = LifelineDrawer(self)
        drawer.draw(self, ctx, offset_x, offset_y, w, h)

FONTNAME = "Serif"
FONTSIZE = 14
BAR_WIDTH = 8
FONTCOLOR = "#0000FF"

class LifelineDrawer:
    def __init__(self, ll):
        self.stack = []
        self.ll = ll

    def draw(self, ctx, offset_x, offset_y, w, h):
        elist = self.ll.entity_list
        idx = bisect.bisect_left(elist, offset_y) - 1
        if idx == -1:
            idx = 0
        
        while True:
            if idx >= len(elist) or elist[idx].ypos > offset_y+h:
                break
            draw_func = getattr(self, "draw_" + elist[idx].event_type)
            draw_func(elist[idx], ctx, offset_x, offset_y, w, h)

    def draw_call(self, entity, ctx, offset_x, offset_y, w, h):
        ctx.select_font_face(FONTNAME, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(FONTSIZE)
        ctx.move_to(len(entity.stack)*BAR_WIDTH + 20 - offset_x, entity.ypos - offset_y)
        ctx.set_source_rgb(*StrToColor(FONTCOLOR))
        ctx.show_text(entity.func_bane)



class SequenceData:
    def __init__(self):
        self.lifelines = []
    
    def get_lifeline(self, llid):
        if llid not in self.lifelines:
            self.lifelines[llid] = Lifeline(llid, 0)
        return self.lifelines[llid]
    
    def draw(self, ctx, offset_x, offset_y, w, h):
        for key, lifeline in self.lifelines.items():
            lifeline.draw(ctx, offset_x, offset_y, w, h)


    def add_data_line(self, line):
        cmd = shlex.split(line.strip())
        if not cmd:
            return
        if cmd[0] == 'CAL':
            self.get_thread(cmd[1]).put_call(cmd[3])
        if cmd[0] == 'RET':
            self.get_thread(cmd[1]).put_return()
        else:
            print "Unknown command: ", cmd[0]

    def read_file(self, filename):
        for line in open(filename, 'r'):
            self.add_data_line(line)
        self.ybase_increased()


