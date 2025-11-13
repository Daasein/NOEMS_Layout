import gdsfactory as gf
from blocks import truss, create_deep_etch_mask
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
def spring_anchor_outside(spring_width=0.15, spring_length=20, spring_separation=3):
    c = gf.Component()
    def flying_bar(truss_number, spring_width, spring_separation):
        c = gf.Component()
        truss_size = 1
        truss_width = 0.15
        truss_ = c << truss(truss_width, truss_size, (1, truss_number))
        truss_.movex(-truss_number/2)
        port_x = -spring_separation*1.5
        for i in range(4):
            c.add_port(
                name=f'p{i+1}',
                center=(port_x,0),
                orientation=270,
                width=spring_width,
                layer='WG',
                port_type='placement'
            )
            port_x += spring_separation
        return c
    
    def shuttle_frame(n1,n2,n3):
        c = gf.Component()
        truss_11 = c << truss(0.15, 1, (1, n1))
        truss_12 = c << truss(0.15, 1, (1, n1))
        truss_21 = c << truss(0.15, 1, (n2, 1))
        truss_22 = c << truss(0.15, 1, (n2, 1))
        truss_3 = c << truss(0.15, 1, (1, n3))
        truss_3.movey(n2-1)
        truss_22.movex(n3-1)
        truss_12.movex(n3-n1)
        return c

    fb = flying_bar(ceil(spring_separation*3+spring_width*2), spring_width, spring_separation)

    fb.pprint_ports()
    fb_ref = c << fb
    fb_ref.movey(spring_length)
    # fb_ref.movex(-ceil(spring_separation*3+spring_width*2)/2)
    spring_single = gf.components.rectangle(size=(spring_width, spring_length), layer='WG')
    spring_refs = [c << spring_single for _ in range(4)]
    for i, spring_ref in enumerate(spring_refs):
        spring_ref.connect("e2", fb_ref.ports[f'p{i+1}'], allow_type_mismatch=True)
    sf_ref = c << shuttle_frame(4, int(spring_length*1.2), int(3*spring_separation+6))
    sf_ref.move((-int(3*spring_separation+6)/2,-1))
    anchor = gf.components.rectangle(size=(spring_separation*1.5,spring_separation*1.5), layer='WG')
    anchor_ref = c << anchor
    anchor_ref.movex(-spring_separation*1.5/2)
    
    anchor_ref.movey(-spring_separation*1.5)
    c_new = gf.Component()
    smoothed_region = gf.kdb.Region(c.get_polygons()[1]).rounded_corners(50,100,100)
    c_new.add_polygon(smoothed_region, layer='WG')
    top_y, btm_y = c_new.bbox().top, c_new.bbox().bottom
    c_new.add_port(
        name = 'N1',
        center = (0, top_y),
        orientation = 90,
        width=1,
        layer='WG',
        port_type='placement'
    )
    c_new.add_port(
        name = 'anchor',
        center = (0, btm_y),
        orientation = 270,
        width=1,
        layer='WG',
        port_type='placement'
    )
    
    return c_new

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
    spring_width=0.15,
    spring_separation=3,
    mask_offset=1,
    if_create_mask=True,
):
    c = gf.Component()
    down_spring = c << spring_anchor_outside(spring_width, spring_length, spring_separation)
    up_spring = c << spring_anchor_outside(spring_width, spring_length, spring_separation)
    truss_connection = c << truss(0.15, 1, (5, 10))
    down_spring.connect("N1", truss_connection.ports["S1"])
    up_spring.connect("N1", truss_connection.ports["N1"])
    

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
    return c