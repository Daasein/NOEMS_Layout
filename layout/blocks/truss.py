import gdsfactory as gf


@gf.cell
def _truss_quater_fill(width, size):
    c = gf.Component()
    rec1 = gf.components.rectangle(size=(width / 2, size), layer=(1, 0))
    rec2 = gf.components.rectangle(size=(size, width / 2), layer=(1, 0))
    bool1 = gf.boolean(rec1, rec2, operation="or", layer=(1, 0))
    points = [
        (0, 0),
        (0.7 * width, 0),
        (size, size - 0.7 * width),
        (size, size),
        (size - 0.7 * width, size),
        (0, 0.7 * width),
    ]
    r3 = gf.Component()
    r3.add_polygon(points=points, layer=(1, 0))
    c << gf.boolean(bool1, r3, operation="or", layer=(1, 0))
    c2 = gf.Component()
    circle2 = c2 << gf.components.circle(radius=width / 2, layer=(2, 0))
    circle2.dmove((size, size))
    c3 = gf.Component()
    c3 << gf.boolean(c, c2, layer1=(1, 0), layer2=(2, 0), operation="not", layer=(1, 0))
    c3.add_port(
        name="E",
        center=[size, size / 2],
        width=size,
        orientation=0,
        layer=(1, 0),
        port_type="structural",
    )
    c3.add_port(
        name="N",
        center=[size / 2, size],
        width=size,
        orientation=90,
        layer=(1, 0),
        port_type="structural",
    )
    return c3


@gf.cell
def _truss_quater_open(width, size):
    c = gf.Component()
    fill = c << _truss_quater_fill(width, size)
    # c2 = gf.Component()
    circle = c << gf.components.circle(radius=width*0.7, layer=(1, 0))

    c3 = gf.Component()
    c3 << gf.boolean(fill, circle, operation="not", layer=(1, 0))
    c3.add_ports(fill.ports)
    return c3


@gf.cell
def _truss_unit(width, size):
    c = gf.Component()
    lb = c << _truss_quater_open(width, size / 2)
    rb = c << _truss_quater_open(width, size / 2)
    rb.connect("E", lb.ports["E"], mirror=True)

    lt = c << _truss_quater_open(width, size / 2)
    lt.connect("N", lb.ports["N"], mirror=True)

    rt = c << _truss_quater_open(width, size / 2)
    rt.connect("N", rb.ports["N"])

    c.add_port(
        name="E",
        center=[size, size / 2],
        width=size,
        orientation=0,
        layer=(1, 0),
        port_type="structural",
    )
    c.add_port(
        name="N",
        center=[size / 2, size],
        width=size,
        orientation=90,
        layer=(1, 0),
        port_type="structural",
    )
    c.add_port(
        name="W",
        center=[0, size / 2],
        width=size,
        orientation=180,
        layer=(1, 0),
        port_type="structural",
    )
    c.add_port(
        name="S",
        center=[size / 2, 0],
        width=size,
        orientation=270,
        layer=(1, 0),
        port_type="structural",
    )

    return c


@gf.cell
def _truss_single(width, size):
    c = gf.Component()
    lb = c << _truss_quater_fill(width, size / 2)
    rb = c << _truss_quater_fill(width, size / 2)
    rb.connect("E", lb.ports["E"], mirror=True)

    lt = c << _truss_quater_fill(width, size / 2)
    lt.connect("N", lb.ports["N"], mirror=True)

    rt = c << _truss_quater_fill(width, size / 2)
    rt.connect("N", rb.ports["N"])

    c.add_port(
        name="E",
        center=[size, size / 2],
        width=size,
        orientation=0,
        layer=(1, 0),
        port_type="structural",
    )
    c.add_port(
        name="N",
        center=[size / 2, size],
        width=size,
        orientation=90,
        layer=(1, 0),
        port_type="structural",
    )
    c.add_port(
        name="W",
        center=[0, size / 2],
        width=size,
        orientation=180,
        layer=(1, 0),
        port_type="structural",
    )
    c.add_port(
        name="S",
        center=[size / 2, 0],
        width=size,
        orientation=270,
        layer=(1, 0),
        port_type="structural",
    )

    return c


@gf.cell
def _truss_corner(width, size):
    c = gf.Component()
    lb = c << _truss_quater_fill(width, size / 2)
    rb = c << _truss_quater_fill(width, size / 2)
    rb.connect("E", lb.ports["E"], mirror=True)

    lt = c << _truss_quater_fill(width, size / 2)
    lt.connect("N", lb.ports["N"], mirror=True)

    rt = c << _truss_quater_open(width, size / 2)
    rt.connect("N", rb.ports["N"])

    c.add_port(
        name="s1",
        center=[size, size / 2],
        width=size,
        orientation=0,
        layer=(1, 0),
        port_type="structural",
    )
    c.add_port(
        name="s2",
        center=[size / 2, size],
        width=size,
        orientation=90,
        layer=(1, 0),
        port_type="structural",
    )

    return c


