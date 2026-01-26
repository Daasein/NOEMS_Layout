from blocks import create_deep_etch_mask
import gdsfactory as gf

@gf.cell
def taper_rib_to_strip(
    width1: float = 0.43,
    width2: float = 0.43,
    w_slab1: float = 0.43,
    w_slab2: float = 3,
    length: float = 10.0,
) -> gf.Component:
    """Returns a taper from rib waveguide to strip waveguide."""
    c = gf.Component()
    taper = c << gf.components.taper_strip_to_ridge(width1=width1, width2=width2, w_slab1=w_slab1, w_slab2=w_slab2, length=length)
    c << gf.boolean(c,c, 'not', 'SHALLOW_ETCH','SLAB90', 'WG')
    create_deep_etch_mask(c, 'bbox',x_off=False,core_layer=['WG','SLAB90'])
    c.ports = taper.ports
    return c