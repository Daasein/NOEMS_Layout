import gdsfactory as gf
from gdsfactory.typings import CrossSectionSpec, LayerSpec


@gf.cell
def stair(w_list, h_list, layer: LayerSpec = "WG"):

    if len(w_list) != len(h_list):
        raise ValueError("Width and height lists must have the same length")

    points = [(0, 0)]  # start at origin
    x_sum, y_sum = 0, 0

    for wi, hi in zip(w_list, h_list):
        points.append((x_sum, y_sum + hi))  # vertical move
        y_sum += hi
        points.append((x_sum + wi, y_sum))  # horizontal move
        x_sum += wi

    points.append((x_sum, 0))  # return to x-axis

    c = gf.Component()
    c.add_polygon(points=points, layer=layer)
    return c
