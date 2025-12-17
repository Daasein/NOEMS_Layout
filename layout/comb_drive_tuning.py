import gdsfactory as gf
from blocks import *

def metal_wire(
    core_width: float,
    wire_width: float,
    mask_offset: float,
    
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
        layer="DEEP_ETCH",
        name="etch_mask1",
    )
    mask_sec2 = gf.Section(
        width=mask_offset,
        offset=-(core_width / 2 + mask_offset / 2),
        layer="DEEP_ETCH",
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
    create_deep_etch_mask(c,'bbox',mask_offset=mask_offset,x_off=False)
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
    c.cross_section = metal_wire(core_width=size[1], wire_width=size[1]-metal_offset, mask_offset=mask_offset)
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
    layers = ['DEEP_ETCH', 'PADDING', 'WG','SHALLOW_ETCH']
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
    hulls = reg.sized(-5e3,1)

    # add hulls to a new component if not empty
    c_output = gf.Component()
    # blk = c5 << gf.components.rectangle(size=(200,1100),layer="DEEP_ETCH")
    # blk.move((-68,-87))
    if not hulls.is_empty():
        c_output.add_polygon(hulls, layer=("DEEP_ETCH"))
    c_output.add_polygon(reg, layer=("WG"))
    
    bbox = gf.kdb.DPolygon(c_output.bbox()).sized(100)
    c_output.add_polygon(bbox, layer=(7,0))
    c_output << gf.boolean(c_output,c_output,"not",(9,0),(7,0),"DEEP_ETCH")
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