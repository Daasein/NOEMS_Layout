import gdsfactory as gf


def _create_deep_etch_mask(c, mask_offset=1, x_off=True, y_off=True):
    """Creates a deep etch mask by offsetting the polygons."""
    polygon = c.get_polygons()[gf.get_layer("WG")][0].sized(
        (mask_offset * 1e3 if x_off else 0, mask_offset * 1e3 if y_off else 0)
    )
    # add an offset polygon to create a deep etch mask (1um offset)
    c.add_polygon(polygon, layer=(39, 0))
    booled = gf.boolean(c, c, "not", "DEEP_ETCH", (39, 0), (1, 0))
    c.remove_layers([(39, 0)])
    c << booled


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

    _create_deep_etch_mask(c, mask_offset)

    c.flatten()
    c.show()
    c.add_port(
        name="s1",
        center=(-length / 2, 0),
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

    _create_deep_etch_mask(c, mask_offset=mask_offset, x_off=False)

    return c


if __name__ == "__main__":
    c = cantilever_beam(length=10, width=0.1, mask_offset=0.5)
    c.draw_ports()
    c.show()
