# %%
import gdsfactory as gf
from blocks import *
from comb_drive_tuning import *
from dowhen import do, when

# %%
def EBL_PL_overlap(c:gf.Component, overlap:float=3) -> gf.Component:
    c_out = gf.Component()
    EBL_reg = c.get_region('DEEP_ETCH',merge=True)
    EBL_reg.insert(c.get_region('WG',merge=True))
    PL_reg = c.get_region('DEEP_ETCH_PL')
    EBL_sized = EBL_reg.sized(-overlap*1000,2)
    
    c_out.add_polygon(PL_reg-EBL_sized, 'DEEP_ETCH_PL')
    c_out.add_ref(c.extract(layers=[l for l in c.layers if gf.get_layer(l) != gf.get_layer('DEEP_ETCH_PL')]))
    
    c_out.ports = c.ports
    return c_out

# %%
def round_inner_corner(c:gf.Component, inner_radius) -> gf.Component:
    c_out = gf.Component()
    reg = c.get_region('WG',merge=True).rounded_corners(r_inner=inner_radius*1000, r_outer=0, n=16)
    c_out.add_polygon(reg, 'WG')
    c_out.add_ref(c.extract(layers=[l for l in c.layers if gf.get_layer(l) != gf.get_layer('WG')]))
    c_out.ports = c.ports
    return c_out

# %%
xs_metal_wire = metal_wire(core_width=10, wire_width=8, mask_offset=5, deep_etch_layer="DEEP_ETCH_PL")
xs_metal_wire_wide = metal_wire(core_width=60, wire_width=50, mask_offset=5 , deep_etch_layer="DEEP_ETCH_PL")
Xtrans = gf.path.transition(cross_section1=xs_metal_wire, cross_section2=xs_metal_wire_wide, width_type="linear",offset_type="linear",)

# %%
p={'WG':3,'PADDING':2,'DEEP_ETCH':1,'DEEP_ETCH_PL':1}

# %%
do("create_deep_etch_mask(c,mask_offset=mask_offset, deep_etch_layer='DEEP_ETCH_PL')").when(electrode,"create_deep_etch_mask").goto("return c")
do("create_deep_etch_mask(c,mask_offset=10, deep_etch_layer='DEEP_ETCH_PL',core_layer='PADDING')").when(pad, 'return c')
do("create_deep_etch_mask(c,'bbox',mask_offset=mask_offset, deep_etch_layer='DEEP_ETCH_PL')").when(beam_fixed_support,"create_deep_etch_mask").goto("for port in rect.ports")

