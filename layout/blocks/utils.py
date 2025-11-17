from typing import Literal
import gdsfactory as gf


def create_deep_etch_mask(
    c,
    method: Literal["bbox", "polygon"] = "polygon",
    mask_offset=1,
    x_off=True,
    y_off=True,
    deep_etch_layer = "DEEP_ETCH",
    core_layer: str|tuple|list = "WG",
):
    """Creates a deep etch mask by offsetting the polygons."""
    tmp_deep_layer = (3,7)
    tmp_core_layer = (1,7)
    
    c_tmp = gf.Component()
    if isinstance(core_layer, list):
        layer_list = [gf.get_layer(layer) for layer in core_layer]
        polygons = {layer: poly_list for layer, poly_list in c.get_polygons().items() if layer in layer_list}
        # combine all polygons to temp layer
        for layer, poly_list in polygons.items():
            for poly in poly_list:
                c_tmp.add_polygon(poly, layer=tmp_core_layer)
    else:
        c_tmp << c.extract([gf.get_layer(core_layer)])
        c_tmp.remap_layers({core_layer: tmp_core_layer},recursive=True)
        
    if method == "bbox":
        # use bounding box to create a deep etch mask
        bbox = c.bbox()
        polygon = gf.kdb.DPolygon(bbox).sized(
            (mask_offset if x_off else 0, mask_offset if y_off else 0)
        )
        c_tmp.add_polygon(polygon, layer=tmp_deep_layer)

    else:
        if not isinstance(core_layer, list):
            polygon = c.get_polygons()[gf.get_layer(core_layer)][0].sized(
                (mask_offset * 1e3 if x_off else 0, mask_offset * 1e3 if y_off else 0)
            )
        else:
            polygon = c_tmp.get_polygons()[gf.get_layer(tmp_core_layer)][0].sized(
                (mask_offset * 1e3 if x_off else 0, mask_offset * 1e3 if y_off else 0)
            )
        c_tmp.add_polygon(polygon, layer=tmp_deep_layer)
            
    # add an offset polygon to create a deep etch mask (1um offset)
    
    
    booled = gf.boolean(c_tmp, c_tmp, "not", deep_etch_layer, tmp_deep_layer, tmp_core_layer)
    c << booled


def merge_deep_etch_mask(c) -> None:
    return None
    booled_deepetch = gf.boolean(c, c, "not", "DEEP_ETCH", "DEEP_ETCH", "WG")
    c.remove_layers(["DEEP_ETCH"])
    c << booled_deepetch


def tmp_merge_deep_etch_mask(c) -> gf.Component:
    """Temporary function to merge deep etch mask."""
    new_c = gf.Component()
    booled_deepetch = gf.boolean(c, c, "not", "DEEP_ETCH", "DEEP_ETCH", "WG")
    new_c << booled_deepetch
    layers_extract = [layer for layer in c.layers if gf.get_layer(layer) != gf.get_layer("DEEP_ETCH")]
    new_c << c.extract(layers=layers_extract)
    
    new_c.ports = c.ports
    return new_c

    # c.remove_layers(["DEEP_ETCH"])
    # c << booled_deepetch
