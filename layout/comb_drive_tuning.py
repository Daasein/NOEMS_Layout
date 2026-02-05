import gdsfactory as gf
from blocks import *

from gdsfactory.generic_tech import get_generic_pdk
from gdsfactory.typings import Layer
from gdsfactory.technology import (
    LayerMap,
)
generic_pdk = get_generic_pdk()
class NEOMS_LayerMap(LayerMap):
    WG: Layer = (1, 0)
    DEEP_ETCH: Layer = (3, 6)
    SHALLOW_ETCH: Layer = (2, 6)
    ALD_CORE: Layer = (5, 0)
    ALD_ETCH_EBL: Layer = (3, 8)
    ALD_ETCH_PL: Layer = (3, 10)
    DEEP_ETCH_EBL: Layer = (10,0)
    DEEP_ETCH_PL: Layer = (9,0)
    PROTECTION_PL: Layer = (11,0)
    MTOP: Layer = (12, 24)
    PADDING: Layer = (67,0)
    SLAB150: Layer = (2, 0)
    FLOORPLAN: Layer = getattr(generic_pdk.layers, "FLOORPLAN")
    MARKER: Layer = (66, 0)
pdk1 = gf.Pdk(
    name="tunable_noems_pdk",
    layers=NEOMS_LayerMap,
    cross_sections=generic_pdk.cross_sections,
    layer_views=generic_pdk.layer_views,
    cells=generic_pdk.cells,
)
pdk1.activate()


def metal_wire(
    core_width: float,
    wire_width: float,
    mask_offset: float,
    deep_etch_layer: str = "DEEP_ETCH",
):
    wire_sec = gf.Section(
        width=wire_width,
        offset=0,
        layer="MTOP",
        name="wire",
    )
    wg_sec = gf.Section(
        width=core_width,
        offset=0,
        layer="WG",
        port_names=("e1", "e2"),
        port_types=("electrical", "electrical"),
        name="wg",
    )
    mask_sec1 = gf.Section(
        width=mask_offset,
        offset=core_width / 2 + mask_offset / 2,
        layer=deep_etch_layer,
        name="etch_mask1",
    )
    mask_sec2 = gf.Section(
        width=mask_offset,
        offset=-(core_width / 2 + mask_offset / 2),
        layer=deep_etch_layer,
        name="etch_mask2",
    )
    xs = gf.CrossSection(sections=[wg_sec, wire_sec, mask_sec1, mask_sec2],radius=1)
    return xs

def routing_with_mytaper(c, port1:gf.Port, port2:gf.Port, cross_section1, cross_section2,taper_length=20, tangent_offset=0):
    offset_sections = [section.model_copy(update={"offset": section.offset + tangent_offset}) for section in cross_section1.sections]
    cross_section1_cp = cross_section1.copy(sections=offset_sections)
    Xtrans = gf.path.transition(cross_section1=cross_section1_cp, cross_section2=cross_section2, width_type="linear",offset_type="linear")
    p2_moved = port2.copy()
    if port2.orientation == 0:
        p2_moved.center = (p2_moved.center[0]+taper_length, p2_moved.center[1]+tangent_offset)
    elif port2.orientation == 180:
        p2_moved.center = (p2_moved.center[0]-taper_length, p2_moved.center[1]-tangent_offset)
    elif port2.orientation == 90:
        p2_moved.center = (p2_moved.center[0]-tangent_offset, p2_moved.center[1]+taper_length)
    elif port2.orientation == 270:
        p2_moved.center = (p2_moved.center[0]+tangent_offset, p2_moved.center[1]-taper_length)
    
    route = gf.routing.route_single(c, port1, p2_moved, cross_section=cross_section1, allow_width_mismatch=True, auto_taper=False,start_straight_length=150)
    trans = gf.path.straight(length=taper_length).extrude_transition(transition=Xtrans)
    
    p2_moved.orientation += 180
    trans_ref = c << trans
    trans_ref.connect(Xtrans.cross_section1.sections[0].port_names[0], p2_moved, allow_type_mismatch=True, allow_width_mismatch=True)
    return route

@gf.cell
def doubly_clamped_beam_with_spring(beam_spec, spring_spec):
    c = gf.Component()
    beam = c << beam_spec()
    spring = c << spring_spec()
    spring.connect("e1", beam.ports["w1"], allow_width_mismatch=True)

    for port in beam.ports:
        if not port.orientation == 180:
            c.add_ports([port])
    c.add_ports(spring.ports.filter(orientation=180))
    c.add_ports(spring.ports.filter(regex='.*_anchor'))
    merge_deep_etch_mask(c)
    return c
