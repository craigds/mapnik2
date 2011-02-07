"""Mapnik classes to assist in creating printable maps

basic usage is along the lines of

import mapnik2

page = mapnik2.printing.PDFPrinter()
m = mapnik2.Map(100,100)
mapnik2.load_map(m, "my_xml_map_description", True)
m.zoom_all()
page.render_map(m,"my_output_file.pdf")

see the documentation of mapnik2.printing.PDFPrinter() for options

"""

from . import render, Map, Box2d, MemoryDatasource, Layer, Feature
import math
from foolscap.crypto import available

try:
    import cairo
    HAS_PYCAIRO_MODULE = True
except ImportError:
    HAS_PYCAIRO_MODULE = False

class centering:
    """Style of centering to use with the map, the default is constrained
    
    none: map will be placed flush with the margin/box in the top left corner
    constrained: map will be centered on the most constrained axis (for an portrait page
                 and a square map this will be horizontally)
    unconstrained: map will be centered on the unconstrained axis
    vertical:
    horizontal:
    both:
    """
    none=0
    constrained=1
    unconstrained=2
    vertical=3
    horizontal=4
    both=5

class pagesizes:
    """Some predefined page sizes custom sizes can also be passed
    a tuple of the page width and height in meters"""
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

"""size of a pt in meters"""
pt_size=0.0254/72.0

def m2pt(x):
    """convert distance from meters to points"""
    return x/pt_size

def pt2m(x):
    """convert distance from points to meters"""
    return x*pt_size

def m2in(x):
    """convert distance from meters to inches"""
    return x/0.0254

def m2px(x,resolution):
    """convert distance from meters to pixels at the given resolution in DPI/PPI"""
    return m2in(x)*resolution

class resolutions:
    """some predefined resolutions in DPI"""
    dpi72=72
    dpi150=150
    dpi300=300
    dpi600=600

def any_scale(scale):
    """Scale helper function that allows any scale"""
    return scale

_default_scale=[1,1.25,1.5,1.75,2,2.5,3,3.5,4,4.5,5,6,7.5,8,9,10]
def default_scale(scale):
    """Default scale helper, this rounds scale to a 'sensible' value"""
    factor = math.floor(math.log10(scale))
    norm = scale/(10**factor)
    
    for s in _default_scale:
        if norm <= s:
            return s*10**factor