@gf.cell
def _truss_side(width, size):
    c = gf.Component()
    lb = c << _truss_quater_fill(width, size / 2)
    rb = c << _truss_quater_fill(width, size / 2)
    rb.connect("E", lb.ports["E"], mirror=True)

    lt = c << _truss_quater_open(width, size / 2)
    lt.connect("N", lb.ports["N"], mirror=True)

    rt = c << _truss_quater_open(width, size / 2)
    rt.connect("N", rb.ports["N"])

    c.add_port(
        name="s1",
        center=[size, size / 2],
        width=size,
        orientation=0,
        layer=(1, 0),
        port_type="structural",
    )
    c.add_port(
        name="s2",
        center=[size / 2, size],
        width=size,
        orientation=90,
        layer=(1, 0),
        port_type="structural",
    )
    c.add_port(
        name="s3",
        center=[0, size / 2],
        width=size,
        orientation=180,
        layer=(1, 0),
        port_type="structural",
    )

    return c


@gf.cell
def _truss_one_side(width, size, num: int):
    c = gf.Component()
    if num == 2:
        unit1 = c << _truss_corner(width, size)
        unit2 = c << _truss_corner(width, size)
        unit2.connect("s1", unit1.ports["s1"], mirror=True)
    else:
        start = c << _truss_corner(width, size)
        last = start
        for i in range(num - 2):
            unit = c << _truss_side(width, size)
            unit.connect("s3", last.ports["s1"])
            last = unit
        unit = c << _truss_corner(width, size)
        unit.connect("s1", last.ports["s1"], mirror=True)

    c.add_port(
        name="slot1",
        center=[size / 2, 0],
        width=size,
        orientation=90,
        layer=(1, 0),
        port_type="structural",
    )
    c.add_port(
        name="slot2",
        center=[(num - 1) * size + size / 2, 0],
        width=size,
        orientation=90,
        layer=(1, 0),
        port_type="structural",
    )
    c.add_port(
        name="key1",
        center=[0, size / 2],
        width=size,
        orientation=180,
        layer=(1, 0),
        port_type="structural",
    )
    c.add_port(
        name="key2",
        center=[size * num, size / 2],
        width=size,
        orientation=0,
        layer=(1, 0),
        port_type="structural",
    )

    return c


@gf.cell
def _truss_core(width, size, mxn: tuple[int, int]):
    c = gf.Component()
    c.add_ref(
        _truss_unit(width, size),
        columns=mxn[1],
        rows=mxn[0],
        row_pitch=size,
        column_pitch=size,
    )

    return c


@gf.cell
def truss(width, size, mxn: tuple[int, int]):
    c = gf.Component()
    nrows, ncols = mxn
    if nrows != 1 and ncols != 1:
        frame_col_bt = c << _truss_one_side(width, size, ncols)
        frame_col_tp = c << _truss_one_side(width, size, ncols)
        frame_row_left = c << _truss_one_side(width, size, nrows)
        frame_row_right = c << _truss_one_side(width, size, nrows)
        frame_row_left.connect("key2", frame_col_bt.ports["slot1"])
        frame_row_right.connect("key1", frame_col_tp.ports["slot2"])
        frame_col_tp.connect("key1", frame_row_left.ports["slot1"], mirror=True)

        has_core = False
        if nrows > 2 and ncols > 2:
            has_core = True
        if has_core:
            core = c << _truss_core(width, size, (nrows - 2, ncols - 2))
            core.dmove((size, size))
    elif nrows == 1:
        start = c << _truss_single(width, size)
        last = start
        for i in range(ncols - 1):
            unit = c << _truss_single(width, size)
            unit.connect("W", last.ports["E"])
            last = unit
    elif ncols == 1:
        start = c << _truss_single(width, size)
        last = start
        for i in range(nrows - 1):
            unit = c << _truss_single(width, size)
            unit.connect("S", last.ports["N"])
            last = unit

    height = size * nrows
    width = size * ncols

    c.add_port(
        name="W1",
        center=(0, height / 2),
        width=1,
        orientation=180,
        layer="WG",
        port_type="placement",
    )
    c.add_port(
        name="E1",
        center=(width, height / 2),
        width=1,
        orientation=0,
        layer="WG",
        port_type="placement",
    )
    c.add_port(
        name="S1",
        center=(width / 2, 0),
        width=1,
        orientation=270,
        layer="WG",
        port_type="placement",
    )
    c.add_port(
        name="N1",
        center=(width / 2, height),
        width=1,
        orientation=90,
        layer="WG",
        port_type="placement",
    )

    return c