@gf.cell
def bridge(mxn = (5,3), mask_offset=10,open=[]):
    c = gf.Component()
    truss_ref = truss_v2(width=0.16,size=1,mxn=mxn,open=open)
    c << truss_ref
    create_deep_etch_mask(c,'bbox',mask_offset=mask_offset,x_off=False)
    c.ports = truss_ref.ports
    return c
@gf.cell
def movable_finger_support(length,mask_offset=5, open=[]):
    c = gf.Component()
    total_number = int(length)
    truss_ = truss_v2(width=0.16,size=1,mxn=(total_number,3),open=open)
    c << truss_
    create_deep_etch_mask(c,'bbox',mask_offset=mask_offset)
    c.ports = truss_.ports
    return c

def finger_hard_support(size,mask_offset=5, metal_offset=2, metal_layer='MTOP'):
    c = gf.Component()
    rect = gf.components.rectangle(size=size,layer="WG")
    c << rect
    metal = c << gf.components.rectangle(size=(size[0]-metal_offset,size[1]-metal_offset),layer=metal_layer)
    metal.movey(metal_offset/2)
    create_deep_etch_mask(c,'bbox',mask_offset=mask_offset,x_off=False, deep_etch_layer='DEEP_ETCH_PL')
    for port in rect.ports:
        if port.orientation == 0:
            name = "E1"
        elif port.orientation == 90:
            name = "N1"
        elif port.orientation == 180:
            name = "W1"
        elif port.orientation == 270:
            name = "S1"
        c.add_port(
            name=name,
            width=1,
            orientation=port.orientation,
            center=port.center,
            layer="WG",
            port_type='electrical'
        )
    c.cross_section = metal_wire(core_width=size[1], wire_width=size[1]-metal_offset, mask_offset=mask_offset, deep_etch_layer='DEEP_ETCH_PL')
    return c
@gf.cell
def finger_hard_support_L(size,mask_offset=5, metal_offset=2, metal_layer='MTOP'):
    c = gf.Component()
    rect = gf.components.rectangle(size=size,layer="WG")
    c << rect
    metal = c << gf.components.rectangle(size=(size[0]-2*metal_offset,size[1]-metal_offset),layer=metal_layer)
    metal.movex(metal_offset)
    metal.movey(metal_offset)
    
    create_deep_etch_mask(c,'bbox',mask_offset=mask_offset)
    for port in rect.ports:
        if port.orientation == 0:
            name = "E1"
        elif port.orientation == 90:
            name = "N1"
        elif port.orientation == 180:
            name = "W1"
        elif port.orientation == 270:
            name = "S1"
        c.add_port(
            name=name,
            width=1,
            orientation=port.orientation,
            center=port.center,
            layer="WG",
            port_type='electrical'
        )
    return c
@gf.cell
def pad(size, metal_offset,pad_layer='PADDING'):
    c = gf.Component()
    rect = c <<  gf.components.rectangle(size=size,layer=pad_layer)
    metal = c << gf.components.rectangle(size=(size[0]-2*metal_offset,size[1]-2*metal_offset),layer='MTOP')
    metal.move((metal_offset,metal_offset))
    for port in metal.ports:
        if port.orientation == 0:
            name = "E1"
        elif port.orientation == 90:
            name = "N1"
        elif port.orientation == 180:
            name = "W1"
        elif port.orientation == 270:
            name = "S1"
        c.add_port(
            name=name,
            width=1,
            orientation=port.orientation,
            center=port.center,
            layer="WG",
            port_type='electrical'
        )
    return c

@gf.cell
def U_shape_pad(p1_size=(100, 800), p2_size=(200, 100), p3_size=(100, 400), metal_offset=10):
    c = gf.Component()
    pad1 = c << pad(size=p1_size, metal_offset=metal_offset, pad_layer='PADDING')
    pad2 = c << pad(size=p2_size, metal_offset=metal_offset, pad_layer='PADDING')
    pad3 = c << pad(size=p3_size, metal_offset=metal_offset, pad_layer='PADDING')
    pad2.connect("W1", pad1.ports["E1"], allow_width_mismatch=True, allow_type_mismatch=True)
    pad2.movey(p1_size[1]/2 - p2_size[1]/2)
    pad3.connect("W1", pad2.ports["E1"], allow_width_mismatch=True, allow_type_mismatch=True)
    pad3.movey(p2_size[1]/2 - p3_size[1]/2)
    c.add_ports(pad1.ports)
    c.add_ports(pad2.ports)
    c.add_ports(pad3.ports)
    c.auto_rename_ports()
    return c

