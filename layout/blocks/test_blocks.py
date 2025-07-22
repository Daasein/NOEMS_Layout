import gdsfactory as gf
from functools import partial
from .mylib import waveguide_inv_extrude


@gf.cell
def _device_with_io(device_spec, coupler_spec, pitch, lateral_offset=0, cs=None):
    c = gf.Component()
    device = c << device_spec()
    coupler_left = c << coupler_spec()
    coupler_right = c << coupler_spec()
    coupler_left.dmirror_x()
    coupler_left.dmovex(-pitch / 2)
    coupler_right.dmovex(pitch / 2)
    device.movey(lateral_offset)
    route_left = gf.routing.route_single(
        c, coupler_left.ports["o1"], device.ports["o1"], cross_section=cs
    )
    route_right = gf.routing.route_single(
        c, coupler_right.ports["o1"], device.ports["o2"], cross_section=cs
    )
    return c


@gf.cell
def grating_coupler_test_block(gc_spec, cross_section):
    extrude_wg = partial(
        waveguide_inv_extrude,
        width=0.43,
        length=50,
        total_width=10,
        sleeve_layer="DEEP_ETCH",
        core_layer="WG",
    )
    c = gf.Component()
    wg_3k = c << _device_with_io(extrude_wg, gc_spec, pitch=3000, cs=cross_section)
    wg_2k = c << _device_with_io(extrude_wg, gc_spec, pitch=2000, cs=cross_section)
    wg_1k = c << _device_with_io(extrude_wg, gc_spec, pitch=1000, cs=cross_section)
    wg_2k.movey(100)
    wg_2k.movex(-500)
    wg_1k.movey(200)
    wg_1k.movex(-1000)
    wg_1_5k = c << _device_with_io(extrude_wg, gc_spec, pitch=1500, cs=cross_section)
    wg_1_5k.movey(200)
    wg_1_5k.movex(750)
    wg_500 = c << _device_with_io(extrude_wg, gc_spec, pitch=500, cs=cross_section)
    wg_500.movey(100)
    wg_500.movex(1250)
    wg_3k_bend = c << _device_with_io(
        extrude_wg, gc_spec, pitch=3000, lateral_offset=500, cs=cross_section
    )
    wg_3k_bend.movey(300)
    wg_2k_bend = c << _device_with_io(
        extrude_wg, gc_spec, pitch=2000, lateral_offset=400, cs=cross_section
    )
    wg_2k_bend.move((-300, 300))
    wg_1k_bend = c << _device_with_io(
        extrude_wg, gc_spec, pitch=1000, lateral_offset=300, cs=cross_section
    )
    wg_1k_bend.move((-600, 300))

    # c.flatten()
    return c
