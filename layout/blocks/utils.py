from typing import Callable, Literal, Union
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
def merge_layers_with_priority(
    component: gf.Component,
    priority: dict[str | tuple[int, int], int],
) -> gf.Component:
    """Boolean merge by layer priority.

    Logic Flow:
    1. Pre-processing: Extract all polygons and perform an intra-layer merge to dissolve overlapping shapes within the same layer.
    2. Categorization: Separate layers into those with defined priorities and those without (unspecified).
    3. Priority-based Clipping: Iterate through layers from highest to lowest priority:
        - Subtract the union of all higher-priority shapes from the current layer (Current = Current - Union_of_Higher).
        - This ensures higher-priority layers "cut through" or overlap lower-priority ones without geometric interference.
    4. Composition: Add the clipped prioritized layers and the original unspecified layers into a new output component.
    5. Port Preservation: Copy the ports from the original component to the output.

    Args:
        component: The source component to process.
        priority: Dictionary mapping layers to priority values (higher value = higher priority).example: {'WG': 3, 'PADDING': 2, 'DEEP_ETCH': 1}
    """
    get_layer = gf.get_layer
    polys = component.get_polygons()
    target_layers = [l for l in  polys.keys()]

    # Merge each layer's polygons
    merged_by_layer: dict[tuple[int, int], gf.kdb.Region] = {}
    for lt in target_layers:
        reg = gf.kdb.Region(polys.get(lt, []))
        merged_by_layer[lt] = reg.merged()

    
    priority_map = {get_layer(k): v for k, v in priority.items()}
    layered = {lt: merged_by_layer[lt] for lt in merged_by_layer if lt in priority_map}
    unspecified = {lt: merged_by_layer[lt] for lt in merged_by_layer if lt not in priority_map}

    # Perform boolean merge based on priority
    c_out = gf.Component()
    higher_union = gf.kdb.Region()
    for p in sorted(set(priority_map.values()), reverse=True):
        same_p_layers = [lt for lt, pv in priority_map.items() if pv == p and lt in layered]
        if not same_p_layers:
            continue
        current_union = gf.kdb.Region()
        for lt in same_p_layers:
            reg = layered[lt] - higher_union
            if not reg.is_empty():
                c_out.add_polygon(reg, layer=lt)
                current_union.insert(reg)
        higher_union.insert(current_union)
    
    # Add unspecified layers without merging
    for lt, reg in unspecified.items():
        if not reg.is_empty():
            c_out.add_polygon(reg, layer=lt)
    c_out.ports = component.ports
    return c_out

def labelme(
    c: gf.Component,
    c_tolabel: gf.ComponentReference,
    text: str,
    *,
    text_spec=gf.components.text_freetype,
    position: Union[str, Callable[[gf.ComponentReference], tuple[float, float]], tuple[float, float]] = "center",
    anchor: Literal["SW", "SE", "NW", "NE", "center"] = "center",
) -> gf.ComponentReference:
    """
    Add a text label to a component with flexible position definition.
    
    Args:
        c: The Component where the final label will exist
        c_tolabel: ComponentReference within c that is used to calculate the label position
        text: Text content
        text_spec: Text component specification (function or component), default is text_freetype
        position: Text position, can be:
            - String: "SW", "SE", "NW", "NE", "center" representing relative positions to c_tolabel
            - Callable: Function receiving (c_tolabel, text_ref), returns (x, y) coordinates
            - Tuple: (x, y) absolute coordinates
        anchor: Reference point of text (for move origin), determines the base point when moving text
            - "SW": Bottom-left corner
            - "SE": Bottom-right corner
            - "NW": Top-left corner
            - "NE": Top-right corner
            - "center": Center (default)
    
    Returns:
        ComponentReference: The created and moved text reference in component c
        
    Example:
        # Create component and add rectangle, then label it
        c = gf.Component()
        rect = c << gf.components.rectangle(size=(100, 50))
        
        # Use string position to center text on rect
        label1 = labelme(c, rect, "test", position="center", anchor="center")
        
        # Use callable to dynamically calculate position (top-right of rect)
        def get_label_pos(comp_ref, text_ref):
            return (comp_ref.xmax + 20, comp_ref.ymax)
        
        label2 = labelme(c, rect, "label", position=get_label_pos, anchor="SW")
        
        # Use absolute coordinates
        label3 = labelme(c, rect, "abs", position=(100, 100), anchor="center")
    """
    # Create and add text component to c
    text_ref = c << text_spec(text=text)
    
    # Determine anchor point coordinates (text's reference point)
    anchor_map = {
        "SW": (text_ref.xmin, text_ref.ymin),
        "SE": (text_ref.xmax, text_ref.ymin),
        "NW": (text_ref.xmin, text_ref.ymax),
        "NE": (text_ref.xmax, text_ref.ymax),
        "center": text_ref.center,
    }
    anchor_point = anchor_map[anchor]
    
    # Calculate destination position
    if callable(position):
        # If position is callable, pass c_tolabel and text_ref to get coordinates
        destination = position(c_tolabel)
    elif isinstance(position, str):
        # If position is string, generate coordinates from c_tolabel's corners or center
        c_anchor_map = {
            "SW": (c_tolabel.xmin, c_tolabel.ymin),
            "SE": (c_tolabel.xmax, c_tolabel.ymin),
            "NW": (c_tolabel.xmin, c_tolabel.ymax),
            "NE": (c_tolabel.xmax, c_tolabel.ymax),
            "center": c_tolabel.center,
        }
        destination = c_anchor_map[position]
    else:
        # Otherwise assume it's a coordinate tuple
        destination = position
    
    # Move text using move (origin is reference point, destination is target point)
    text_ref.move(origin=anchor_point, destination=destination)
    
    return text_ref