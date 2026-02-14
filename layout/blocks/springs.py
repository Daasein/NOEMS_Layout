import gdsfactory as gf
from blocks import truss, create_deep_etch_mask, truss_v2
from typing import Literal
from math import ceil


@gf.cell
def spring_with_truss(anchor_size=5, spring_length=20, spring_width=0.15):

    spring_space = 3
    truss_length = 3 * spring_space

    c = gf.Component()

    # create anchor square
    anchor = c << gf.components.rectangle(size=(anchor_size, anchor_size), layer="WG")
    anchor.movex(-anchor_size / 2)
    truss_base = gf.Component()
    truss_base << truss(0.1, 1, (1, 9))
    for i in range(4):
        truss_base.add_port(
            name=f"p{i+1}",
            center=(spring_width / 2 + i * (spring_space - spring_width / 3), 1),
            width=spring_width,
            port_type="placement",
            layer="WG",
            orientation=90,
        )
    # truss_base.draw_ports()

    truss_base_and_spring = gf.Component()
    truss_base_ref = truss_base_and_spring << truss_base
    truss_base_and_spring_ref = c << truss_base_and_spring
    spring_single = gf.components.rectangle(
        size=(spring_width, spring_length), layer="WG", port_type="placement"
    )
    for i in range(4):
        spring = truss_base_and_spring << spring_single
        spring.connect("e4", truss_base.ports[f"p{i+1}"])

    truss_base_and_spring_ref.move((-4.5, -spring_length - 1))

    truss_hat = gf.Component()
    truss_hat << truss(0.1, 1, (1, 9))
    left_hat = (truss_hat << truss(0.1, 1, (7, 1))).movey(-7)
    right_hat = (truss_hat << truss(0.1, 1, (7, 1))).movey(-7).mirror_x(4.5)

    truss_hat_ref = c << truss_hat
    truss_hat_ref.move((-4.5, 7))
    c.movey(-8)

    return c


@gf.cell
def spring_anchor_outside(spring_width=0.16, spring_length=20, spring_separation=3, metal_offset=1,open: Literal[list['left', 'right']]=['left']):
    c = gf.Component()
    def flying_bar(truss_number, spring_width, spring_separation):
        c = gf.Component()
        truss_size = 1
        truss_width = 0.16
        truss_ = truss_v2(truss_width, truss_size, (1, truss_number))
        truss_ref = c << truss_
        truss_ref.movex(-truss_.info['width']/2)
        port_x = -truss_.info['width']/2 + spring_width/2
        for i in range(2):
            c.add_port(
                name=f'p{i+1}',
                center=(port_x,0),
                orientation=270,
                width=spring_width,
                layer='WG',
                port_type='placement'
            )
            port_x += spring_separation
        port_x = +truss_.info['width']/2 - spring_width/2
        for i in range(4,2,-1):
            c.add_port(
                name=f'p{i}',
                center=(port_x,0),
                orientation=270,
                width=spring_width,
                layer='WG',
                port_type='placement'
            )
            port_x -= spring_separation
        c.info['width'] = truss_.info['width']
        return c
    
    def shuttle_frame(n1,n2,n3):
        from blocks.truss import _truss_core
        truss_width = 0.16
        c = gf.Component()
        truss_11 = c << _truss_core(truss_width, 1, (1, n1))
        truss_21 = c << _truss_core(truss_width, 1, (n2, 1))
        truss_3 = c << _truss_core(truss_width, 1, (1, n3))
        truss_3.movey(n2-1)
        truss_22 = c << _truss_core(truss_width, 1, (n2, 1))
        truss_22.movex(n3-1)
        truss_12 = c << _truss_core(truss_width, 1, (1, n1))
        truss_12.movex(n3-n1)
        points = [
        (0,0),
        (n1, 0),
        (n1, 1),
        (1, 1),
        (1, n2-1),
        (n3-1, n2-1),
        (n3-1, 1),
        (n3-n1,1),
        (n3-n1,0),
        (n3,0),
        ]
        if 'left' not in open:
            points.insert(0, (0,n2))
        if 'right' not in open:
            points.append( (n3,n2) )
        p = gf.Path(points)
        sec = gf.Section(width=truss_width/2,offset=truss_width/4,layer='WG')
        xs = gf.CrossSection(sections=[sec])
        path_ref = c << p.extrude(xs)
        return c

    fb_number = ceil(spring_separation*3+spring_width*2)
    fb = flying_bar(fb_number, spring_width, spring_separation)

    fb_ref = c << fb
    fb_ref.movey(spring_length)
    
    spring_single = gf.components.rectangle(size=(spring_width, spring_length), layer='WG')
    spring_refs = [c << spring_single for _ in range(4)]
    for i, spring_ref in enumerate(spring_refs):
        spring_ref.connect("e2", fb_ref.ports[f'p{i+1}'], allow_type_mismatch=True)
    # add additional support incase spring width is large
    if spring_width > 0.16:
        support_ref = c << gf.components.rectangle(size=(spring_width-0.16, 1.08), layer='WG')
        support_ref.connect("e2", spring_refs[0].ports["e4"], allow_type_mismatch=True,allow_width_mismatch=True)
        support_ref.movex(0.08)
        
        support_ref2 = c << gf.components.rectangle(size=(spring_width-0.16, 1.08), layer='WG')
        support_ref2.connect("e2", spring_refs[3].ports["e4"], allow_type_mismatch=True,allow_width_mismatch=True)
        support_ref2.movex(-0.08)
    
    n1 = ceil(spring_separation)+1
    n3 = 2*n1 + fb_number
    n2 = max(ceil(spring_length*1.2),spring_length+6)
    sf_ref = c << shuttle_frame(n1, n2, n3)
    sf_ref.move((-n3/2,-1))
    
    # Anchors
    
    anchor_width = fb.info['width'] - 2*spring_separation
    anchor = gf.components.rectangle(size=(anchor_width,anchor_width/2), layer='WG')
    anchor_ref = c << anchor
    anchor_ref.movex(- anchor_width/2)
    
    anchor_ref.movey(-anchor_width/2)
    
    anchor_2 = gf.components.rectangle(size=(2*anchor_width,anchor_width), layer='WG')
    anchor_2_ref = c << anchor_2
    anchor_2_ref.movex(- anchor_width)
    anchor_2_ref.movey(-anchor_width*1.5)
    
    metal_width = 2*anchor_width-2*metal_offset
    if metal_width>0:
        metal = gf.components.rectangle(size=(metal_width,anchor_width-metal_offset), layer='MTOP')
        metal_ref = c << metal
        metal_ref.movex(- metal_width/2)
        metal_ref.movey(-anchor_width*1.5)
    
    c_new = gf.Component()
    top_y, btm_y = c.bbox().top, c.bbox().bottom
    c.add_port(
        name = 'N1',
        center = (0, top_y),
        orientation = 90,
        width=1,
        layer='WG',
        port_type='placement'
    )
    c.add_port(
        name = 'anchor',
        center = (0, btm_y),
        orientation = 270,
        width=1,
        layer='WG',
        port_type='electrical'
    )
    c.info['frame_width'] = n3
    c.info['frame_length'] = n2
    return c

