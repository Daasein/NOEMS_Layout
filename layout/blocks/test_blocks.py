import gdsfactory as gf
from functools import partial
from .mylib import waveguide_inv_extrude
from .cross_section import cross_section_with_sleeves
from .taper import taper_rib_to_strip


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

@gf.cell
def euler_test(n,grating_coupler_spec,cross_section):
    
    def bend180(bend90):
        c = gf.Component()
        b1 = c << bend90
        b2 = c << bend90
        b2.connect('o1',b1.ports['o2'])
        # c << bend180
        c.add_port(name='o1', port=b1.ports['o1'])
        c.add_port(name='o2', port=b2.ports['o2'])
        return c
    bend90 = gf.components.bend_euler(cross_section=cross_section,angle=90)
    bend180 = bend180(bend90)
    straight = gf.components.straight(length=50, cross_section=cross_section)
    c = gf.Component()
    gc_ref = (c << grating_coupler_spec()).rotate(180)
    straight_ref = c << straight
    straight_ref.connect("o1",gc_ref.ports["o1"])
    b90_ref = c << bend90
    b90_ref.connect("o1",straight_ref.ports["o2"])
    for i in range(2*n-1):
        b180_ref = c << bend180
        if i==0:
            b180_ref.connect("o1",b90_ref.ports["o2"], mirror=True)
        elif i%2==1:
            b180_ref.connect("o1",prev_b180_ref.ports["o2"])
        else:
            b180_ref.connect("o1",prev_b180_ref.ports["o2"],mirror=True)
        prev_b180_ref = b180_ref
    b90_end = c << bend90
    b90_end.connect("o1",prev_b180_ref.ports["o2"])
    straight_end = c << straight
    straight_end.connect("o1",b90_end.ports["o2"])
    gc_end = c << grating_coupler_spec()
    gc_end.connect("o1",straight_end.ports["o2"])
    c.info['num_bends'] = (2*n-1)*2 + 2
    return c
@gf.cell
def circular_bend_test(n,radius,grating_coupler_spec,cross_section):
    
    def bend180(bend90):
        c = gf.Component()
        b1 = c << bend90
        b2 = c << bend90
        b2.connect('o1',b1.ports['o2'])
        # c << bend180
        c.add_port(name='o1', port=b1.ports['o1'])
        c.add_port(name='o2', port=b2.ports['o2'])
        return c
    bend90 = gf.components.bend_circular(radius=radius,cross_section=cross_section,angle=90)
    bend180 = bend180(bend90)
    straight = gf.components.straight(length=50, cross_section=cross_section)
    c = gf.Component()
    gc_ref = (c << grating_coupler_spec()).rotate(180)
    straight_ref = c << straight
    straight_ref.connect("o1",gc_ref.ports["o1"])
    b90_ref = c << bend90
    b90_ref.connect("o1",straight_ref.ports["o2"])
    for i in range(2*n-1):
        b180_ref = c << bend180
        if i==0:
            b180_ref.connect("o1",b90_ref.ports["o2"], mirror=True)
        elif i%2==1:
            b180_ref.connect("o1",prev_b180_ref.ports["o2"])
        else:
            b180_ref.connect("o1",prev_b180_ref.ports["o2"],mirror=True)
        prev_b180_ref = b180_ref
    b90_end = c << bend90
    b90_end.connect("o1",prev_b180_ref.ports["o2"])
    straight_end = c << straight
    straight_end.connect("o1",b90_end.ports["o2"])
    gc_end = c << grating_coupler_spec()
    gc_end.connect("o1",straight_end.ports["o2"])
    c.info['num_bends'] = (2*n-1)*2 + 2
    return c


