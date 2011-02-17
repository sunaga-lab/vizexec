# -*- coding: utf-8 -*-

import bisect
import shlex
import gtk
import gtk.glade
import cairo
import traceback
from subprocess import list2cmdline

def StrToColor(s):
    col = gtk.gdk.Color(s)
    return (col.red / 65535.0, col.green / 65535.0, col.blue / 65535.0)


def len_point_to_line2(px, py, x0, y0, x1, y1):
    dx = x1 - x0
    dy = y1 - y0
    a = dx*dx + dy*dy
    if a == 0.0:
        return (x0-px)*(x0-px) + (y0-py)*(y0-py)
    b = dx*(x0-px) + dy*(y0-py)
    t =  -(b/a)
    t = max(0.0, t)
    t = min(1.0, t)
    x = t*dx + x0
    y = t*dy + y0
    return (x-px)*(x-px) + (y-py)*(y-py)


class YPosComparable:
    def __init__(self, ypos):
        self.ypos = ypos

    def __lt__(self, other):
        return self.ypos < other.ypos
        
    def __le__(self, other):
        return self.ypos <= other.ypos


    def __gt__(self, other):
        return self.ypos > other.ypos

    def __ge__(self, other):
        return self.ypos >= other.ypos


class LifelineEntity(YPosComparable):
    def __init__(self, lifeline, ypos, event_type, stack):
        YPosComparable.__init__(self, ypos)
        self.lifeline = lifeline
        self.event_type = event_type
        self.stack = stack
        self.name = ""
        self.info = []

    def get_name(self):
        return self.name

    def __str__(self):
        return self.get_name()

    def add_info(self, line):
        self.info.append(line.rstrip())

    def get_info_text(self):
        return "[{t}{name}]\ntpos: {tpos}\n{info}".format(
            t = self.event_type,
            tpos = self.ypos,
            name = (": " + self.get_name()) if self.get_name() else "",
            info = '\n'.join(self.info)
        )
        
    def shift_ypos(self, new_ypos):
        self.lifeline.shift_ypos(self.ypos, new_ypos)


class StackFrame:
    def __init__(self, func_name):
        self.func_name = func_name
        self.call_entity = None
        self.return_entity = None

class Communication:
    def __init__(self):
        self.comm_id = ""
        self.send_entity = None
        self.recv_entity = None
    
    def is_complete(self):
        if not self.send_entity or not self.recv_entity:
            return False
        return True
    
    def __str__(self):
        return "[comm:{id} {src} -> {dst} ]".format(
            id = self.comm_id,
            src = str(self.send_entity),
            dst = str(self.recv_entity),
        )

    def get_name(self):
        return self.__str__()

    def get_info_text(self):
        return self.send_entity.get_info_text() + "\n\n--- TO ---\n\n" + self.recv_entity.get_info_text()


BAR_WIDTH = 5

SELECTED_BGCOLOR = '#0000FF'
SELECTED_ALPHA = 0.2

DEFAULT_PARAMS = {
    'bgcolor': None,
    'fontname': 'Serif',
    'fontsize': 10,
    'fontcolor': '#000000',
    'textalign': 'center',
    'text': None,
    'linecolor': None,
    'linewidth': 1.0,
    'dash': [],
    'associated': None,
    'alpha': None,
    'linealpha': None,
}

class ParamClass:
    def __init__(self, d):
        self.d = {}
        self.d.update(DEFAULT_PARAMS)
        self.d.update(d)
    
    def __getattr__(self, name):
        return self.d[name]

    def __setattr__(self, name, value):
        if name == 'd':
            self.__dict__['d'] = value
        else:
            self.__dict__['d'][name] = value

    def __hasattr__(self, name):
        return name in self.d