@gf.cell
def spring_pair(
    anchor_size=5,
    spring_length=20,
    spring_width=0.15,
    mask_offset=1,
    if_create_mask=True,
):
    c = gf.Component()
    down_spring = c << spring_with_truss(anchor_size, spring_length, spring_width)
    up_spring = c << spring_with_truss(anchor_size, spring_length, spring_width)
    up_spring.mirror_y(7)
    truss_connection = c << truss(0.1, 1, (14, 1))
    truss_connection.movex(-4.5)

    c.add_port(
        name="e1",
        center=(-3.5, 7),
        width=1,
        port_type="placement",
        layer="WG",
        orientation=0,
    )
    c.add_port(
        name="w1",
        center=(-4.5, 7),
        width=1,
        port_type="placement",
        layer="WG",
        orientation=180,
    )

    import warnings

    if if_create_mask:
        create_deep_etch_mask(c, method="bbox", mask_offset=mask_offset)
    else:
        warnings.warn(
            "Parameter 'mask_offset' is not in use because 'if_create_mask' is False."
        )

    return c

@gf.cell
def spring_pair_anchor_outside(
    spring_length=20,
    spring_width=0.16,
    spring_separation=3,
    mask_offset=1,
    if_create_mask=True,
    metal_offset=1,
    open: Literal[list['left', 'right']]=['left']
):
    c = gf.Component()
    spring = spring_anchor_outside(spring_width, spring_length, spring_separation, open=open, metal_offset=metal_offset)
    down_spring = c << spring
    up_spring = c << spring
    truss_connection = c << truss_v2(0.16, 1, (4,spring.info['frame_width']), open=(['top','bottom'] + open))

    down_spring.connect("N1", truss_connection.ports["S1"])
    up_spring.connect("N1", truss_connection.ports["N1"],mirror=True)
    

    c.add_ports(truss_connection.ports.filter(regex="^E|^W"))
    for port in c.ports:
        port.name = port.name.lower()
    c.add_ports(down_spring.ports.filter(regex="anchor"), prefix="down_")
    c.add_ports(up_spring.ports.filter(regex="anchor"), prefix="up_")

    import warnings

    if if_create_mask:
        create_deep_etch_mask(c, method="bbox", mask_offset=mask_offset)
    else:
        warnings.warn(
            "Parameter 'mask_offset' is not in use because 'if_create_mask' is False."
        )
    c.move(origin=c.center, destination=(0, 0))
    c.info['frame_width'] = spring.info['frame_width']
    c.info['frame_length'] = spring.info['frame_length']*2 + 4
    return c