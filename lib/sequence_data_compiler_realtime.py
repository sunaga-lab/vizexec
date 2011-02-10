# -*- coding: utf-8 -*-

import figure_data
import shlex

sample_data = {
    "thread-1": [
        (100, "call", "MethodA"),
        (150, "call", "MethodB"),
        (200, "ret"),
        (300, "ret"),
    ],
    "thread-2": [
        (120, "call", "MethodA"),
        (150, "call", "MethodB"),
        (210, "ret"),
        (300, "ret"),
    ]
}



class SequenceCompiler:
    
    def __init__(self):
        self.EXECUTIONBAR_WIDTH = 6
        self.time_scale = 0.0
        self.comm_lines = {}
        self.comm_serial = 0
        self.open_comm = {}
        self.thread_name_map = {}
        self.threads = {}
        self.lifeline_x_offset = 30
        self.ybase = 10
        self.current_ybase = self.ybase

        
    def new_comm_serial_id(self):
        self.comm_serial += 1
        return self.comm_serial


    def set_data(self, data):
        self.data = data


    def check_thread(self, threadid):
        if threadid not in self.threads:
            self.put_new_thread(threadid)

    def put_new_thread(self, threadid):
        self.threads[threadid] = {
            "name": threadid,
            "lifeline": [],
            "xoffset": self.lifeline_x_offset,
            "yoffset": 0,
            "stack_box": [],
        }
        self.lifeline_x_offset += 200
        
        self.threads[threadid]["titlebox"] = self.fig.put(
            "box",
            text = threadid,
            pos = (self.threads[threadid]["xoffset"] - 10, self.current_ybase),
            size = (120, 26),
            autosize = True,
            bgcolor = "#FFFFFF",
            linecolor = "#000000",
            linewidth = 2.0
        )
        self.current_ybase += 30

    def calc_line_xpos(self, threadid, pos = "l"):
        tdic = self.threads[threadid]
        if pos == "l":
            pos_offset = 0
        elif pos == "c":
            pos_offset = self.EXECUTIONBAR_WIDTH / 2
        elif pos == "r":
            pos_offset = self.EXECUTIONBAR_WIDTH
        else:
            pos_offset = 0

        return tdic["xoffset"] + len(tdic["stack_box"]) * self.EXECUTIONBAR_WIDTH + pos_offset
        

    def put_call(self, time, threadid, funcname):
        tdic = self.threads[threadid]
        lb = self.calc_line_xpos(threadid)
        
        bar = self.fig.put(
            "box",
            pos = (lb, self.current_ybase),
            size = (self.EXECUTIONBAR_WIDTH, 20),
            bgcolor = "#FFFFFF",
            linecolor = "#000000",
            linewidth = 1.0
        )
        self.fig.put(
            "box",
            pos = (lb + self.EXECUTIONBAR_WIDTH + 2, self.current_ybase + 0),
            autosize = True,
            text = funcname,
            textalign = "lefttop",
            fontsize = 13
        )
        tdic["stack_box"].append(bar)
        self.current_ybase += 20

    def put_return(self, time, threadid):
        tdic = self.threads[threadid]
        if not tdic["stack_box"]:
            print "Error: over return"
            return
        
        target_bar = tdic["stack_box"].pop()
        target_bar.size = (target_bar.size[0], self.current_ybase - target_bar.pos[1])
        target_bar.recalc_bounding()
        self.current_ybase += 10

    def put_phase(self, time, threadid, funcname):
        self.put_return(time, threadid)
        self.put_call(time, threadid, funcname)

    def ybase_increased(self):
        for key, tdic in self.threads.items():
            for bar in tdic["stack_box"]:
                bar.size = (bar.size[0], self.current_ybase - bar.pos[1])
                bar.recalc_bounding()
    
    def change_threadname(self, threadid, name):
        self.threads[threadid]["titlebox"].text = name


    def put_mark(self, time, threadid, label):
        x = self.calc_line_xpos(threadid, "c")
        y = self.current_ybase + 10
        sz = 5
        x0 = x - sz
        y0 = y - sz
        x1 = x + sz
        y1 = y + sz
        
        common_params = {
            "linecolor": "#0000FF",
            "linewidth": 1.0,
            "dash": [],
        }
        self.fig.put(
            "line",
            src = (x0, y0),
            dst = (x1, y1),
            **common_params
        )
        self.fig.put(
            "line",
            src = (x1, y0),
            dst = (x0, y1),
            **common_params
        )

        self.fig.put(
            "box",
            pos = (x + 6, y-10),
            size = (100,20),
            text = label,
            textalign = "left",
            fontsize = 13
        )
        self.current_ybase += 20

    def put_event_mark(self, time, threadid, label):
        self.put_mark(time, threadid, label)
        
    def put_send(self, time, threadid, comm_id):
        self.open_comm[comm_id] = {
            "broad": False,
            "id": self.new_comm_serial_id(),
            "start_threadid": threadid,
            "start_pos": self.current_ybase,
        }
        # self.put_mark(time, threadid, comm_id)
        self.current_ybase += 0

    def put_recv(self, time, threadid, comm_id):
        self.put_comm_line(
            self.open_comm[comm_id]["start_threadid"],
            self.open_comm[comm_id]["start_pos"],
            threadid,
            self.current_ybase,
        )
        
        if not self.open_comm[comm_id]["broad"]:
            del self.open_comm[comm_id]
        self.current_ybase += 0

    def put_comm_line(self, start_tid, start_pos, end_tid, end_pos):
        x0 = (self.threads[start_tid]["xoffset"]
             + len(self.threads[start_tid]["stack_box"])*self.EXECUTIONBAR_WIDTH
             + self.EXECUTIONBAR_WIDTH/2)
        y0 = start_pos
        x1 = (self.threads[end_tid]["xoffset"]
             + len(self.threads[end_tid]["stack_box"])*self.EXECUTIONBAR_WIDTH
             + self.EXECUTIONBAR_WIDTH/2)
        y1 = end_pos
        self.fig.put(
            "line",
            src = (x0, y0),
            dst = (x1, y1),
            linecolor = "#0000FF",
            linewidth = 1.0,
            dash = [6,2]
       )


    def add_data_line(self, line):
        cmd = shlex.split(line.strip())
        if not cmd:
            return
        if cmd[0] in ('C','R','P'):
            self.check_thread(cmd[1])
            
            if cmd[0] == 'C':
                self.put_call(int(cmd[2]), cmd[1], cmd[3])
            if cmd[0] == 'R':
                self.put_return(int(cmd[2]), cmd[1])
            if cmd[0] == 'P':
                self.put_phase(int(cmd[2]), cmd[1], cmd[3])

        elif cmd[0] in ('S','V','B'):
            self.check_thread(cmd[1])
            if cmd[0] == 'S':
                self.put_send(int(cmd[2]), cmd[1], cmd[3])
            if cmd[0] == 'B':
                self.put_sendbroad(int(cmd[2]), cmd[1], cmd[3])
            if cmd[0] == 'V':
                self.put_recv(int(cmd[2]), cmd[1], cmd[3])

        elif cmd[0] == 'THREADNAME':
            self.change_threadname(cmd[1], cmd[2])

        elif cmd[0] == 'E':
            self.put_event_mark(int(cmd[2]), cmd[1], cmd[3])

        elif cmd[0] == '#':
            pass
        else:
            print "Unknown command: ", cmd[0]

    def read_file(self, filename):
        for line in open(filename, 'r'):
            self.add_data_line(line)
        self.ybase_increased()