# %%
def doubly_clamped_beam_comb_drive_tuning(
    beam_length = 1000, 
    beam_width = 0.1, 
    spring_length = 100,
    spring_width = 2,
    spring_loop_num = 3, 
    spring_separation = 15,
    combdrive_spacing = 80, 
    movable_base_width = 10,
    fixed_base_width = 30,
    combdrive_array_num_push=5,
    combdrive_array_num_pull=5,
    finger_pair_num =50,
    finger_length=20,
    finger_overlap=5, 
    shaft_height=100,
    shaft_hole_size=(20,2),
    shaft_hole_margin=10,
    electrode_gap = 5,
    mask_offset = 10
    ) -> gf.Component: 
    c = gf.Component()
    spring = spring_5um(spring_length=spring_length,spring_width=spring_width, separation=spring_separation, num_loops=spring_loop_num,mask_offset=mask_offset)
    shaft_width = combdrive_spacing*(combdrive_array_num_push+combdrive_array_num_pull) + spring.info['total_width']*2
    beam = doubly_clamped_beam_with_round_support(width=beam_width, length=beam_length, support_length=[2, 2],create_mask=True, mask_offset=electrode_gap+5)
    shaft = perforated_shaft(width=shaft_width, height=shaft_height,margin=shaft_hole_margin, mask_offset=mask_offset, hole_size=shaft_hole_size)
    
    beam_ref = c << beam
    
    shaft_ref = c.add_ref(shaft)
    shaft_ref.connect('e3',beam_ref.ports['w1'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)

    bfs = beam_fixed_support(size=(250,250),mask_offset=mask_offset,metal_offset=10)
    bfs_ref = c.add_ref(bfs)
    bfs_ref.connect('E1',beam_ref.ports['e1'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
       
    # add springs at 4 corners of the shaft
    spring_se = c << spring
    spring_se.connect(
        'p1',shaft_ref.ports['e4'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True
        ).movex(origin=spring_se.xmax, destination=shaft_ref.xmax)
    spring_ne = c << spring
    spring_ne.connect(
        'p1',shaft_ref.ports['e2'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True,mirror=True
        ).movex(origin=spring_ne.xmax, destination=shaft_ref.xmax)
    spring_nw = c << spring
    spring_nw.connect(
        'p1',shaft_ref.ports['e2'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True,mirror=False
        ).movex(origin=spring_nw.xmin, destination=shaft_ref.xmin)
    spring_sw = c << spring
    spring_sw.connect(
        'p1',shaft_ref.ports['e4'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True,mirror=True
        ).movex(origin=spring_sw.xmin, destination=shaft_ref.xmin)
    
    # add comb drive arrays to the shaft
    finger_spec = partial(combdrive_fingers_5um, finger_length=finger_length, pair_num=finger_pair_num, overlap=finger_overlap)
    comb_array = combdrive_array(finger_spec=finger_spec, movable_base_width=movable_base_width, fixed_base_width=fixed_base_width,mask_offset=mask_offset+5)
    
    total_arrays = combdrive_array_num_push + combdrive_array_num_pull
    usable_span = combdrive_spacing * total_arrays
    start_x = shaft_ref.center[0]- usable_span / 2
    pull_origin_x = start_x
    push_origin_x = start_x + combdrive_array_num_pull * combdrive_spacing - combdrive_spacing/2
    
    ports_ne = []
    ports_se = []
    for i in range(combdrive_array_num_push):
        x_push = push_origin_x + combdrive_spacing * (i + 0.75)
        ports_ne.append(
            gf.Port(name=f'comb_ne_{i}', center=(x_push, shaft_height/2), orientation=90, width=10, layer=gf.get_layer('WG'))
                    )
        ports_se.append(
            gf.Port(name=f'comb_se_{i}', center=(x_push, -shaft_height/2), orientation=270, width=10, layer=gf.get_layer('WG'))
                    )
    
    ports_nw = []
    ports_sw = []
    for i in range(combdrive_array_num_pull):
        x_pull = pull_origin_x + combdrive_spacing * (i + 0.75)
        ports_nw.append(
            gf.Port(name=f'comb_nw_{i}', center=(x_pull, shaft_height/2), orientation=90, width=10, layer=gf.get_layer('WG'))
                    )
        ports_sw.append(
            gf.Port(name=f'comb_sw_{i}', center=(x_pull, -shaft_height/2), orientation=270, width=10, layer=gf.get_layer('WG'))
                    )
    
    comb_array_ref_ne = []
    comb_array_ref_nw = []
    comb_array_ref_se = []
    comb_array_ref_sw = []   
    
    for port in ports_nw:
        comb_nw = c.add_ref(comb_array)
        comb_nw.connect('m', port,allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True,mirror=True)
        comb_array_ref_nw.append(comb_nw)
    for port in ports_ne:
        comb_ne = c.add_ref(comb_array)
        comb_ne.connect('m', port,allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
        comb_array_ref_ne.append(comb_ne)
    for port in ports_sw:
        comb_sw = c.add_ref(comb_array)
        comb_sw.connect('m', port,allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
        comb_array_ref_sw.append(comb_sw)
    for port in ports_se:
        comb_se = c.add_ref(comb_array)
        comb_se.connect('m', port,allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True,mirror=True)
        comb_array_ref_se.append(comb_se)
        
    if comb_array_ref_ne:
        fixed_finger_pad_push = pad(size=(combdrive_array_num_push*combdrive_spacing,250),metal_offset=10)
        fixed_finger_pad_ne = c.add_ref(fixed_finger_pad_push)
        fixed_finger_pad_ne.connect('S1', comb_array_ref_ne[-1].ports['f'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
        fixed_finger_pad_ne.movex(origin=fixed_finger_pad_ne.xmax, destination=comb_array_ref_ne[-1].xmax)
        
        fixed_finger_pad_se = c.add_ref(fixed_finger_pad_push)
        fixed_finger_pad_se.connect('S1', comb_array_ref_se[-1].ports['f'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
        fixed_finger_pad_se.movex(origin=fixed_finger_pad_se.xmax, destination=comb_array_ref_se[-1].xmax)
    
    if comb_array_ref_nw:
        fixed_finger_pad_pull = pad(size=(combdrive_array_num_pull*combdrive_spacing,250),metal_offset=10)
        fixed_finger_pad_nw = c.add_ref(fixed_finger_pad_pull)
        fixed_finger_pad_nw.connect('S1', comb_array_ref_nw[0].ports['f'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
        fixed_finger_pad_nw.movex(origin=fixed_finger_pad_nw.xmax, destination=comb_array_ref_nw[-1].xmax)
        
        fixed_finger_pad_sw = c.add_ref(fixed_finger_pad_pull)
        fixed_finger_pad_sw.connect('S1', comb_array_ref_sw[0].ports['f'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
        fixed_finger_pad_sw.movex(origin=fixed_finger_pad_sw.xmax, destination=comb_array_ref_sw[-1].xmax)
    
    
    
    beam_pad = U_shape_pad(p1_size=(200,500+finger_spec().info['total_length']-spring_length+20), 
                           p2_size=(shaft_width-20,250), 
                           p3_size=(200,300),
                           metal_offset=10)
    beam_pad_n = c.add_ref(beam_pad)
    beam_pad_n.connect(
        'e12', spring_nw.ports['p2'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True
        ).movex(origin=beam_pad_n.center[0], destination=shaft_ref.center[0]).movey(10)
    
    beam_pad_s = c.add_ref(beam_pad)
    beam_pad_s.connect(
        'e12', spring_sw.ports['p2'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True,mirror=True
        ).movex(origin=beam_pad_s.center[0], destination=shaft_ref.center[0]).movey(-10)
    routing_with_mytaper(
        c,
        port1=beam_pad_n.ports['e10'],
        port2=spring_ne.ports['p2'],
        cross_section2=metal_wire(core_width=spring_ne.ports['p2'].width, wire_width=spring_ne.ports['p2'].width-5, mask_offset=mask_offset,deep_etch_layer="DEEP_ETCH_PL"),
        cross_section1=metal_wire(core_width=200, wire_width=180, mask_offset=mask_offset,deep_etch_layer="DEEP_ETCH_PL"),
        tangent_offset=-(beam_pad_n.ports['e10'].center[0]-spring_ne.ports['p2'].center[0]),
        taper_length=150
        )
    routing_with_mytaper(
        c,
        port1=beam_pad_s.ports['e10'],
        port2=spring_se.ports['p2'],
        cross_section2=metal_wire(core_width=spring_se.ports['p2'].width, wire_width=spring_se.ports['p2'].width-5, mask_offset=mask_offset,deep_etch_layer="DEEP_ETCH_PL"),
        cross_section1=metal_wire(core_width=200, wire_width=180, mask_offset=mask_offset,deep_etch_layer="DEEP_ETCH_PL"),
        tangent_offset=+(beam_pad_s.ports['e10'].center[0]-spring_se.ports['p2'].center[0]),
        taper_length=150
        )
    
    
    # add pad connect two big pads together
    pad_w = pad(size=(150, shaft_height+spring_length*2+100), metal_offset=10)
    pad_w_ref = c.add_ref(pad_w)
    pad_w_ref.connect('N1', beam_pad_n.ports['e12'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True).movex(-25)
    
    electrode_section = metal_wire(core_width=beam_length-20, wire_width=beam_length-40, mask_offset=mask_offset,deep_etch_layer="DEEP_ETCH_PL")
    
    electrode_ = electrode(width=beam_length-20, height=10, cross_section=electrode_section,metal_offset=10,mask_offset=mask_offset+5)
    electrode_n = c.add_ref(electrode_)
    v_spacer_n = c << vertical_spacer(length=5)
    v_spacer_n.connect('p1', beam.ports['n1'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
    electrode_n.connect('s1', v_spacer_n.ports['p2'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
    
    electrode_s = c.add_ref(electrode_)
    v_spacer_s = c << vertical_spacer(length=5)
    v_spacer_s.connect('p1', beam.ports['s1'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
    electrode_s.connect('s1', v_spacer_s.ports['p2'],allow_layer_mismatch=True,allow_width_mismatch=True,allow_type_mismatch=True)
    
    actuation_sensing_pad = pad(size=(beam_length-200,500+finger_spec().info['total_length']-spring_length+20), metal_offset=10)
    actuation_sensing_pad_n = c.add_ref(actuation_sensing_pad)
    actuation_sensing_pad_n.move(origin=(actuation_sensing_pad_n.xmax,actuation_sensing_pad_n.ymax), destination=(beam.xmax-20, beam_pad_n.ymax))
    actuation_sensing_pad_redundant = pad(size=(250,500+finger_spec().info['total_length']-spring_length+20), metal_offset=10)
    aspr_ref_n = c.add_ref(actuation_sensing_pad_redundant)
    aspr_ref_n.move(
        origin=(aspr_ref_n.xmin, aspr_ref_n.ymin),
        destination=(actuation_sensing_pad_n.xmin, actuation_sensing_pad_n.ymin)
    )
    pad_section = metal_wire(core_width=beam_length-200, wire_width=beam_length-220, mask_offset=mask_offset,deep_etch_layer="DEEP_ETCH_PL")
    routing_with_mytaper(
        c,
        port1=electrode_n.ports['n1'],
        port2=actuation_sensing_pad_n.ports['S1'],
        cross_section1=electrode_section,
        cross_section2=pad_section,
        tangent_offset=-(actuation_sensing_pad_n.ports['S1'].center[0]-electrode_n.ports['n1'].center[0]),
        taper_length=(actuation_sensing_pad_n.ports['S1'].center[1]-electrode_n.ports['n1'].center[1])
    )
    actuation_sensing_pad_s = c.add_ref(actuation_sensing_pad)
    actuation_sensing_pad_s.move(origin=(actuation_sensing_pad_s.xmax,actuation_sensing_pad_s.ymin), destination=(beam.xmax-20, beam_pad_s.ymin))
    aspr_ref_s = c.add_ref(actuation_sensing_pad_redundant)
    aspr_ref_s.move(
        origin=(aspr_ref_s.xmin, aspr_ref_s.ymax),
        destination=(actuation_sensing_pad_s.xmin, actuation_sensing_pad_s.ymax)
    )
    
    routing_with_mytaper(
        c,
        port1=actuation_sensing_pad_s.ports['N1'],
        port2=electrode_s.ports['n1'],
        cross_section1=pad_section,
        cross_section2=electrode_section,
        tangent_offset=+(actuation_sensing_pad_s.ports['N1'].center[0]-electrode_s.ports['n1'].center[0]),
        taper_length=-(actuation_sensing_pad_s.ports['N1'].center[1]-electrode_s.ports['n1'].center[1])
    )
    
    
    c = round_inner_corner(c, inner_radius=2)
    c = merge_layers_with_priority(c, p)
    c = EBL_PL_overlap(c, overlap=1)
    
    c.info['num_push_combs'] = combdrive_array_num_push*2*finger_pair_num
    c.info['num_pull_combs'] = combdrive_array_num_pull*2*finger_pair_num

    return c
c = doubly_clamped_beam_comb_drive_tuning(
    shaft_height=30, 
    beam_length=1000, 
    finger_pair_num=25,
    finger_length=15,
    combdrive_array_num_push=1, 
    combdrive_array_num_pull=4, 
    spring_length=30, 
    spring_loop_num=1, 
    combdrive_spacing=100)
c.show()


