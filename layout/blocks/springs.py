import gdsfactory as gf
from blocks import truss, create_deep_etch_mask


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

    import warnings

    if if_create_mask:
        create_deep_etch_mask(c, method="bbox", mask_offset=mask_offset)
    else:
        warnings.warn(
            "Parameter 'mask_offset' is not in use because 'if_create_mask' is False."
        )

    return c
