import gdsfactory as gf


def cross_section_with_sleeves(
    core_width,
    total_width,
    core_layer="WG",
    sleeve_layer="DEEP_ETCH",
    radius=50,
):
    """Initialize a cross-section with a core and two sleeves."""
    sec1 = gf.Section(
        width=(total_width - core_width) / 2,
        offset=(total_width - core_width) / 4 + core_width / 2,
        layer=sleeve_layer,
    )
    sec2 = gf.Section(
        width=(total_width - core_width) / 2,
        offset=-(total_width - core_width) / 4 - core_width / 2,
        layer=sleeve_layer,
    )
    sec3 = gf.Section(
        width=core_width, offset=0, layer=core_layer, port_names=["o1", "o2"]
    )
    xs = gf.CrossSection(sections=[sec3, sec1, sec2], radius=radius)
    return xs
def cross_section_with_mask(
    core_width,
    total_width,
    core_layer="WG",
    mask_layer="DEEP_ETCH",
    radius=50,
):
    """Initialize a cross-section with a core and one mask."""
    sec1 = gf.Section(
        width=total_width,
        offset=0,
        layer=mask_layer,
        name="mask",
    )
    sec2 = gf.Section(
        width=core_width,
        offset=0,
        layer=core_layer,
        port_names=["o1", "o2"],
        name="core",
    )
    xs = gf.CrossSection(sections=[sec2, sec1], radius=radius)
    return xs