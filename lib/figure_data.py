# -*- coding: utf-8 -*-

import gtk
import gtk.glade
import cairo
import traceback


def StrToColor(s):
    col = gtk.gdk.Color(s)
    return (col.red / 65535.0, col.green / 65535.0, col.blue / 65535.0)

class FigureNode:
    def __init__(self):
        self.name = ""
        self.bounding_box = [200,200,300,300]
        self.priority = 0.0
        self.pos = (200,200)
        self.size = (50,20)
        self.dash = None

    def draw(self, ctx, offset_x, offset_y):
        self.draw_custom(
            ctx, offset_x, offset_y
        )
        
    def draw_custom(self, ctx, offset_x, offset_y):
        pass
        

    def get_node_in_rect(self, x0, y0, x1, y1):
        return

    def set_param(self, key, value):
        setattr(self, key, value)

    def recalc_bounding(self):
        self.bounding_box[0] = self.pos[0]
        self.bounding_box[1] = self.pos[1]
        self.bounding_box[2] = self.pos[0] + self.size[0]
        self.bounding_box[3] = self.pos[1] + self.size[1]

    def set_param_from_dict(self, dic):
        for key, value in dic.items():
            self.set_param(key, value)

    def parse_line_flags(self, ctx):
        ctx.set_source_rgb(*StrToColor(self.linecolor))
        ctx.set_line_width(self.linewidth)
        if self.dash:
            ctx.set_dash(self.dash, 0)
        else:
            ctx.set_dash([], 0)


class BoxNode(FigureNode):
    def __init__(self):
        FigureNode.__init__(self)
        self.name = "box"
        self.autosize = False
        self.linecolor = None
        self.linewidth = 1.0
        self.bgcolor = None
        self.text = None
        self.textalign = "center"
        self.fontname = "Serif"
        self.fontcolor = "#000000"
        self.fontsize = 14
        
    def draw_custom(self, ctx, offset_x, offset_y):
        x0 = self.pos[0] - offset_x
        y0 = self.pos[1] - offset_y
        xs = self.size[0]
        ys = self.size[1]

        if self.bgcolor is not None:
            ctx.rectangle(x0, y0, self.size[0], self.size[1])
            ctx.set_source_rgb(*StrToColor(self.bgcolor))
            ctx.fill()

        if self.linecolor is not None:
            ctx.rectangle(x0, y0, self.size[0], self.size[1])
            self.parse_line_flags(ctx)
            ctx.stroke()

        if self.text is not None:
            ctx.select_font_face(self.fontname, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(self.fontsize)
            
            (x_bearing, y_bearing, width, height, x_advance, y_advance) = ctx.text_extents(self.text)
            
            if self.textalign == "center":
                ctx.move_to(x0 + (xs - width)/2 , y0 + (ys + height)/2)
            elif self.textalign == "left":
                ctx.move_to(x0, y0 + (ys + height)/2)
            elif self.textalign == "lefttop":
                ctx.move_to(x0, y0 + height)
            else:
                ctx.move_to(x0 + (xx - width)/2 , y0 + (ys + height)/2)
            ctx.set_source_rgb(*StrToColor(self.fontcolor))
            ctx.show_text(self.text)


class LineNode(FigureNode):
    def __init__(self):
        FigureNode.__init__(self)
        self.name = "line"
        self.linecolor = '#000000'
        self.linewidth = 1.0
        self.dash = None

    def recalc_bounding(self):
        self.bounding_box[0] = min(self.src[0], self.dst[0])
        self.bounding_box[1] = min(self.src[1], self.dst[1])
        self.bounding_box[2] = max(self.src[0], self.dst[0])
        self.bounding_box[3] = max(self.src[1], self.dst[1])

    def draw_custom(self, ctx, offset_x, offset_y):
        ctx.move_to(self.src[0] - offset_x, self.src[1] - offset_y)
        ctx.line_to(self.dst[0] - offset_x, self.dst[1] - offset_y)
        self.parse_line_flags(ctx)
        ctx.stroke()


def CreateNode(kind, **kwargs):
    if kind == "":
        return None
    elif kind == "box":
        node = BoxNode()
    elif kind == "line":
        node = LineNode()
    else:
        raise "Node type error"
    
    node.set_param_from_dict(kwargs)
    node.recalc_bounding()
    return node

class FigureData:
    def __init__(self):
        self.nodes = []
        self.width = 100
        self.height = 100
        self.name = "figure"
        self.text = ""

    def get_node_in_rect(self, x0,y0,x1,y1):
        for node in self.nodes:
            nx0 = node.bounding_box[0]
            ny0 = node.bounding_box[1]
            nx1 = node.bounding_box[2]
            ny1 = node.bounding_box[3]
            
            if (nx0 < x1 and ny0 < y1) and (x0 < nx1 and y0 < ny1):
                yield node
        return
            
        
    def put(self, kind, **args):
        node = CreateNode(kind, **args)
        self.put_node(node)
        return node

    def put_node(self, node):
        self.nodes.append(node)
        if node.bounding_box[2] > self.width:
            self.width = node.bounding_box[2]
        if node.bounding_box[3] > self.height:
            self.height = node.bounding_box[3]


    def get_height(self):
        return self.height

    def get_width(self):
        return self.width
