import gdsfactory as gf

from functools import partial
from .spacer import vertical_spacer
from .beams import cantilever_beam
from .mylib import ring_resonator
from .cross_section import cross_section_with_sleeves


@gf.cell
def resonator_with_beam(resonator_spec, beam_spec, gap=0.1):
    c = gf.Component()
    resonator = c << resonator_spec()
    beam = c << beam_spec()
    spacer = c << vertical_spacer(gap)

    spacer.connect("p1", resonator.ports["p1"])
    beam.connect("s1", spacer.ports["p2"])

    c.add_ports(beam.ports)
    c.add_ports(resonator.ports)

    booled_deepetch = gf.boolean(c, c, "not", "DEEP_ETCH", "DEEP_ETCH", "WG")
    c.remove_layers(["DEEP_ETCH"])
    c << booled_deepetch
    return c


if __name__ == "__main__":
    cs = cross_section_with_sleeves(0.43, 5)
    resonator_spec = partial(
        ring_resonator,
        radius=10,
        length_y=0,
        length_x=5,
        gap=0.1,
        cross_section=cs,
        total_width=10,
        bend="bend_circular",
    )
    cantilever_spec = partial(cantilever_beam, length=10, width=0.13)
    c = resonator_with_beam(resonator_spec, cantilever_spec, gap=0.1)
    c.draw_ports()
    c.show()
