import gdsfactory as gf


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

    polygon = c.get_polygons()[gf.get_layer("WG")][0].sized(mask_offset * 1e3)
    # add a offset polygon to create a deep etch mask (1um offset)

    c.add_polygon(polygon, layer=(39, 0))

    booled = gf.boolean(c, c, "not", "DEEP_ETCH", (39, 0), (1, 0))
    c.remove_layers([(39, 0)])
    c << booled
    c.flatten()
    c.show()
    c.add_port(
        name="p1",
        center=(-length / 2, 0),
        orientation=-90,
        width=1,
        layer="WG",
        port_type="placement",
    )

    return c


if __name__ == "__main__":
    c = cantilever_beam(length=10, width=0.1, mask_offset=0.5)
    c.draw_ports()
    c.show()
