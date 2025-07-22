import gdsfactory as gf


def vertical_spacer(length):
    c = gf.Component()
    c.add_port(
        "p1", center=(0, 0), width=1, orientation=-90, layer="WG", port_type="placement"
    )
    c.add_port(
        "p2",
        center=(0, length),
        width=1,
        orientation=90,
        layer="WG",
        port_type="placement",
    )
    return c


if __name__ == "__main__":
    c = vertical_spacer(10)
    c.draw_ports()
    c.plot()