@gf.cell
def beam_fixed_support(size,mask_offset=5, metal_offset=2, metal_layer='MTOP'):
    c = gf.Component()
    rect = gf.components.rectangle(size=size,layer="WG")
    c << rect
    metal_rect = gf.components.rectangle(size=(size[0]-2*metal_offset, size[1]-2*metal_offset),layer=metal_layer)
    metal_rect_ref = c << metal_rect
    metal_rect_ref.move((metal_offset,metal_offset))
    create_deep_etch_mask(c,'bbox',mask_offset=mask_offset, deep_etch_layer='DEEP_ETCH')
    for port in rect.ports:
        if port.orientation == 0:
            name = "E1"
        elif port.orientation == 90:
            name = "N1"
        elif port.orientation == 180:
            name = "W1"
        elif port.orientation == 270:
            name = "S1"
        c.add_port(
            name=name,
            width=1,
            orientation=port.orientation,
            center=port.center,
            layer="WG",
            port_type='placement'
        )
    return c

@gf.cell
def beam_test(width=10,length=50):
    '''"
    Test resistance of doubly clamped beam
    '''
    pad_= pad(size=(400,400),metal_offset=10)
    xs = cross_section_with_sleeves(core_width=width,total_width=width+15)
    beam = gf.components.straight(length=length, width=width, cross_section=xs)
    c = gf.Component()
    pad1_ref = c << pad_
    pad2_ref = c << pad_
    beam_ref = c << beam
    pad1_ref.connect('E1', beam_ref.ports['o1'],allow_width_mismatch=True,allow_type_mismatch= True)
    pad2_ref.connect('W1', beam_ref.ports['o2'],allow_width_mismatch=True,allow_type_mismatch= True)
    # create_deep_etch_mask(c,'bbox',mask_offset=5,core_layer=['MTOP','WG','PADDING'],deep_etch_layer='DEEP_ETCH')
    return c

def convert_to_printable(c, post_collection_layers=['MTOP','SHALLOW_ETCH']):
    c2 = gf.Component()
    # extract the layers of interest into a new component
    layers = ['DEEP_ETCH', 'PADDING', 'WG','SHALLOW_ETCH', 'PROTECTION_PL','DEEP_ETCH_PL']
    layers = [gf.get_layer(layer) for layer in layers]
    
    c2 << c.extract(layers)

    # get the polygons dictionary and layer keys
    polys = c2.get_polygons()
    reg = gf.kdb.Region()
    

    for layer in layers:
        reg_layer = gf.kdb.Region(polys.get(layer, []))
        reg.insert(reg_layer)
    
    holes = reg.holes()
    # filter small holes
    min_area = 1e6
    small_holes = gf.kdb.Region()
    
    for poly in holes.each():
        if poly.area() < min_area:
            small_holes.insert(poly)
    
    # 将小面积的 holes 补回 reg 中
    reg.insert(small_holes)
    hulls = reg.sized(-3e3,1)

    # add hulls to a new component if not empty
    c_output = gf.Component()
    if not hulls.is_empty():
        c_output.add_polygon(hulls, layer=("DEEP_ETCH"))
    c_output.add_polygon(reg, layer=("WG"))
    
    bbox = gf.kdb.DPolygon(c_output.bbox()).sized(100)
    c_output.add_polygon(bbox, layer=(7,0))
    # DEEPETCH_PL is bbox - DEEP_ETCH + DEEP_ETCH_PL in original component
    # c_output << gf.boolean(c_output,c_output,"not",'DEEP_ETCH_PL',(7,0),"DEEP_ETCH")
    DEEPETCH_PL_component = gf.boolean(c_output,c_output,"not",'DEEP_ETCH_PL',(7,0),"DEEP_ETCH")
    DEEPETCH_PL_component = gf.boolean(DEEPETCH_PL_component, c2, "or", "DEEP_ETCH_PL", "DEEP_ETCH_PL", "DEEP_ETCH_PL")
    c_output << DEEPETCH_PL_component
    
    
    
    for layer, polys in c2.get_polygons(layers=['DEEP_ETCH']).items():
        for poly in polys:
            c_output.add_polygon(poly,layer=(10,0))
    c_output << c.extract(post_collection_layers)
    return c_output

