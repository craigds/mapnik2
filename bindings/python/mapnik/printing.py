"""Mapnik classes to assist in creating printable maps"""

from . import render, Map
import math
from foolscap.crypto import available

try:
    import cairo
    HAS_PYCAIRO_MODULE = True
except ImportError:
    HAS_PYCAIRO_MODULE = False

class centering:
    none=0
    constrained=1
    unconstrained=2
    vertical=3
    horizontal=4
    both=5

class pagesizes:
    a0 = (0.841000,1.189000)
    a0l = (1.189000,0.841000)
    b0 = (1.000000,1.414000)
    b0l = (1.414000,1.000000)
    c0 = (0.917000,1.297000)
    c0l = (1.297000,0.917000)
    a1 = (0.594000,0.841000)
    a1l = (0.841000,0.594000)
    b1 = (0.707000,1.000000)
    b1l = (1.000000,0.707000)
    c1 = (0.648000,0.917000)
    c1l = (0.917000,0.648000)
    a2 = (0.420000,0.594000)
    a2l = (0.594000,0.420000)
    b2 = (0.500000,0.707000)
    b2l = (0.707000,0.500000)
    c2 = (0.458000,0.648000)
    c2l = (0.648000,0.458000)
    a3 = (0.297000,0.420000)
    a3l = (0.420000,0.297000)
    b3 = (0.353000,0.500000)
    b3l = (0.500000,0.353000)
    c3 = (0.324000,0.458000)
    c3l = (0.458000,0.324000)
    a4 = (0.210000,0.297000)
    a4l = (0.297000,0.210000)
    b4 = (0.250000,0.353000)
    b4l = (0.353000,0.250000)
    c4 = (0.229000,0.324000)
    c4l = (0.324000,0.229000)
    a5 = (0.148000,0.210000)
    a5l = (0.210000,0.148000)
    b5 = (0.176000,0.250000)
    b5l = (0.250000,0.176000)
    c5 = (0.162000,0.229000)
    c5l = (0.229000,0.162000)
    a6 = (0.105000,0.148000)
    a6l = (0.148000,0.105000)
    b6 = (0.125000,0.176000)
    b6l = (0.176000,0.125000)
    c6 = (0.114000,0.162000)
    c6l = (0.162000,0.114000)
    a7 = (0.074000,0.105000)
    a7l = (0.105000,0.074000)
    b7 = (0.088000,0.125000)
    b7l = (0.125000,0.088000)
    c7 = (0.081000,0.114000)
    c7l = (0.114000,0.081000)
    a8 = (0.052000,0.074000)
    a8l = (0.074000,0.052000)
    b8 = (0.062000,0.088000)
    b8l = (0.088000,0.062000)
    c8 = (0.057000,0.081000)
    c8l = (0.081000,0.057000)
    a9 = (0.037000,0.052000)
    a9l = (0.052000,0.037000)
    b9 = (0.044000,0.062000)
    b9l = (0.062000,0.044000)
    c9 = (0.040000,0.057000)
    c9l = (0.057000,0.040000)
    a10 = (0.026000,0.037000)
    a10l = (0.037000,0.026000)
    b10 = (0.031000,0.044000)
    b10l = (0.044000,0.031000)
    c10 = (0.028000,0.040000)
    c10l = (0.040000,0.028000)
    letter = (0.216,0.279)
    letterl = (0.279,0.216)
    legal = (0.216,0.356)
    legall = (0.356,0.216)

    
pt_size=0.0254/72.0

def m2pt(x):
    return x/pt_size

def pt2m(x):
    return x*pt_size

def m2in(x):
    return x/0.0254

def m2px(x,resolution):
    return m2in(x)*resolution

class resolutions:
    dpi72=72
    dpi150=150
    dpi300=300
    dpi600=600

def any_scale(scale):
    return scale

_default_scale=[1,1.25,1.5,1.75,2,2.5,3,3.5,4,4.5,5,6,7.5,8,9,10]
def default_scale(scale):
    factor = math.floor(math.log10(scale))
    norm = scale/(10**factor)
    
    for s in _default_scale:
        if norm <= s:
            return s*10**factor

