import gdsfactory as gf
import math
import numpy as np
import functools
from gdsfactory.generic_tech import LAYER


@gf.cell
def waveguide_inv_extrude(
    width, length, total_width=4, sleeve_layer=(2, 0), core_layer=(1, 0)
):
    c = gf.Component()
    core_sec = gf.Section(
        width=width,
        offset=0,
        layer=core_layer,
        port_names=["o1", "o2"],
        port_types=["optical", "optical"],
    )
    sleeve_up_sec = gf.Section(
        width=(total_width - width) / 2,
        offset=(total_width - width) / 4 + width / 2,
        layer=sleeve_layer,
    )
    sleeve_down_sec = gf.Section(
        width=(total_width - width) / 2,
        offset=-(total_width - width) / 4 - width / 2,
        layer=sleeve_layer,
    )
    cs = gf.CrossSection(sections=[core_sec, sleeve_up_sec, sleeve_down_sec])
    p = gf.path.straight(length=length)
    c << p.extrude(cross_section=cs)
    c.add_port(name="o1", center=[0, 0], width=width, orientation=180, layer=core_layer)
    c.add_port(
        name="o2", center=[length, 0], width=width, orientation=0, layer=core_layer
    )
    return c


@gf.cell
def ring_resonator(
    gap,
    radius,
    length_x,
    length_y,
    cross_section,
    x_span=20,
    bend="bend_euler",
):
    core_layer = cross_section.layer
    c = gf.Component()
    ring_single = gf.components.ring_single(
        cross_section=cross_section,
        gap=gap,
        radius=radius,
        length_y=length_y,
        length_x=length_x,
        bend=bend,
        length_extension=x_span / 2 - length_x / 2,
    )

    ring_top_pos = (
        -length_x / 2,
        radius * 2 + length_y + cross_section.width * 3 / 2 + gap,
    )
    c << ring_single
    c.ports = ring_single.ports
    c.add_port(
        name="p1",
        center=ring_top_pos,
        width=1,
        orientation=90,
        layer=core_layer,
        port_type="placement",
    )

    with_sleeve = False
    section_names = set([section.name for section in cross_section.sections])
    if "sleeve" in section_names:
        with_sleeve = True

    if with_sleeve:

        section_layers = set([section.layer for section in cross_section.sections])
        section_layers.remove(core_layer)
        sleeve_layer = list(section_layers)[0]
        c2 = gf.Component()
        c2 << gf.boolean(
            c, c, "or", layer=core_layer, layer1=core_layer, layer2=core_layer
        )
        c2 << gf.boolean(
            c, c, "not", layer=sleeve_layer, layer1=sleeve_layer, layer2=core_layer
        )
        c2.ports = c.ports
        return c2
    else:
        return c


@gf.cell
def adiabatic_resonator(
    radius, angle, x_span, gap, cross_section, core_layer="WG", sleeve_layer="DEEP_ETCH"
):
    def create_Bezier(theta, r):
        n1 = np.array([1, 0])
        n2 = np.array([0, 1])
        theta = math.radians(theta)
        t_alpha = math.sin(math.atan(1 / math.tan(theta) ** (1 / 4))) ** 2
        l = (
            2
            * r
            * (t_alpha * (1 - t_alpha))
            / (3 * (t_alpha**4 + (1 - t_alpha) ** 4) ** (3 / 2))
        )
        p0 = -l * n1
        p3 = l * n2
        p1 = np.array([0, 0])
        p2 = np.array([0, 0])
        q0 = p0
        q1 = t_alpha * p0 + (1 - t_alpha) * p1
        q2 = (
            t_alpha**2 * p0 + 2 * (1 - t_alpha) * t_alpha * p1 + (1 - t_alpha) ** 2 * p2
        )
        q3 = (
            t_alpha**3 * p0
            + 3 * (1 - t_alpha) * t_alpha**2 * p1
            + 3 * (1 - t_alpha) ** 2 * t_alpha * p2
            + (1 - t_alpha) ** 3 * p3
        )
        q0, q1, q2, q3 = tuple(map(tuple, [q0, q1, q2, q3]))

        return bezier_curve(np.linspace(0, 1, 100), [q0, q1, q2, q3])

    def bezier_curve(t, control_points):
        """Returns bezier coordinates.

        Args:
            t: 1D array of points varying between 0 and 1.
            control_points: for the bezier curve.
        """
        from scipy.special import binom

        xs = 0.0
        ys = 0.0
        n = len(control_points) - 1
        for k in range(n + 1):
            ank = binom(n, k) * (1 - t) ** (n - k) * t**k
            xs += ank * control_points[k][0]
            ys += ank * control_points[k][1]

        return np.column_stack([xs, ys])

    tmp = gf.Component()

    bezier_path = create_Bezier(angle, radius)
    p1 = gf.path.straight(length=0.01) + gf.path.Path(bezier_path)
    arc = gf.path.arc(radius=10, angle=180 - 2 * p1.end_angle)
    p = (
        p1
        + arc
        + gf.path.Path(p1.points[::-1]).dmirror()
        + p1
        + arc
        + gf.path.Path(p1.points[::-1]).dmirror()
    )
    resonator = tmp << gf.path.extrude(p, cross_section=cross_section)
    core_width = cross_section.width
    resonator.dmovey(core_width + gap)
    straight = tmp << gf.components.straight(length=x_span, cross_section=cross_section)
    straight.dmovex(-x_span / 2)
    tmp.add_port(name="o1", port=straight.ports["o1"])
    tmp.add_port(name="o2", port=straight.ports["o2"])

    # new_sleeve = gf.boolean(tmp,tmp,layer1=sleeve_layer,layer2=core_layer,operation="not", layer=sleeve_layer)
    new_sleeve = gf.boolean(
        tmp,
        tmp,
        layer1=sleeve_layer,
        layer2=core_layer,
        operation="or",
        layer=sleeve_layer,
    )
    new_sleeve = gf.boolean(
        new_sleeve,
        tmp,
        layer1=sleeve_layer,
        layer2=core_layer,
        operation="not",
        layer=sleeve_layer,
    )

    c = gf.Component()
    # c << tmp.extract([(1, 0)])
    c << new_sleeve
    c.add_ports(tmp.ports)

    return c