class Lifeline:
    def __init__(self, seqdata, lifeline_id, start_ypos):
        self.seqdata = seqdata
        self.lifeline_id = lifeline_id
        self.entity_list = []
        self.start_ypos = start_ypos
        self.end_ypos = None
        self.__current_ypos = start_ypos
        self.current_stack = []
        self.lifeline_name = str(lifeline_id)
        self.terminated = False
        self.lane = 0

    def get_info_text(self):
        return "[Lifeline: {name}]\nid = {lid}".format(
            name = self.lifeline_name,
            lid = self.lifeline_id
        )

    def get_current_ypos(self):
        if self.seqdata.synchronized:
            self.__current_ypos = self.seqdata.current_ypos
        return self.__current_ypos

    def set_current_ypos_least(self, ypos):
        self.__current_ypos = max(self.get_current_ypos(), ypos)
        if self.seqdata.synchronized:
            self.seqdata.current_ypos = self.__current_ypos

    def get_id(self):
        return self.lifeline_id

    def get_display_name(self):
        return self.lifeline_name

    def new_entity(self, event_type, add_ypos = 20):
        entity = LifelineEntity(self, self.get_current_ypos(), event_type, self.current_stack)
        self.entity_list.append(entity)
        self.set_current_ypos_least(self.get_current_ypos() + add_ypos)
        return entity

    def stack_push(self, name):
        if self.seqdata.synchronized:
            self.current_ypos = self.seqdata.current_ypos
        self.current_stack = self.current_stack[:]
        frm = StackFrame(name)
        self.current_stack.append(frm)
        return frm

    def stack_pop(self):
        self.current_stack = self.current_stack[:]
        self.current_stack.pop()

    def put_thread_name(self, name):
        self.lifeline_name = name

    def bar_xpos(self, stk, align = "l"):
        if align == "c":
            align_int = BAR_WIDTH / 2
        elif align == "r":
            align_int = BAR_WIDTH
        else:
            align_int = 0
        return len(stk)*BAR_WIDTH + align_int + 20 + self.lane * 150

    def parse_line_flags(self, p):
        ctx = self.ctx
        if p.linealpha is not None:
            ctx.set_source_rgba(*StrToColor(p.linecolor) + (p.linealpha, ))
        else:
            ctx.set_source_rgb(*StrToColor(p.linecolor))

        ctx.set_line_width(p.linewidth)
        if p.dash:
            ctx.set_dash(p.dash, 0)
        else:
            ctx.set_dash([], 0)


    def parse_fill_flags(self, p):
        ctx = self.ctx
        if p.alpha is not None:
            ctx.set_source_rgba(*StrToColor(p.bgcolor) + (p.alpha, ))
        else:
            ctx.set_source_rgb(*StrToColor(p.bgcolor))

    def draw_line(self, **prms):
        p = ParamClass(prms)
        if self.only_check:
            if len_point_to_line2(*(self.seqdata.selected_pos + p.src + p.dest)) < 16.0:
                self.seqdata.selected_object = p.associated
            return
        
        if p.associated and self.seqdata.selected_object == p.associated:
            self.draw_line(
                associated = None,
                src = p.src,
                dest = p.dest,
                linewidth = 8.0,
                linealpha = SELECTED_ALPHA,
                linecolor = SELECTED_BGCOLOR,
            )
            
        self.ctx.move_to(p.src[0], p.src[1])
        self.ctx.line_to(p.dest[0], p.dest[1])
        self.parse_line_flags(p)
        self.ctx.stroke()


    def draw_box(self, **prms):
        p = ParamClass(prms)
        ctx = self.ctx
        x0 = p.pos[0]
        y0 = p.pos[1]
        xs = p.size[0]
        ys = p.size[1]
        
        if self.only_check:
            if ( self.seqdata.selected_pos and
                x0 < self.seqdata.selected_pos[0] and y0 < self.seqdata.selected_pos[1] and
                self.seqdata.selected_pos[0] < x0+xs and self.seqdata.selected_pos[1] < y0+ys):
                    self.seqdata.selected_object = p.associated
            return
                
        if p.associated and self.seqdata.selected_object == p.associated:
            p.bgcolor = SELECTED_BGCOLOR
            p.alpha = SELECTED_ALPHA

        if p.bgcolor is not None:
            ctx.rectangle(x0,y0,xs,ys)
            self.parse_fill_flags(p)
            ctx.fill()

        if p.linecolor is not None:
            ctx.rectangle(x0,y0,xs,ys)
            self.parse_line_flags(p)
            ctx.stroke()

        if p.text is not None:
            ctx.select_font_face(p.fontname, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(p.fontsize)
            
            (x_bearing, y_bearing, width, height, x_advance, y_advance) = ctx.text_extents(p.text)
            
            if p.textalign == "center":
                ctx.move_to(x0 + (xs - width)/2 , y0 + (ys + height)/2)
            elif p.textalign == "left":
                ctx.move_to(x0, y0 + (ys + height)/2)
            elif p.textalign == "lefttop":
                ctx.move_to(x0, y0 + height)
            else:
                ctx.move_to(x0 + (xx - width)/2 , y0 + (ys + height)/2)
            ctx.set_source_rgb(*StrToColor(p.fontcolor))
            ctx.show_text(p.text)


    def draw_mark(self, stk, ypos, label, associated):
        x = self.bar_xpos(stk, "c") - self.x
        y = ypos - self.y + 10
        sz = 5
        x0 = x - sz
        y0 = y - sz
        x1 = x + sz
        y1 = y + sz
        
        common_params = {
            "linecolor": "#FF0000",
            "linewidth": 1.0,
            "dash": [],
        }
        self.draw_line(
            src = (x0, y0),
            dest = (x1, y1),
            **common_params
        )
        self.draw_line(
            src = (x1, y0),
            dest = (x0, y1),
            associated = associated,
            **common_params
        )

        self.draw_box(
            pos = (x + 6, y - 10),
            size = (100,20),
            text = label,
            textalign = "left",
            linecolor = None,
            associated = associated,
        )

    def shift_ypos(self, ypos, new_ypos):
        idx = bisect.bisect_left(self.entity_list, YPosComparable(ypos))
        
        biggest_ypos = 0
        for i in range(idx, len(self.entity_list)):
            self.entity_list[i].ypos += new_ypos - ypos
            biggest_ypos = max(self.entity_list[i].ypos, biggest_ypos)


    def draw(self, ctx, offset_x, offset_y, w, h, only_check = False):
        self.ctx = ctx
        self.x = offset_x
        self.y = offset_y
        self.w = w
        self.h = h
        self.only_check = only_check

        elist = self.entity_list
        idx = bisect.bisect_left(elist, YPosComparable(self.y)) - 1
        if idx == -1:
            idx = 0

        if elist:
            self.last_stack = elist[max(idx-1, 0)].stack
        else:
            self.last_stack = []
            
        stk = self.last_stack[:]
        while stk:
            self.draw_call_base(stk)
            stk.pop()
            
        while True:
            if idx >= len(elist) or elist[idx].ypos > self.y + self.h:
                break
            draw_func = getattr(self, "draw_" + elist[idx].event_type)
            draw_func(elist[idx])
            self.last_stack = elist[idx].stack
            idx += 1
        self.draw_all_return()

        underlabel_ypos = min(self.y + h - 40, self.end_ypos if self.end_ypos else self.y + h - 40)
        self.draw_box(
            text = self.get_display_name(),
            textalign = 'center',
            linecolor = None,
            bgcolor = '#FFFFFF',
            alpha = 0.8,
            pos = (self.bar_xpos([], "r") - 30 - self.x, underlabel_ypos - self.y),
            size = (120, 20),
            associated = self,
        )
        

    def draw_comm(self, comm):
        if not comm.is_complete():
            return
        ctx = self.ctx
        self.draw_line(
            src = (
                    comm.send_entity.lifeline.bar_xpos(comm.send_entity.stack, "c") + 2 - self.x, 
                    comm.send_entity.ypos - self.y
                ),
            dest = (
                    comm.recv_entity.lifeline.bar_xpos(comm.recv_entity.stack, "c") + 2 - self.x,
                    comm.recv_entity.ypos - self.y
                ),
            linewidth = 1.0,
            linecolor = '#0000FF',
            dash = [6,2],
            associated = comm,
        )

    def draw_all_return(self):
        pass

    def put_call(self, func_name):
        frm = self.stack_push(func_name)
        entity = self.new_entity("call")
        entity.func_name = func_name
        entity.name = func_name
        frm.call_entity = entity
        return entity

    def draw_call(self, entity):
        ctx = self.ctx
        self.draw_box(
            text = entity.func_name,
            textalign = 'left',
            linecolor = None,
            bgcolor = None,
            pos = (self.bar_xpos(entity.stack, "r") + 2 - self.x, entity.ypos - self.y),
            size = (100, 20),
            associated = entity,
        )

        x0 = self.bar_xpos(entity.stack)
        y0 = entity.ypos - self.y
        y1 = entity.stack[-1].return_entity.ypos - self.y if entity.stack[-1].return_entity else self.h + 10
        w = BAR_WIDTH
        h = y1 - y0
        
        self.draw_box(
            pos = (x0 - self.x, y0),
            size = (w,h),
            linecolor = '#000000',
            linewidth = 1.0,
            associated = entity.stack[-1].call_entity,
        )

    def draw_call_base(self, stk):
        x0 = self.bar_xpos(stk)
        y0 = -2
        y1 = stk[-1].return_entity.ypos - self.y if stk[-1].return_entity else self.h
        w = BAR_WIDTH
        h = y1 - y0
        
        self.draw_box(
            pos = (x0 - self.x, y0),
            size = (w,h),
            linecolor = '#000000',
            linewidth = 1.0,
            associated = stk[-1].call_entity,
        )

    def put_return(self):
        if not self.current_stack:
            return None
        frm = self.current_stack[-1]
        self.stack_pop()
        entity = self.new_entity("return")
        frm.return_entity = entity
        return entity

    def draw_return(self, entity):
        pass

    def put_phase(self, phase_name):
        entity = self.new_entity("phase")
        entity.func_name = phase_name
        entity.name = phase_name
        return entity

    def draw_phase(self, entity):
        x = self.bar_xpos(entity.stack, "c") - self.x
        y = entity.ypos - self.y + 10
        
        self.draw_box(
            pos = (x + 6, y - 10),
            size = (100,20),
            text = entity.func_name,
            textalign = "left",
            linecolor = None,
            associated = entity,
        )

    def put_send(self, comm_obj):
        entity = self.new_entity("send", 5)
        entity.comm = comm_obj
        return entity

    def draw_send(self, entity):
        self.draw_comm(entity.comm)

    def put_recv(self, comm_obj):
        entity = self.new_entity("recv", 5)
        entity.comm = comm_obj
        return entity

    def draw_recv(self, entity):
        self.draw_comm(entity.comm)

    def put_lifeline_start(self):
        entity = self.new_entity("lifeline_start", 30)
        return entity

    def draw_lifeline_start(self, entity):
        ctx = self.ctx
        self.draw_box(
            text = self.get_display_name(),
            textalign = 'center',
            linecolor = '#000000',
            bgcolor = '#FFFEDD',
            pos = (self.bar_xpos(entity.stack, "r") - 40 - self.x, entity.ypos - self.y),
            size = (120, 30),
            associated = self,
        )


    def put_event(self, label):
        entity = self.new_entity("event", 20)
        entity.label = label
        entity.name = label
        return entity

    def draw_event(self, entity):
        self.draw_mark(entity.stack, entity.ypos, entity.label, entity)

    def put_terminate(self):
        if self.end_ypos is not None:
            return        
        entity = self.new_entity("terminate", 20)

        while self.current_stack:
            frm = self.current_stack[-1]
            self.stack_pop()
            frm.return_entity = entity

        if self.seqdata.synchronized:
            self.current_ypos = self.seqdata.current_ypos
        self.end_ypos = self.current_ypos
        self.terminated = True
        return entity


    def draw_terminate(self, entity):
        self.draw_mark([0], entity.ypos, "Terminate", None)

    def put_info(self, infoline):
        last_entity = self.entity_list[-1]
        last_entity.add_info(infoline)




class SequenceData:
    def __init__(self):
        self.lifelines = {}
        self.used_lane = set([])
        self.max_lane = 0
        self.current_ypos = 50
        self.synchronized = True
        self.open_sending = {}
        self.open_receiving = {}
        self.selected_pos = None
        self.selected_object = None
        
        self.raw_log = []

    def search_unused_lane(self):
        for i in range(1024):
            if i not in self.used_lane:
                self.used_lane.add(i)
                self.max_lane = max(self.max_lane, i)
                return i
        raise "Too many lanes"

    def get_lifeline(self, llid):
        if llid not in self.lifelines:
            self.lifelines[llid] = Lifeline(self, llid, self.current_ypos)
            self.lifelines[llid].lane = self.search_unused_lane()
            self.lifelines[llid].put_lifeline_start()
            
        return self.lifelines[llid]
    
    def draw(self, ctx, offset_x, offset_y, w, h, only_check = False):
        for key, lifeline in self.lifelines.items():
            if lifeline.start_ypos > offset_y + h:
                continue
            if lifeline.end_ypos and offset_y > lifeline.end_ypos:
                continue
            lifeline.draw(ctx, offset_x - 50, offset_y, w, h, only_check)

    def keep_raw_log(self, line = "", arr = None):
        self.raw_log.append(line + (list2cmdline(arr) if arr else ""))
        
    def save_log_to(self, fn):
        f = open(fn, 'w')
        for rlog in self.raw_log:
            f.write(rlog + "\n")
        f.close()
    
    def sync_ypos(self):
        if self.synchronized:
            return
        now_ypos = self.current_ypos
        for key, ll in self.lifelines.items():
            now_ypos = max(now_ypos, ll.get_current_ypos())

        for key, ll in self.lifelines.items():
            ll.set_current_ypos_least(now_ypos)
        self.current_ypos = now_ypos
        print "Sync:", self.current_ypos    
            
    def add_data_line(self, line, th_grp = "d"):
        cmd = shlex.split(line.strip())
        if not cmd:
            return
        elif cmd[0] == '#':
            self.keep_raw_log(line = line.strip())
            return
        
        if len(cmd) >= 2 and cmd[1] not in ("", "-"):
            lifeline = self.get_lifeline(th_grp + "/" + cmd[1])
            cmd[1] = lifeline.get_id()
            if lifeline.terminated:
                print "Thread", lifeline.get_id(), "already terminated command: ", cmd[0]
                self.keep_raw_log(arr = cmd)
                return
        else:
            print "Incomplete command: ", cmd[0]
            self.keep_raw_log(line = line)
            return

        if cmd[0] == 'CAL' and len(cmd) >= 4:
            lifeline.put_call(cmd[3])
        elif cmd[0] == 'PHS' and len(cmd) >= 4:
            lifeline.put_phase(cmd[3])
        elif cmd[0] == 'RET' and len(cmd) >= 3:
            lifeline.put_return()
        elif cmd[0] == 'TNM' and len(cmd) >= 3:
            lifeline.put_thread_name(cmd[2])
        elif cmd[0] == 'SND' and len(cmd) >= 4:
            if cmd[3] in self.open_receiving:
                comm = self.open_receiving[cmd[3]]
                del self.open_receiving[cmd[3]]
                # comm.recv_entity.shift_ypos(lifeline.get_current_ypos() + 40)
            else:
                comm = Communication()
                self.open_sending[cmd[3]] = comm
            comm.send_entity = lifeline.put_send(comm)
        elif cmd[0] == 'RCV' and len(cmd) >= 4:
            if cmd[3] in self.open_sending:
                comm = self.open_sending[cmd[3]]
                del self.open_sending[cmd[3]]
            else:
                comm = Communication()
                self.open_receiving[cmd[3]] = comm
            comm.recv_entity = lifeline.put_recv(comm)
        elif cmd[0] == 'EVT' and len(cmd) >= 4:
            lifeline.put_event(cmd[3])

        elif cmd[0] == 'INF' and len(cmd) >= 3:
            lifeline.put_info(cmd[2])

        elif cmd[0] == 'TRM' and len(cmd) >= 1:
            lifeline.put_terminate()
            self.used_lane.remove(lifeline.lane)
        else:
            print "Invalid command: ", cmd[0]

        self.keep_raw_log(arr = cmd)

    def terminated_lifeline_group(self, group):
        for key in self.lifelines:
            if key.startswith(group):
                if not self.lifelines[key].terminated:
                    self.lifelines[key].put_terminate()
                    self.used_lane.remove(self.lifelines[key].lane)
                    self.keep_raw_log(arr = ['TRM', key])

    def read_file(self, filename):
        for line in open(filename, 'r'):
            self.add_data_line(line)

    def get_width(self):
        return self.max_lane * 150 + 300

    def get_height(self):
        return self.current_ypos + 10
