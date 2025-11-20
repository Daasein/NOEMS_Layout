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
    truss_ref = truss(width=0.15,size=1,mxn=mxn,open=open)
    c << truss_ref
    create_deep_etch_mask(c,'bbox',mask_offset=mask_offset,x_off=False)
    c.ports = truss_ref.ports
    return c
@gf.cell
def movable_finger_support(length,mask_offset=5, open=[]):
    c = gf.Component()
    total_number = int(length)
    truss_ = truss(width=0.15,size=1,mxn=(total_number,3),open=open)
    c << truss_
    create_deep_etch_mask(c,'bbox',mask_offset=mask_offset)
    c.ports = truss_.ports
    return c
@gf.cell
def finger_hard_support(size,mask_offset=5, metal_offset=2, metal_layer='MTOP'):
    c = gf.Component()
    rect = gf.components.rectangle(size=size,layer="WG")
    c << rect
    metal = c << gf.components.rectangle(size=(size[0],size[1]-metal_offset),layer=metal_layer)
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
    return c
@gf.cell
def finger_hard_support_L(size,mask_offset=5, metal_offset=2, metal_layer='MTOP'):
    c = gf.Component()
    rect = gf.components.rectangle(size=size,layer="WG")
    c << rect
    metal = c << gf.components.rectangle(size=(size[0]-metal_offset,size[1]-metal_offset),layer=metal_layer)
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

