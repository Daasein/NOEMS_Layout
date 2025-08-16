from itertools import chain
from math import ceil, floor
import gdsfactory as gf


@gf.cell
def combdrive_fingers(
    fingers: int = 4,
    finger_length: float | int = 20.0,
    finger_gap: float | int = 2.0,
    thickness: float | int = 5.0,
    base_thickness: float | int = 3.0,
    a_c: float | int = 3.0,
    layer="WG",
):
    c = gf.Component()

    width = 2 * base_thickness + finger_length + a_c  # total length
    height = fingers * thickness + (fingers - 1) * finger_gap  # total height
    points_1 = [
        (0, 0),
        (0, height),
        (base_thickness + finger_length, height),
        (base_thickness + finger_length, height - thickness),
        (base_thickness, height - thickness),
        *chain.from_iterable(
            (
                (base_thickness, height - (2 * i) * (thickness + finger_gap)),
                (
                    base_thickness + finger_length,
                    height - (2 * i) * (thickness + finger_gap),
                ),
                (
                    base_thickness + finger_length,
                    height - (2 * i) * (thickness + finger_gap) - thickness,
                ),
                (
                    base_thickness,
                    height - (2 * i) * (thickness + finger_gap) - thickness,
                ),
            )
            for i in range(ceil(fingers / 2))
        ),
        (base_thickness, 0),
        (0, 0),
    ]

    points_2 = [
        (width, 0),
        (width, height),
        (width - base_thickness, height),
        *chain.from_iterable(
            (
                (
                    width - base_thickness,
                    height - (1 + 2 * i) * thickness - (1 + 2 * i) * finger_gap,
                ),
                (
                    width - (base_thickness + finger_length),
                    height - (1 + 2 * i) * thickness - (1 + 2 * i) * finger_gap,
                ),
                (
                    width - (base_thickness + finger_length),
                    height - (2 + 2 * i) * thickness - (1 + 2 * i) * finger_gap,
                ),
                (
                    width - base_thickness,
                    height - (2 + 2 * i) * thickness - (1 + 2 * i) * finger_gap,
                ),
            )
            for i in range(floor(fingers / 2))
        ),
        (width - base_thickness, 0),
        (width, 0),
    ]

    c.add_polygon(points_1, layer=layer)
    c.add_polygon(points_2, layer=layer)
    c.add_port(
        name="w1",
        center=(0, height / 2),
        width=thickness,
        orientation=180,
        layer=layer,
        port_type="placement",
    )
    c.add_port(
        name="e1",
        center=(width, height / 2),
        width=thickness,
        orientation=0,
        layer=layer,
        port_type="placement",
    )
    return c