@gf.cell
def my_coupler(
    coupler=None,
    waveguide_width=0.43,
    taper_angle=15,
    shallow_layer="SHALLOW_ETCH",
    deep_layer="DEEP_ETCH",
):
    import numpy as np

    c = gf.Component()
    if coupler is None:
        gc = gf.components.grating_coupler_elliptical(
            wavelength=1.55, taper_angle=taper_angle
        )
        layer_slab = "SLAB150"
    else:
        gc = coupler()
        if "layer_slab" in coupler.keywords:
            layer_slab = coupler.keywords["layer_slab"]
        else:
            layer_slab = "SLAB150"

    taper_length = (5 - waveguide_width) / 2 / np.tan(np.deg2rad(taper_angle) / 2)
    taper = gf.components.taper(
        width1=waveguide_width, width2=0.5, length=1, layer=(1, 0), with_two_ports=True
    )
    gc = c << gc
    taper = c << taper
    taper.connect(port="o2", other=gc.ports["o1"])
    c.add_polygon(gf.kdb.DPolygon(c.bbox()).sized((0, 2)), layer=(3, 0))

    c.add_polygon(
        gf.kdb.Region(
            c.extract([gf.get_layer(layer_slab)])
            .get_polygons()[gf.get_layer(layer_slab)][0]
            .sized((200, 0))
        ),
        layer=(8, 0),
    )

    bool1 = gf.boolean(
        c, c, layer1=(8, 0), layer2=(1, 0), operation="not", layer=shallow_layer
    )
    bool2 = gf.boolean(
        c, c, layer1=(3, 0), layer2=layer_slab, operation="not", layer=(4, 0)
    )

    bool3 = gf.boolean(
        bool2, c, layer1=(4, 0), layer2=(1, 0), operation="not", layer=deep_layer
    )

    c2 = gf.Component()
    c2 << bool1
    c2 << bool3
    # c2 << c
    c2.add_ports(taper.ports.filter(orientation=180))
    return c2


@gf.cell
def text_outline(
    text,
    font="Consolas",
    size=10,
    layer="DEEP_ETCH",
    outline_width=1,
    mask_layer=(1, 0),
    with_mask=True,
):
    c = gf.Component()
    t = gf.components.text_freetype(text=text, size=size - 1, layer=layer, font=font)
    c2 = gf.Component()
    for p in t.get_polygons()[gf.get_layer(layer)]:
        c2.add_polygon(p.sized(outline_width * 1000), layer=layer)
    c << gf.boolean(c2, t, "not", layer=layer)
    if with_mask:
        bbox = gf.kdb.DPolygon(c.bbox())
        c.add_polygon(bbox.sized(4), layer=mask_layer)
    return c


@gf.cell
def small_mark_set(layer=(7, 0)):
    c = gf.Component()
    chip_alignment_mark = gf.components.cross(length=40, width=1, layer=layer)
    mark1 = c << chip_alignment_mark
    mark2 = c << chip_alignment_mark
    mark3 = c << chip_alignment_mark
    mark1.dmove((-50, 0))
    mark3.dmove((50, 0))
    return c


