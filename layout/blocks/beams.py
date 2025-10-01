import gdsfactory as gf
from .utils import create_deep_etch_mask, merge_deep_etch_mask
from gdsfactory.typings import LayerSpec


def cantilever_beam(length, width, mask_offset=1):
    """Creates a cantilever beam with a deep etch mask."""
    c = gf.Component()
    c.add_polygon(
        [
            (0, 0),
            (0, 5),
            (5, 5),
            (5, 0),
        ],
        layer="WG",
    )
    c.add_polygon(
        [
            (0, 0),
            (0, width),
            (-length, width),
            (-length, 0),
        ],
        layer="WG",
    )
    c.flatten()

    create_deep_etch_mask(c, mask_offset)

    c.flatten()
    c.show()
    c.add_port(
        name="s1",
        center=(-length, 0),
        orientation=-90,
        width=1,
        layer="WG",
        port_type="placement",
    )

    return c


@gf.cell
def doubly_clamped_beam(
    length, width, taper_length=0.1, taper_width=0.3, mask_offset=1
):
    c = gf.Component()
    beam = c << gf.components.rectangle(
        size=(length, width), layer="WG", port_type="placement"
    )
    clamp_left = c << gf.components.taper(
        length=taper_length,
        width1=width,
        width2=taper_width,
        layer="WG",
        port_types=["placement", "placement"],
    )
    clamp_left.connect("o1", beam.ports["e1"])

    clamp_right = c << gf.components.taper(
        length=taper_length,
        width1=width,
        width2=taper_width,
        layer="WG",
        port_types=["placement", "placement"],
    )
    clamp_right.connect("o1", beam.ports["e3"])
    c.add_ports([clamp_left.ports["o2"], clamp_right.ports["o2"]])
    c.ports[0].name = "w1"
    c.ports[1].name = "e1"

    c.add_port(
        "s1",
        center=(length / 2, 0),
        orientation=-90,
        width=1,
        layer="WG",
        port_type="placement",
    )

    c.flatten()

    create_deep_etch_mask(c, mask_offset=mask_offset, x_off=False)

    return c


@gf.cell
def doubly_clamped_beam_with_spring(beam_spec, spring_spec):
    c = gf.Component()
    beam = c << beam_spec()
    spring = c << spring_spec()
    spring.connect("e1", beam.ports["w1"], allow_width_mismatch=True)

    c.ports = beam.ports
    merge_deep_etch_mask(c)
    return c


@gf.cell
def doubly_clamped_beam_with_round_support(
    width,
    length,
    support_length,
    layer: LayerSpec = "WG",
    create_mask=False,
    mask_offset=1,
):
    points = [
        (0, 0),
        (width + 2 * support_length, 0),
        (width + 2 * support_length, support_length),
        (width + 1 * support_length, support_length),
        (width + 1 * support_length, length - support_length),
        (width + 2 * support_length, length - support_length),
        (width + 2 * support_length, length),
        (0, length),
        (0, length - support_length),
        (support_length, length - support_length),
        (support_length, support_length),
        (0, support_length),
    ]
    c = gf.Component()
    c.add_polygon(points, layer=layer)
    layer_tuple = gf.get_layer_tuple(layer)
    circle = gf.components.circle(
        radius=support_length, layer=(layer_tuple[0], layer_tuple[1] + 1)
    )
    c1, c2, c3, c4 = (c.add_ref(circle) for _ in range(4))
    c1.move((0, support_length))
    c2.move((width + 2 * support_length, support_length))
    c3.move((0, length - support_length))
    c4.move((width + 2 * support_length, length - support_length))

    beam_round = gf.boolean(
        c, c, "not", layer, layer, (layer_tuple[0], layer_tuple[1] + 1)
    )
    c = gf.Component()
    c.add_ref(beam_round)
    c.add_port(
        "w1",
        center=(width / 2 + support_length, length),
        port_type="placement",
        width=width,
        orientation=90,
        layer=layer,
    )
    c.add_port(
        "e1",
        center=(width / 2 + support_length, 0),
        port_type="placement",
        width=width,
        orientation=270,
        layer=layer,
    )
    c.add_port(
        "s1",
        center=(support_length, length / 2),
        port_type="placement",
        width=1,
        orientation=180,
        layer=layer,
    )

    if create_mask:
        create_deep_etch_mask(c, mask_offset=mask_offset, y_off=False)
    c.rotate(90)
    return c


if __name__ == "__main__":
    c = cantilever_beam(length=10, width=0.1, mask_offset=0.5)
    c.draw_ports()
    c.show()
