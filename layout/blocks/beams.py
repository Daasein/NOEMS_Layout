from collections.abc import Sequence
import gdsfactory as gf
import numpy as np
from .utils import create_deep_etch_mask, merge_deep_etch_mask
from .path import smooth_asymmetric
from gdsfactory.typings import LayerSpec


def cantilever_beam(length, width, mask_offset=1, deep_etch_layer="DEEP_ETCH"):
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

    create_deep_etch_mask(c, mask_offset, deep_etch_layer=deep_etch_layer)

    c.flatten()
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

    for port in beam.ports:
        if not port.orientation == 180:
            c.add_ports([port])
    c.add_ports(spring.ports.filter(orientation=180))
    merge_deep_etch_mask(c)
    return c


# @gf.cell
def doubly_clamped_beam_with_round_support(
    width,
    length,
    support_length: float | Sequence[float],
    layer: LayerSpec = "WG",
    create_mask=False,
    mask_offset=1,
):
    def transition_support(w1: float, w2: float, height: float, npoints: int = 10) -> gf.Component:
        # Calculations based on your requirements
        r1 = (w1 - w2) / 2
        r2 = height
        
        # Right side waypoints: Bottom-Right -> Corner -> Top-Right
        # We add a small vertical stem at the bottom and horizontal stem at the top 
        # to ensure the spline has 'room' to breathe if needed.
        right_waypoints = [
            (w1 / 2, 0),
            (w2 / 2, 0),
            (w2 / 2, height)
        ]
        
        # Generate right profile
        right_side = smooth_asymmetric(right_waypoints, r1=r1, r2=r2, npoints=npoints)
        
        # Mirror for left profile
        left_points = right_side.points.copy()
        left_points[:, 0] *= -1  # Flip X coordinates
        
        polygon_points = np.vstack([left_points, right_side.points[::-1]])
        c = gf.Component()
        c.add_polygon(polygon_points,'WG')
        c.add_port(name='W1', center=(0, 0), width=w1, orientation=-90,layer='WG',port_type='placement')
        c.add_port(name='W2', center=(0, height), width=w2, orientation=90,layer='WG',port_type='placement')
        return c
    
    if isinstance(support_length, (int, float)):
        support = transition_support(support_length, width, support_length)
    elif isinstance(support_length, Sequence) and len(support_length) == 2:
        support = transition_support(
            support_length[0], width, support_length[1]
        )
    else:
        raise ValueError("support_length must be a float or a sequence of two floats.")
    
    c = gf.Component()
    beam_pts = [
        (0, -width / 2),
        (length, -width / 2),
        (length, width / 2),
        (0, width / 2),
    ]
    c.add_polygon(beam_pts, layer=layer)
    transition_support_l = c << support
    transition_support_l.connect("W2", gf.Port(name="p1", center=(0, 0), width=width, orientation=180,layer=gf.get_layer(layer),port_type='placement'))
    
    transition_support_r = c << support
    transition_support_r.connect("W2", gf.Port(name="p1", center=(length, 0), width=width, orientation=0,layer=gf.get_layer(layer),port_type='placement'))
    
    c.add_port(
        name='w1',
        port=transition_support_l.ports['W1']
    )
    c.add_port(
        name='e1',
        port=transition_support_r.ports['W1']
    )
    c.add_port(
        name='s1',
        center=(length / 2, -width / 2),
        width=width,
        orientation=270,
        layer=gf.get_layer(layer),
        port_type='placement'
    )    
    c.add_port(
        name='n1',
        center=(length / 2, width / 2),
        width=width,
        orientation=90,
        layer=gf.get_layer(layer),
        port_type='placement'
    )

    if create_mask:
        create_deep_etch_mask(c, method="bbox", mask_offset=mask_offset)
    return c
@gf.cell
def cantilever_beam_with_round_support(
    width,
    length,
    support_length: float | Sequence[float],
    layer: LayerSpec = "WG",
    create_mask=False,
    mask_offset=1,
    deep_etch_layer = "DEEP_ETCH",
):
    """Creates a cantilever beam with round support on one side (fixed end)."""
    def transition_support(w1: float, w2: float, height: float, npoints: int = 10) -> gf.Component:
        # Calculations based on your requirements
        r1 = (w1 - w2) / 2
        r2 = height
        
        # Right side waypoints: Bottom-Right -> Corner -> Top-Right
        right_waypoints = [
            (w1 / 2, 0),
            (w2 / 2, 0),
            (w2 / 2, height)
        ]
        
        # Generate right profile
        right_side = smooth_asymmetric(right_waypoints, r1=r1, r2=r2, npoints=npoints)
        
        # Mirror for left profile
        left_points = right_side.points.copy()
        left_points[:, 0] *= -1  # Flip X coordinates
        
        polygon_points = np.vstack([left_points, right_side.points[::-1]])
        c = gf.Component()
        c.add_polygon(polygon_points,'WG')
        c.add_port(name='W1', center=(0, 0), width=w1, orientation=-90,layer='WG',port_type='placement')
        c.add_port(name='W2', center=(0, height), width=w2, orientation=90,layer='WG',port_type='placement')
        return c
    
    if isinstance(support_length, (int, float)):
        support = transition_support(support_length, width, support_length)
    elif isinstance(support_length, Sequence) and len(support_length) == 2:
        support = transition_support(
            support_length[0], width, support_length[1]
        )
    else:
        raise ValueError("support_length must be a float or a sequence of two floats.")
    
    c = gf.Component()
    beam_pts = [
        (0, -width / 2),
        (length, -width / 2),
        (length, width / 2),
        (0, width / 2),
    ]
    c.add_polygon(beam_pts, layer=layer)
    
    # Only add support on the left side (fixed end)
    transition_support_l = c << support
    transition_support_l.connect("W2", gf.Port(name="p1", center=(0, 0), width=width, orientation=180,layer=gf.get_layer(layer),port_type='placement'))
    
    c.add_port(
        name='w1',
        port=transition_support_l.ports['W1']
    )
    c.add_port(
        name='e1',
        center=(length, 0),
        width=width,
        orientation=0,
        layer=gf.get_layer(layer),
        port_type='placement'
    )
    c.add_port(
        name='s1',
        center=(length / 2, -width / 2),
        width=width,
        orientation=270,
        layer=gf.get_layer(layer),
        port_type='placement'
    )    
    c.add_port(
        name='n1',
        center=(length / 2, width / 2),
        width=width,
        orientation=90,
        layer=gf.get_layer(layer),
        port_type='placement'
    )

    if create_mask:
        create_deep_etch_mask(c, method="bbox", mask_offset=mask_offset, deep_etch_layer=deep_etch_layer)
    return c

if __name__ == "__main__":
    c = cantilever_beam(length=10, width=0.1, mask_offset=0.5)
    c.draw_ports()
    c.show()