@gf.cell
def spiral_test(grating_coupler_spec,cross_section):
    '''Creates a component with multiple spirals of different lengths,
       Use xs = cross_section_with_sleeves(core_width=0.43, total_width=5, radius=50,radius_min=10)
       The length is fixed to be 2000, 9100, 15000, and 35000 um,
    '''
    c = gf.Component()
    spiral_list = [
        gf.components.spiral_racetrack_fixed_length(cross_section=cross_section,length=2000,n_straight_sections=4,in_out_port_spacing=600),
        gf.components.spiral_racetrack_fixed_length(cross_section=cross_section,length=9100,n_straight_sections=22,in_out_port_spacing=600),
        gf.components.spiral_racetrack_fixed_length(cross_section=cross_section,length=15000,n_straight_sections=34,in_out_port_spacing=600),
        gf.components.spiral_racetrack_fixed_length(cross_section=cross_section,length=35000,n_straight_sections=64,in_out_port_spacing=600)
    ]
    straight_100 = gf.components.straight(length=100, cross_section=cross_section)
    for i, spiral in enumerate(spiral_list):
        gc = grating_coupler_spec()
        gc_ref = (c << gc).rotate(180)
        spiral_ref = c << spiral
        # create a 100um straight from 1st gc.
        straight_100_ref = c << straight_100
        straight_100_ref.connect("o1",gc_ref.ports["o1"])
        spiral_ref.connect("o1",straight_100_ref.ports["o2"], mirror=False if spiral_ref.ports['o1'].y<0 else True)
        gc_end = c << gc
        gc_end.connect("o1",spiral_ref.ports["o2"])
        # add a pair of reference gratings and straights below
        gc2_ref = (c << gc).rotate(180).movey(-200)
        gc2_end = c << gc
        gc2_end.move(gc2_end.center, gc_end.center).movey(-200)
        straight_ref = c << gf.components.straight(length=-gc2_ref.ports['o1'].x + gc2_end.ports['o1'].x, cross_section=cross_section)
        straight_ref.connect("o1",gc2_ref.ports["o1"])
        
        [item.move((1000*(i%2),-700*(i//2))) for item in [gc_ref, spiral_ref, gc_end, gc2_ref, gc2_end,straight_ref,straight_100_ref]]
    c.info["Spiral lengths"] = [2100, 9200, 15100, 35100]
    return c

@gf.cell
def converter_test(grating_coupler_spec, wg_width=0.43, slab_width=6, taper_length=20, num_taper_pair=2,deep_etch_layer="DEEP_ETCH"):
    c = gf.Component()
    gc = grating_coupler_spec()
    gc_ref = (c << gc).rotate(180)
    xs_rib = cross_section_with_sleeves(core_width=wg_width, total_width=slab_width, sleeve_layer=deep_etch_layer)
    straight = gf.components.straight(length=10, cross_section=xs_rib)
    prev_straight = gc_ref
    for i in range(num_taper_pair):
        taper1 = c << taper_rib_to_strip(width1=wg_width,width2=wg_width,w_slab1=wg_width,w_slab2=slab_width,length=taper_length,deep_etch_layer=deep_etch_layer)
        taper1.connect("o2",prev_straight.ports["o1"] if i==0 else prev_straight.ports["o2"])
        straight_mid_ref =c << straight
        straight_mid_ref.connect("o1",taper1.ports["o1"])
        taper2 = c << taper_rib_to_strip(width1=wg_width,width2=wg_width,w_slab1=wg_width,w_slab2=slab_width,length=taper_length,deep_etch_layer=deep_etch_layer)
        taper2.connect("o1",straight_mid_ref.ports["o2"])
        if i != num_taper_pair-1:
            straight_post = c << straight
            straight_post.connect("o1",taper2.ports["o2"])
            prev_straight = straight_post
        else:
            prev_straight = taper2
    gc_end = c << gc
    gc_end.connect("o1",prev_straight.ports["o2"])
    return c

@gf.cell
def converter_test_array(converter_test_spec, pair_num_list=[20,40,60,80], deep_etch_layer="DEEP_ETCH"):
    c = gf.Component()
    for i, pair_num in enumerate(pair_num_list):
        inst = c << converter_test_spec(num_taper_pair=pair_num, deep_etch_layer=deep_etch_layer)
        inst.movey(-120*i)
    c.info['pair_num_list'] = pair_num_list
    return c

@gf.cell
def euler_bend_test_array(bend_spec, n_bend_list=[5,10,15]):
    c = gf.Component()
    for i, n_bend in enumerate(n_bend_list):
        inst = c << bend_spec(n=n_bend)
        inst.movey(-200*i)
    c.info['n_bend_list'] = n_bend_list
    return c