class PDFPrinter:
    """Main class for creating PDF print outs, basically contruct an instance
    with appropriate options and then call render_map with your mapnik map
    """
    def __init__(self, pagesize=pagesizes.a4, 
                 margin=0.01, 
                 box=None,
                 percent_box=None,
                 scale=default_scale, 
                 resolution=resolutions.dpi72,
                 preserve_aspect=True,
                 centering=centering.constrained):
        """Creates a cairo surface and context to render a PDF with.
        
        pagesize: tuple of page size in meters, see predefined sizes in pagessizes class (default a4)
        margin: page margin in meters (default 0.01)
        box: box within the page to render the map into (will not render over margin). This should be 
             a Mapnik Box2d object. Default is the full page within the margin
        percent_box: as per box, but specified as a percent (0->1) of the full page size. If both box
                     and percent_box are specified percent_box will be used.
        scale: scale helper to use when rounding the map scale. This should be a function that
               takes a single float and returns a float which is at least as large as the value
               passed in. This is a 1:x scale.
        resolution: the resolution to render non vector elements at (in DPI), defaults to 72 DPI
        preserve_aspect: whether to preserve map aspect ratio. This defaults to True and it
                         is recommended you do not change it unless you know what you are doing
                         scales and so on will not work if this is False.
        centering: Centering rules for maps where the scale rounding has reduced the map size.
                   This should be a value from the centering class. The default is to center on the
                   maps constrained axis, typically this will be horizontal for portrait pages and
                   vertical for landscape pages.
        """
        self._pagesize = pagesize
        self._margin = margin
        self._box = box
        self._scale = scale
        self._resolution = resolution
        self._preserve_aspect = preserve_aspect
        self._centering = centering
        
        self._s = None
        
        self.map_box = None
        self.scale = None
        
        # don't both to round the scale if they are not preserving the aspect ratio
        if not preserve_aspect:
            self._scale = any_scale
        
        if percent_box:
            self._box = Box2d(percent_box[0]*pagesize[0],percent_box[1]*pagesize[1],
                         percent_box[2]*pagesize[0],percent_box[3]*pagesize[1])

        if not HAS_PYCAIRO_MODULE:
            raise Exception("PDF rendering only available when pycairo is available")
    
    def _get_render_area(self):
        """return a bounding box with the area of the page we are allowed to render out map to
        in page coordinates (i.e. meters)
        """
        # take off our page margins
        render_area = Box2d(self._margin,self._margin,self._pagesize[0]-self._margin,self._pagesize[1]-self._margin)
        
        #then if user specified a box to render get intersection with that
        if self._box:
            return render_area.intersect(self._box)
        
        return render_area

    def _get_render_area_size(self):
        """Get the width and height (in meters) of the area we can render the map to, returned as a tuple"""
        render_area = self._get_render_area()
        return (render_area.width(),render_area.height())

    def _is_h_contrained(self,m):
        """Test if the map size is constrained on the horizontal or vertical axes"""
        available_area = self._get_render_area_size()
        map_aspect = m.envelope().width()/m.envelope().height()
        page_aspect = available_area[0]/available_area[1]
        
        return map_aspect > page_aspect

    def _get_meta_info_corner(self,render_size,m):
        """Get the corner (in page coordinates) of a possibly
        sensible place to render metadata such as a legend or scale"""
        (x,y) = self._get_render_corner(render_size,m)
        if self._is_h_contrained(m):
            y += render_size[1]+0.005
            x = self._margin
        else:
            x += render_size[0]+0.005
            y = self._margin
            
        return (x,y)

    def _get_render_corner(self,render_size,m):
        """Get the corner of the box we should render our map into"""
        available_area = self._get_render_area()

        x=available_area[0]
        y=available_area[1]
        
        h_is_contrained = self._is_h_contrained(m)
        
        if (self._centering == centering.both or
            self._centering == centering.horizontal or
            (self._centering == centering.constrained and h_is_contrained) or
            (self._centering == centering.unconstrained and not h_is_contrained)):
            x+=(available_area.width()-render_size[0])/2

        if (self._centering == centering.both or
            self._centering == centering.vertical or
            (self._centering == centering.constrained and not h_is_contrained) or
            (self._centering == centering.unconstrained and h_is_contrained)):
            y+=(available_area.height()-render_size[1])/2
        return (x,y)
    
    def _get_map_pixel_size(self, width_page_m, height_page_m):
        """for a given map size in paper coordinates return a tuple of the map 'pixel' size we
        should create at the defined resolution"""
        return (int(m2px(width_page_m,self._resolution)), int(m2px(height_page_m,self._resolution)))
        
    def render_map(self,m, filename):
        """Render the given map to filename"""
        
        # work out the best scale to render out map at given the available space
        (eff_width,eff_height) = self._get_render_area_size()
        map_aspect = m.envelope().width()/m.envelope().height()
        page_aspect = eff_width/eff_height
        
        scalex=m.envelope().width()/eff_width
        scaley=m.envelope().height()/eff_height
        
        scale=max(scalex,scaley)

        rounded_mapscale=self._scale(scale)
        scalefactor = scale/rounded_mapscale
        mapw=eff_width*scalefactor
        maph=eff_height*scalefactor
        if self._preserve_aspect:
            if map_aspect > page_aspect:
                maph=mapw*(1/map_aspect)
            else:
                mapw=maph*map_aspect
        
        # set the map size so that raster elements render at the correct resolution
        m.resize(*self._get_map_pixel_size(mapw,maph))
        # calculate the translation for the map starting point
        (tx,ty) = self._get_render_corner((mapw,maph),m)
        
        # create our cairo surface and context and then render the map into it
        self._s = cairo.PDFSurface(filename, m2pt(self._pagesize[0]),m2pt(self._pagesize[1]))
        ctx=cairo.Context(self._s)
        ctx.save()
        ctx.translate(m2pt(tx),m2pt(ty))
        #cairo defaults to 72dpi
        ctx.scale(72.0/self._resolution,72.0/self._resolution)
        render(m, ctx)
        ctx.restore()
        
        self.scale = rounded_mapscale
        self.map_box = Box2d(tx,ty,tx+mapw,ty+maph)
    
    def render_legend(self,m, render_scale=False):
        if self._s:
            ctx=cairo.Context(self._s)

            (tx,ty) = self._get_meta_info_corner((self.map_box.width(),self.map_box.height()),m)
            ctx.translate(m2pt(tx),m2pt(ty))

            line = 1
            # dont report scale if we have warped the aspect ratio
            ctx.set_source_rgb(0.0, 0.0, 0.0)
            ctx.select_font_face("Georgia", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            ctx.set_font_size(10)
            if self._preserve_aspect and render_scale:
                ctx.move_to(0,line*10)
                ctx.show_text("SCALE 1:%d" % self.scale)
                line += 1
            
            ctx.set_font_size(6)
            ctx.move_to(0,(line-1)*10+6)
            line += 1
            ctx.show_text("SRS: " + m.srs)
        
            
            added_styles={}
            have_header = False
            for l in m.layers:
                print "Creating legend for: ", l.name
                for s in l.styles:
                    st = m.find_style(s)
                    for r in st.rules:
                        if added_styles.has_key((s,r.name)):
                            continue
                        for f in l.datasource.all_features():
                            if f.geometry:
                                if (not r.filter) or r.filter.evaluate(f) == '1':
                                    legend_feature = f
                                    break
                        else:
                            print "No valid geometry found for layer: ", l.name
                            continue
                        added_styles[(s,r.name)] = None
                        
                        if not have_header:
                            ctx.set_font_size(12)
                            ctx.move_to(0,line*12)
                            line += 1
                            ctx.show_text("LEGEND:")
                            have_header = True
                        
                        for sym in r.symbols:
                            try:
                                sym.avoid_edges=False
                            except:
                                print "**** Cant set avoid edges for rule", r.name
                        
                        legend_map_size = (int(m2pt(0.02)),int(m2pt(0.01)))
                        lemap=Map(*legend_map_size,srs=m.srs)
                        lemap.background = m.background
                        lemap.buffer_size=1000
                        lemap.append_style(s,st)

                        ds = MemoryDatasource()
                        if legend_feature.envelope().width() == 0:
                            ds.add_feature(Feature(legend_feature.id(),"POINT(0 0)",**legend_feature.attributes))
                            lemap.zoom_to_box(Box2d(-1,-1,1,1))
                            layer_srs = m.srs
                        else:
                            ds.add_feature(legend_feature)
                            layer_srs = l.srs

                        lelayer = Layer("LegendLayer",layer_srs)
                        lelayer.datasource = ds
                        lelayer.styles.append(s)
                        lemap.layers.append(lelayer)
                        
                        if legend_feature.envelope().width() != 0:
                            lemap.zoom_all()
                            lemap.zoom(1.1)
                            
                        ctx.save()
                        ctx.translate(0,line*12)
                        #extra save around map render as it sets up a clip box and doesn't clear it
                        ctx.save()
                        render(lemap, ctx)
                        ctx.restore()
                        
                        ctx.rectangle(0,0,*legend_map_size)
                        ctx.set_source_rgb(0.5,0.5,0.5)
                        ctx.set_line_width(1)
                        ctx.stroke()
                        ctx.restore()

                        ctx.move_to(m2pt(0.025),line*12+m2pt(0.01)/2+ 6)
                        if len(st.rules) == 1:
                            ctx.show_text("%s" % ( s, ))
                        else:
                            ctx.show_text("%s: %s" % ( s, r.name))


                        line += 2.5
        
