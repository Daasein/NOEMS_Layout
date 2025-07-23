from typing import Literal
import gdsfactory as gf


def create_deep_etch_mask(
    c,
    method: Literal["bbox", "polygon"] = "polygon",
    mask_offset=1,
    x_off=True,
    y_off=True,
):
    """Creates a deep etch mask by offsetting the polygons."""
    if method == "bbox":
        # use bounding box to create a deep etch mask
        bbox = c.bbox()
        polygon = gf.kdb.DPolygon(bbox).sized(
            (mask_offset if x_off else 0, mask_offset if y_off else 0)
        )
    else:
        polygon = c.get_polygons()[gf.get_layer("WG")][0].sized(
            (mask_offset * 1e3 if x_off else 0, mask_offset * 1e3 if y_off else 0)
        )
    # add an offset polygon to create a deep etch mask (1um offset)
    c.add_polygon(polygon, layer=(39, 0))
    booled = gf.boolean(c, c, "not", "DEEP_ETCH", (39, 0), (1, 0))
    c.remove_layers([(39, 0)])
    c << booled