class PDFPrinter:
    def __init__(self, pagesize=pagesizes.a4, 
                 margin=0.02, 
                 box=None, 
                 scale=default_scale, 
                 resolution=resolutions.dpi72,
                 preserve_aspect=True,
                 centering=centering.constrained):
        self._pagesize = pagesize
        self._margin = margin
        self._box = box
        self._scale = scale
        self._resolution = resolution
        self._preserve_aspect = preserve_aspect
        self._centering = centering
        
        if not preserve_aspect:
            self._scale = any_scale

        if not HAS_PYCAIRO_MODULE:
            raise Exception("PDF rendering only available when pycairo is available")
    
    def _get_render_area(self):
        # take off our page margins
        eff_width = self._pagesize[0]-2*self._margin
        eff_height = self._pagesize[1]-2*self._margin
        
        #then if user specified a box to render get intersection with that
        
        
        return (eff_width,eff_height)

    def _is_h_contrained(self,m):
        available_area = self._get_render_area()
        map_aspect = m.envelope().width()/m.envelope().height()
        page_aspect = available_area[0]/available_area[1]
        
        return map_aspect > page_aspect

    def _get_meta_info_corner(self,render_size,m):
        (x,y) = self._get_render_corner(render_size,m)
        if self._is_h_contrained(m):
            y += render_size[1]
        else:
            x += render_size[0]
            
        return (x,y)

    def _get_render_corner(self,render_size,m):
        available_area = self._get_render_area()

        x=self._margin;
        y=self._margin;
        
        # TODO: adjust for render box if provided
        
        h_is_contrained = self._is_h_contrained(m)
        
        if (self._centering == centering.both or
            self._centering == centering.horizontal or
            (self._centering == centering.constrained and h_is_contrained) or
            (self._centering == centering.unconstrained and not h_is_contrained)):
            x+=(available_area[0]-render_size[0])/2

        if (self._centering == centering.both or
            self._centering == centering.vertical or
            (self._centering == centering.constrained and not h_is_contrained) or
            (self._centering == centering.unconstrained and h_is_contrained)):
            y+=(available_area[1]-render_size[1])/2
        return (x,y)
    
    def _get_map_pixel_size(self, width_page_m, height_page_m):
        return (int(m2px(width_page_m,self._resolution)), int(m2px(height_page_m,self._resolution)))
        
    def render_map(self,m, filename):
        
        # work out the best scale to render out map at given the available space
        (eff_width,eff_height) = self._get_render_area()
        map_aspect = m.envelope().width()/m.envelope().height()
        page_aspect = eff_width/eff_height
        
        scalex=m.scale()*m.width/eff_width
        scaley=m.scale()*m.height/eff_height
        
        scale=max(scalex,scaley)

        rounded_mapscale=self._scale(scale)
        scalefactor = scale/rounded_mapscale
        mapw=eff_width*scalefactor
        maph=eff_height*scalefactor
        if self._preserve_aspect:
            if map_aspect > page_aspect:
                maph=mapw
            else:
                mapw=maph
            
        m.resize(*self._get_map_pixel_size(mapw,maph))
        
        (tx,ty) = self._get_render_corner((mapw,maph),m)
        
        s = cairo.PDFSurface(filename, m2pt(self._pagesize[0]),m2pt(self._pagesize[1]))
        ctx=cairo.Context(s)
        ctx.save()
        ctx.translate(m2pt(tx),m2pt(ty))
        #cairo defaults to 72dpi
        ctx.scale(72.0/self._resolution,72.0/self._resolution)
        render(m, ctx)
        ctx.restore()
        
        # dont report scale if we have warped the aspect ratio
        if self._preserve_aspect:
            (tx,ty) = self._get_meta_info_corner((mapw,maph),m)
            ctx.translate(m2pt(tx),m2pt(ty))

            ctx.set_source_rgb(0.0, 0.0, 0.0)
            ctx.select_font_face("Georgia", cairo.FONT_SLANT_NORMAL,
            cairo.FONT_WEIGHT_BOLD)
            ctx.set_font_size(12)
            ctx.move_to(0,12)
            ctx.show_text("SCALE 1:%d" % rounded_mapscale)
        