@gf.cell
def big_mark_set(seperation=1500, layer=(7, 0)):
    c = gf.Component()
    global_alignment_mark = gf.components.cross(length=1000, width=1, layer=layer)
    mark1 = c << global_alignment_mark
    mark2 = c << global_alignment_mark
    mark3 = c << global_alignment_mark
    mark1.dmove((0, seperation))
    mark3.dmove((0, -seperation))
    (c << text_outline("1", size=100, layer=layer, with_mask=False)).dmove(
        (400, -seperation + 500)
    )
    (c << text_outline("2", size=100, layer=layer, with_mask=False)).dmove((400, 500))
    (c << text_outline("3", size=100, layer=layer, with_mask=False)).dmove(
        (400, seperation + 500)
    )
    return c


@gf.cell
def die_with_alignment_marks(die_size, layers):
    c = gf.Component()
    c << gf.components.die(size=(die_size, die_size), die_name=f"{die_size}*{die_size}")

    for layer in layers:
    
        global_mark_left = c << big_mark_set(layer=layer)
        global_mark_left.dmovex(die_size / 2 + 500)
        global_mark_right = c << big_mark_set(layer=layer)
        global_mark_right.dmovex(-die_size / 2 - 500)
        chip_mark_points = [
            [-die_size / 2 + 1000, die_size / 2 - 1000],
            [die_size / 2 - 1000, die_size / 2 - 1000],
            [die_size / 2 - 1000, -die_size / 2 + 1000],
            [-die_size / 2 + 1000, -die_size / 2 + 1000],
        ]
        for point in chip_mark_points:
            chip_mark = c << small_mark_set(layer=layer)
            chip_mark.dmove(point)
            
    return c


@gf.cell
def ruler_mark(layer1, layer2, base_pitch=2, offset=0.05):
    c = gf.Component()
    long_mark_layer1 = gf.components.rectangle(size=(0.3, 10), layer=layer1)
    short_mark_layer1 = gf.components.rectangle(size=(0.3, 5), layer=layer1)
    long_mark_layer2 = gf.components.rectangle(size=(0.3, 5), layer=layer2)
    short_mark_layer2 = gf.components.rectangle(size=(0.3, 5), layer=layer2)
    for i in range(11):
        if i % 5 == 0:
            (c << long_mark_layer1).dmovex(i * base_pitch)
        (c << short_mark_layer1).dmovex(i * base_pitch)
    for i in range(11):
        if i % 5 == 0:
            (c << long_mark_layer2).dmovex(i * (base_pitch + offset)).dmovey(-10)
        (c << short_mark_layer2).dmovex(i * (base_pitch + offset)).dmovey(-5)
    c2 = gf.Component()
    ref1 = c2 << c
    ref1.dmovex(-0.15)
    ref2 = c2 << c
    ref2.dmovex(-0.15)
    ref2.dmirror_x()
    return c2


@gf.cell
def etch_depth_square(size, layer1, layer2):
    c = gf.Component()
    box_layer1 = gf.components.rectangle(size=size, layer=layer1)
    box_layer2 = gf.components.rectangle(size=size, layer=layer2)
    c << box_layer1
    (c << box_layer2).dmovex(size[0] + 20)
    return c


@gf.cell
def ruler_set():
    c = gf.Component()
    ruler = c << ruler_mark((2, 6), (3, 6))
    ruler_vertical = c << ruler_mark((2, 6), (3, 6))
    ruler_vertical.drotate(90)
    ruler_vertical.dmove((-50, -20))
    return c


@gf.cell
def frame(size=10000, layers=((2, 6))):
    c = gf.Component()
    for layer in layers:
        corner_rt = c << l_corner(layer)
        corner_rb = c << l_corner(layer)
        corner_lt = c << l_corner(layer)
        corner_lb = c << l_corner(layer)

        corner_lb.dmove((-size / 2, -size / 2))
        corner_rb.dmirror_x()
        corner_rb.dmove((size / 2, -size / 2))

        corner_lt.dmirror_y()
        corner_lt.dmove((-size / 2, size / 2))

        corner_rt.dmirror_x()
        corner_rt.dmirror_y()
        corner_rt.dmove((size / 2, size / 2))

    return c


@gf.cell
def l_corner(layer):
    c = gf.Component()
    c << gf.components.rectangle(size=(40, 2), layer=layer)
    c << gf.components.rectangle(size=(2, 40), layer=layer)
    return c