@gf.cell
def ring_resonator_fill_middle(**kwargs):
    ring_resonator_component = ring_resonator(**kwargs)
    ring_resonator_component.extract(['DEEP_ETCH']).get_polygons(layers=['DEEP_ETCH'])
    region = gf.kdb.Region(ring_resonator_component.extract(['DEEP_ETCH']).get_polygons(layers=['DEEP_ETCH'])[gf.get_layer('DEEP_ETCH')]).hulls()
    c = gf.Component()
    c << ring_resonator_component
    c.add_polygon(region,layer=gf.get_layer('DEEP_ETCH'))
    c.ports = ring_resonator_component.ports
    return c

@gf.cell
def etch_depth_array(spacing=150, layers=['WG','DEEP_ETCH'], frame_layer='DEEP_ETCH'):
    def etch_depth_trench(size=(35,35), layer='WG'):
        c = gf.Component()
        layer_tuple = gf.get_layer_tuple(layer)
        layer_name = ''
        try:
            layer_name = gf.get_layer_name(layer_tuple)
        except ValueError:
            pass
        c << gf.components.rectangle(size=size, layer=layer)
        text = c << gf.components.text(text=f"{layer_name}{layer_tuple}", size=10, layer=layer, position=(0,0))
        text.move(origin=text.center, destination=(size[0]/2,-8))
        return c
    c = gf.Component()
    col_per_row = ceil(700/spacing)
    for i, layer in enumerate(layers):
        trench = c << etch_depth_trench(layer=layer)
        trench.move(((i%col_per_row)*spacing, -(i//col_per_row)*spacing))
    c2 = gf.Component()
    c2 << gf.components.add_frame(c, width=2, layer=frame_layer)
    text = gf.components.text(text="Etch Depth", size=80, layer=frame_layer)
    text_ref = c2 << text
    text_ref.move(origin=(text.xmin, text.ymin), destination=(c2.xmin+10, c2.ymin+2))
    return c2

@gf.cell
def litho_calipers(alignment_type:Literal['EBL','PL']= 'EBL', row_spacing=0, layer1='WG', layer2='SLAB150'):
    num_notches = 5
    if alignment_type == 'EBL':
        notch_size = (0.3, 10)
        notch_spacing = 2
        offset_per_notch = 0.02
    if alignment_type == 'PL':
        notch_size = (2, 10)
        notch_spacing = 2
        offset_per_notch = 0.1
    c = gf.Component()
    c << gf.components.litho_calipers(
        notch_size=notch_size, 
        notch_spacing=notch_spacing, 
        num_notches=num_notches, 
        offset_per_notch=offset_per_notch, 
        row_spacing=row_spacing, 
        layer1=layer1, 
        layer2=layer2)
    layer_tuple1 = gf.get_layer_tuple(layer1)
    layer_tuple2 = gf.get_layer_tuple(layer2)

    main_label = c << text_outline(text=f"{layer_tuple1} M",size=10,layer=layer1,outline_width=1,with_mask=False)
    main_label.move(origin=(main_label.xmin, main_label.ymin), destination=(num_notches*2*(notch_spacing+notch_size[0]) + 5,0))
    
    vernier_label = c << text_outline(text=f"{layer_tuple2} V",size=10,layer=layer2,outline_width=1,with_mask=False)
    vernier_label.move(origin=(vernier_label.xmin, vernier_label.ymax), destination=(num_notches*2*(notch_spacing+notch_size[0]) + 5,0))
    c2 = gf.Component()
    horizontal = c2 << c
    vertical = c2<<c
    vertical.rotate(90)
    vertical.move(origin=(vertical.xmin, 0), destination=(horizontal.xmin, horizontal.ymax+10))
    label_text = f'''spacing = {notch_spacing}\noffset= {offset_per_notch}'''
    label = c2 << text_outline(text=label_text, size=15, outline_width=1, with_mask=False,layer=layer1)
    label.move(origin=(label.xmin, label.ymin), destination=(vertical.xmax,horizontal.ymax))
    label2 = c2 << text_outline(text=label_text, size=15, outline_width=1, with_mask=False,layer=layer2)
    label2.move(origin=(label2.xmin, label2.ymin), destination=(vertical.xmax,label.ymax))
    return c2

@gf.cell
def litho_caliper_array(types:list[Literal['EBL', 'PL']], layers, frame_layer='DEEP_ETCH'):
    """
    Used to create a lithographic caliper array.
    The first type and layer in the lists are used as the reference for all calipers.
    
    Args:
        types (list[Literal['EBL', 'PL']]): List of types for the calipers.
        layers (list): List of layers corresponding to the types.
        frame_layer (str, optional): Layer for the frame. Defaults to 'DEEP_ETCH'.
    """
    c = gf.Component()
    first_type, first_layer = types[0], layers[0]
    for i, (type2, layer2) in enumerate(zip(types[1:], layers[1:])):
        if 'PL' in (first_type, type2):
            type_ = 'PL'
        else:
            type_ = 'EBL'
        caliper = litho_calipers(alignment_type=type_, layer1=first_layer, layer2=layer2)
        caliper_ref = c << caliper
        caliper_ref.move((i%4 * 200, i//4 * -200))
    c2 = gf.Component()
    c2 << gf.components.add_frame(c, width=2, layer=frame_layer)
    text = gf.components.text(text="Alignment", size=80, layer=frame_layer)
    text_ref = c2 << text
    text_ref.move(origin=(text.xmin, text.ymin), destination=(c2.xmin+10, c2.ymin+2))
    return c2

@gf.cell
def ALD_beam_with_ring_end(width=0.4, length=50, radius = 5, support_length=1,support_thickness = 0.1, layer:LayerSpec='ALD_CORE', mask_offset:float=1) -> gf.Component:
    c = gf.Component()
    beam = c << gf.components.rectangle(size=(length+width/2, width), layer=layer,port_type='placement')
    def ring_end():
        c = gf.Component()
        ring_end = c << gf.components.ring(radius=radius, layer=layer, angle=180, width=width)
        c.add_port('n1',center=(ring_end.center[0],ring_end.ymax),width=width,orientation=90,layer=layer,port_type='placement')
        c.add_port('e_mid',center=(ring_end.center[0],ring_end.ymin),width=width,orientation=270,layer=layer,port_type='placement')
        c.add_port('e1',center=(ring_end.xmin+width/2,ring_end.ymin),width=width,orientation=270,layer=layer,port_type='placement')
        c.add_port('e2',center=(ring_end.xmax-width/2,ring_end.ymin),width=width,orientation=270,layer=layer,port_type='placement')
        return c
    ring = c << ring_end()
    ring.connect('n1', beam.ports['e1'])
    ring.movex(width/2)
    create_deep_etch_mask(c, 'bbox', mask_offset=mask_offset, deep_etch_layer='DEEP_ETCH',x_off=False)
    roung_corner_support = gf.components.rectangle(size=(support_thickness, support_length), layer=layer,port_type='placement')
    ports = [ring.ports['e1'], ring.ports['e2'], beam.ports['e3']]
    for port in ports:
        corner_support = c << roung_corner_support
        corner_support.connect('e1', port,allow_width_mismatch=True)
    reg = c.get_region(layer=layer,merge=True)
    reg2 = reg.rounded_corners(r_inner=(support_length-width)/2*1e3,r_outer=0, n=32)
    c2 = gf.Component()
    c2.add_polygon(reg2, layer=layer)
    c2.add_ports(ports+[ring.ports['e_mid'],beam.ports['e4'].copy()])
    c2 << c.extract(['DEEP_ETCH'])
    c2 << gf.boolean(c2,c2,'not','ALD_ETCH_EBL','DEEP_ETCH','ALD_CORE')
    return c2

@gf.cell
def electrode(width: float, height: float, cross_section, metal_offset, mask_offset=5) -> gf.Component:
    c = gf.Component() 
    xs_end = metal_wire(core_width=width, wire_width=width- 2*metal_offset, mask_offset=10.0)
    xs_start = cross_section
    
    Xtrans1 = gf.path.transition(cross_section1=xs_start, cross_section2=xs_end, width_type="linear",offset_type="linear",)
    electrode_body = gf.path.straight(length=height).extrude_transition(Xtrans1)
    
    body_ref = c << electrode_body
    body_ref.rotate(-90)
    
    
    end = gf.components.rectangle(size=(width, metal_offset*2), layer='WG')
    rounded = end.get_region('WG').rounded_corners(r_outer=metal_offset*1000, r_inner=metal_offset,n=50)
    rounded_c = gf.Component()
    rounded_c.add_polygon(rounded, layer='WG')
    bbox = end.bbox()
    bbox.top = bbox.height()/2
    bbox = gf.kdb.DPolygon(bbox)
    c2 = gf.Component()
    c2.add_polygon(bbox, layer='WG',)
    
    btm = c << gf.boolean(A=c2, B=rounded_c, operation="and", layer='WG')
    btm.move((-width / 2, -height-metal_offset))

    c.remove_layers(['DEEP_ETCH'])
    
    c.add_port(name='n1', center=(0, 0),cross_section=cross_section,orientation=90,port_type='electrical')
    c.add_port(name='s1', center=(0, -height -metal_offset),width=1, layer='WG', orientation=270)
    c.flatten()
    create_deep_etch_mask(c,mask_offset=mask_offset,y_off=False, deep_etch_layer='DEEP_ETCH')
    
    return c

@gf.cell
def electrode_rect(width, height, metal_offset, mask_offset=5) -> gf.Component:
    c = gf.Component()
    metal_height = height - 2 * metal_offset
    metal_width = width - 2 * metal_offset
    metal = gf.components.rectangle(size=(metal_width, metal_height), layer="MTOP")
    metal_rounded = metal.get_region(layer="MTOP").rounded_corners(r_inner=0, r_outer=metal_offset*1000, n=50)
    c.add_polygon(metal_rounded, layer="MTOP")
    
    silicon = gf.components.rectangle(size=(width, height), layer="WG")
    silicon_rounded = silicon.get_region(layer="WG").rounded_corners(r_inner=0, r_outer=metal_offset*1000, n=50)
    silicon_rounded_c = gf.Component()
    silicon_rounded_c.add_polygon(silicon_rounded, layer="WG")
    silicon_rounded_c.ports = silicon.ports
    silicon_rounded_ref = c << silicon_rounded_c
    
    silicon_rounded_ref.move((-metal_offset, -metal_offset))
    c.ports = metal.ports
    c.add_ports(silicon_rounded_ref.ports)
    c.auto_rename_ports()
    create_deep_etch_mask(c,'bbox',mask_offset=mask_offset)
    return c

@gf.cell
def perforated_shaft(width=100, height=20, hole_size=(15,5), margin=5, recursive_fill=True, brick_mode:Literal[0,1]=0,create_mask=True,mask_offset=5) -> gf.Component:
    """Generates a rectangular waveguide component 'shaft' filled with a tiled 
    pattern of rounded rectangular holes (bricks).

    The function creates a waveguide layer and populates it with an array of holes. 
    If recursive_fill is enabled, it attempts to fill remaining empty spaces by 
    incrementally decreasing the hole size until the margin limit is reached.

    Args:
        width: Total width of the waveguide shaft.
        height: Total height of the waveguide shaft.
        hole_size: Dimensions (x, y) of the initial hole/brick to be placed.
        margin: The minimum spacing between holes and between holes and the 
            waveguide edge.
        recursive_fill: If True, iteratively fills remaining gaps with 
            progressively smaller holes (decreasing size by 1 unit per iteration).
        brick_mode: Tiling orientation and fill strategy.
            0: Horizontal emphasis. Bricks are tiled with a half-width offset in 
               the x-direction (staggered columns).
            1: Vertical emphasis. Bricks are tiled with a half-height offset in 
               the y-direction (staggered rows).

    Returns:
        gf.Component: A component containing the waveguide ('WG' layer) with the 
            patterned holes subtracted. Includes a deep etch mask based on the 
            bounding box.

    Note:
        - The holes are automatically rounded using a corner radius of 1000 
          (effectively max rounding for small holes).
        - Uses boolean 'not' operations to extract hole regions from the 
          waveguide bulk.
    """
    hole_layer = (1,2)
    brick_layer = (1,3)
    def brick(size):
        c = gf.Component()
        reg = gf.components.rectangle(size=size, layer=hole_layer).get_region(hole_layer)
        rounded = reg.rounded_corners(0, 1000,10)
        c.add_polygon(rounded, layer=hole_layer)
        bbox = c.bbox()
        bbox.bottom -= margin/2
        bbox.top += margin/2
        bbox.left -= margin/2
        bbox.right += margin/2
        c.add_polygon(gf.kdb.DPolygon(bbox),brick_layer)
        return c
    c = gf.Component()
    shaft = gf.components.rectangle(size=(width, height), layer='WG')
    pattern_area = gf.components.rectangle(size=(width - margin, height - margin), layer='WG')
    pattern_area_ref = c << pattern_area
    pattern_area_ref.move((margin/2, margin/2))
    
    idx = brick_mode
    current_hole_size = hole_size[idx]
     
    
    while current_hole_size >= margin/2:
        brick_size = (current_hole_size,hole_size[1]) if brick_mode ==0 else (hole_size[0],current_hole_size)
        brick_ = brick(size=brick_size)
        c2 = gf.boolean(c,c,'not','WG','WG',brick_layer)
        if brick_mode == 0:
            c2.fill(brick_,
                fill_layers=[('WG',0)],
                row_step=gf.kdb.DVector(brick_size[0]+margin,0),
                col_step=gf.kdb.DVector(brick_size[0]/2+margin/2,brick_size[1]+margin),
                multi=True
                )
        if brick_mode == 1:
            c2.fill(brick_,
                fill_layers=[('WG',0)],
                row_step=gf.kdb.DVector(brick_size[0]+margin,brick_size[1]/2+margin/2),
                col_step=gf.kdb.DVector(0,brick_size[1]+margin),
                multi=True
                )
            
        
        current_hole_size -= 1
        if brick_layer not in c2.layers:
            continue
        c.add_ref(c2.extract(layers=[hole_layer,brick_layer]))
        
        if not recursive_fill:
            break
    c << shaft
    c2 = gf.Component()
    holes_ref = c2 << c.extract(layers=[hole_layer,brick_layer])
    holes_ref.move(origin=holes_ref.center, destination=shaft.center)
    final_component = gf.boolean(shaft, holes_ref, 'not', 'WG', 'WG', hole_layer)
    final_component.ports = shaft.ports
    if create_mask:
        create_deep_etch_mask(final_component, 'bbox', deep_etch_layer='DEEP_ETCH_PL', mask_offset=mask_offset)
    return final_component

@gf.cell
def spring_5um(spring_width, spring_length, separation, num_loops, mask_offset=5) -> gf.Component:
    c = gf.Component()
    # spring base support
    base = perforated_shaft(width=separation, height=separation)
    flying_bar = perforated_shaft(width=separation, height=separation/2)
    base_start = c << base
    beam_single = gf.components.rectangle(size=(spring_length, spring_width), layer='WG')
    
    beam_start = c << beam_single
    beam_start.connect('e1', base_start.ports['e4'],allow_width_mismatch=True,allow_type_mismatch=True)
    beam_start.movex(separation/2-spring_width/2)
    
    current_beam = beam_start
    for _ in range(num_loops):
        flying_bar_ref = c << flying_bar
        flying_bar_ref.connect('e2', current_beam.ports['e3'],allow_width_mismatch=True,allow_type_mismatch=True).movex(separation/2-spring_width/2)
        beam = c << beam_single
        beam.connect('e1', flying_bar_ref.ports['e2'],allow_width_mismatch=True,allow_type_mismatch=True).movex(separation/2-spring_width/2)
        flying_bar_ref2 = c << flying_bar
        flying_bar_ref2.connect('e4', beam.ports['e3'],allow_width_mismatch=True,allow_type_mismatch=True).movex(separation/2-spring_width/2)
        beam2 = c << beam_single
        beam2.connect('e1', flying_bar_ref2.ports['e4'],allow_width_mismatch=True,allow_type_mismatch=True).movex(separation/2-spring_width/2)
        current_beam = beam2
    
    base_end = c << gf.components.rectangle(size=(separation, separation), layer='WG')
    base_end.connect('e2', current_beam.ports['e3'],allow_width_mismatch=True,allow_type_mismatch=True).movex(separation/2-spring_width/2)
    
    c.add_port(name='p1',port=base_start.ports['e2'])
    c.add_port(name='p2',port=base_end.ports['e4'])
    total_width = c.xsize
    create_deep_etch_mask(c, 'bbox', deep_etch_layer='DEEP_ETCH_PL', mask_offset=mask_offset)
    c = merge_layers_with_priority(c, {'WG':3,'PADDING':2,'DEEP_ETCH':1,'DEEP_ETCH_PL':1})
    
    c.info['total_width'] = total_width
    
    return c

@gf.cell
def combdrive_fingers_5um(finger_length:float=20.0, finger_width:float=2, finger_gap:float=2, overlap=2, pair_num=20, round_corner=1) -> gf.Component:
    c = gf.Component()
    
    finger_pts = [(0, 0), (finger_length, 0), (finger_length, finger_width), (0, finger_width)]
    finger_single = gf.Component()
    finger_single.add_polygon(finger_pts, layer='WG')
    round_corner_pts = [(0, 0), (2*round_corner*1000, 0), (2*round_corner*1000, finger_width*1000), (0, finger_width*1000)]
    round_corner_poly = gf.kdb.Polygon(round_corner_pts).round_corners(rinner=0,router=round_corner*1000,n=16).moved(dx=finger_length*1000 - round_corner*1000,dy=0)
    finger_single.add_polygon(round_corner_poly, layer='WG')
    finger_single.flatten()
    
    for i in range(pair_num):
        finger_l = c << finger_single
        finger_l.movey(2*i*(finger_width + finger_gap))
        finger_r = c << finger_single
        finger_r.mirror()
        finger_r.movex(2*finger_length - overlap).movey(finger_gap+finger_width)
        finger_r.movey(2*i*(finger_width + finger_gap))
    finger_l = c << finger_single
    finger_l.movey(2*pair_num*(finger_width + finger_gap))
    c.move(origin=c.center, destination=(0,0))
    c.add_port(name='w1', center=(c.xmin, 0), orientation=180,width=finger_width,layer='WG',port_type='placement')
    c.add_port(name='e1', center=(c.xmax, 0), orientation=0,width=finger_width,layer='WG',port_type='placement')
    c.info['total_length'] = c.ysize
    c.info['total_width'] = c.xsize
    return c

@gf.cell
def combdrive_array(finger_spec, movable_base_width, fixed_base_width, mask_offset=10) -> gf.Component:
    c = gf.Component()
    
    base_length = finger_spec().ysize + 30  # ensure base is longer than finger
    movable_base = perforated_shaft(width=movable_base_width, height=base_length,brick_mode=1,hole_size=(5,10), margin=5,create_mask=False)
    movable_base_ref = c.add_ref(movable_base)
    finger_ref = c.add_ref(finger_spec())
    movable_base_ref.connect('e1', finger_ref.ports['w1'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
    movable_base_ref.movey(-10)
    
    fixed_base = gf.components.rectangle(size=(fixed_base_width, base_length), layer='WG')
    fixed_base_ref = c.add_ref(fixed_base)
    fixed_base_ref.connect('e1', finger_ref.ports['e1'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
    fixed_base_ref.movey(10)
    
    c.add_port(name='m', port=movable_base_ref.ports['e2'])
    c.add_port(name='f', port=fixed_base_ref.ports['e2'])
    create_deep_etch_mask(c, 'bbox', deep_etch_layer='DEEP_ETCH_PL', mask_offset=mask_offset)
    
    return c

@gf.cell
def folded_spring_5um(length, width, separation, anchor_size, flying_bar_height, shaft_hole_size, shaft_margin, mask_offset=2):
    Point = gf.kdb.Point
    Trans = gf.kdb.Trans    
    c_out = gf.Component()
    anchor = gf.components.rectangle(size=(anchor_size, anchor_size))
    flying_bar = perforated_shaft(width=3*separation+width, height=flying_bar_height, hole_size=shaft_hole_size, margin=shaft_margin, create_mask=False)
    beam_single = gf.components.rectangle(size=(length, width))
    
    flying_bar_ref = c_out.add_ref(flying_bar)
    x_start = width/2
    y_start = flying_bar_height
    center_p = Point(flying_bar_ref.ports['e2'].x*1000, flying_bar_ref.ports['e2'].y*1000)
    beam_refs = []
    for i in range(4):
        beam_ref = c_out.add_ref(beam_single)
        beam_ref.connect('e1', flying_bar_ref.ports['e2'].copy(Trans(Point(x_start*1000, y_start*1000)-center_p)),
                         allow_width_mismatch=True)
        beam_refs.append(beam_ref)
        x_start += separation
    anchor_1 = c_out.add_ref(anchor)
    anchor_1.connect('e1', beam_refs[-1].ports['e3'].copy(Trans(x=(anchor_size/2-width/2)*1000,y=0)), allow_width_mismatch=True)
    
    anchor_2 = c_out.add_ref(anchor)
    anchor_2.connect('e1', beam_refs[0].ports['e3'].copy(Trans(x=-(anchor_size/2-width/2)*1000,y=0)), allow_width_mismatch=True)
    
    anchor_3 = perforated_shaft(width=separation+width, height=anchor_size+10, hole_size=(shaft_hole_size[1],shaft_hole_size[0]), margin=shaft_margin, brick_mode=1,create_mask=False)
    anchor_3_ref = c_out.add_ref(anchor_3)
    anchor_3_ref.connect('e4', flying_bar_ref.ports['e2'].copy(Trans(x=0,y=(length*1000))),
                         allow_width_mismatch=True)
    c_out.add_ports([
        anchor_3_ref.ports['e2'],
        anchor_1.ports['e4'],
        anchor_2.ports['e2']
    ])
    c_out.auto_rename_ports()
    c_out.info['total_width'] = c_out.xsize

    create_deep_etch_mask(c_out, 'bbox', mask_offset=mask_offset,deep_etch_layer='DEEP_ETCH_PL')
    
    
    return c_out