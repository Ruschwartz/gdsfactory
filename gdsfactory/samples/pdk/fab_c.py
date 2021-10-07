"""

"""

from typing import Callable

import pydantic.dataclasses as dataclasses

import gdsfactory as gf
from gdsfactory.add_pins import add_pin_square_inside
from gdsfactory.component import Component
from gdsfactory.cross_section import strip
from gdsfactory.port import select_ports
from gdsfactory.tech import LayerLevel, LayerStack
from gdsfactory.types import Layer


@dataclasses.dataclass(frozen=True)
class LayerMap:
    WG: Layer = (10, 1)
    WG_CLAD: Layer = (10, 2)
    WGN: Layer = (34, 0)
    WGN_CLAD: Layer = (36, 0)
    PIN: Layer = (100, 0)


LAYER = LayerMap()
WIDTH_NITRIDE_OBAND = 0.9
WIDTH_NITRIDE_CBAND = 1.0

select_ports_optical = gf.partial(select_ports, layers_excluded=((100, 0),))


def get_layer_stack_fab_c(thickness: float = 350.0) -> LayerStack:
    """Returns generic LayerStack"""
    return LayerStack(
        layers=[
            LayerLevel(
                name="core",
                layer=(34, 0),
                zmin=0.220 + 0.100,
            ),
            LayerLevel(name="clad", layer=(36, 0)),
        ]
    )


def add_pins(
    component: Component,
    function: Callable = add_pin_square_inside,
    pin_length: float = 0.5,
    port_layer: Layer = LAYER.PIN,
    **kwargs,
) -> None:
    """Add Pin port markers.

    Args:
        component: to add ports
        function:
        pin_length:
        port_layer:
        function: kwargs

    """
    for p in component.ports.values():
        function(
            component=component,
            port=p,
            layer=port_layer,
            label_layer=port_layer,
            pin_length=pin_length,
            **kwargs,
        )


# cross_sections

fabc_nitride_cband = gf.partial(
    strip, width=WIDTH_NITRIDE_CBAND, layer=LAYER.WGN, layers_cladding=(LAYER.WGN_CLAD,)
)
fabc_nitride_oband = gf.partial(
    strip, width=WIDTH_NITRIDE_OBAND, layer=LAYER.WGN, layers_cladding=(LAYER.WGN_CLAD,)
)
fabc_nitride_cband.__name__ = "fab_nitridec"
fabc_nitride_oband.__name__ = "fab_nitrideo"


# LEAF COMPONENTS have pins

mmi1x2_nitride_c = gf.partial(
    gf.components.mmi1x2,
    width=WIDTH_NITRIDE_CBAND,
    width_mmi=3,
    cross_section=fabc_nitride_cband,
    decorator=add_pins,
)
mmi1x2_nitride_o = gf.partial(
    gf.components.mmi1x2,
    width=WIDTH_NITRIDE_OBAND,
    cross_section=fabc_nitride_oband,
    decorator=add_pins,
)
bend_euler_c = gf.partial(
    gf.components.bend_euler, cross_section=fabc_nitride_cband, decorator=add_pins
)
straight_c = gf.partial(
    gf.components.straight, cross_section=fabc_nitride_cband, decorator=add_pins
)
bend_euler_o = gf.partial(
    gf.components.bend_euler, cross_section=fabc_nitride_oband, decorator=add_pins
)
straight_o = gf.partial(
    gf.components.straight, cross_section=fabc_nitride_oband, decorator=add_pins
)

gc_nitride_c = gf.partial(
    gf.components.grating_coupler_elliptical_te,
    grating_line_width=0.6,
    wg_width=WIDTH_NITRIDE_CBAND,
    layer=LAYER.WGN,
    decorator=add_pins,
)

# HIERARCHICAL COMPONENTS made of leaf components

mzi_nitride_c = gf.partial(
    gf.components.mzi,
    cross_section=fabc_nitride_cband,
    splitter=mmi1x2_nitride_c,
    decorator=add_pins,
    straight=straight_c,
    bend=bend_euler_c,
    layer=LAYER.WGN,
)
mzi_nitride_o = gf.partial(
    gf.components.mzi,
    cross_section=fabc_nitride_oband,
    splitter=mmi1x2_nitride_o,
    decorator=add_pins,
    straight=straight_o,
    bend=bend_euler_o,
    layer=LAYER.WGN,
)


# for testing
factory = dict(
    mmi1x2_nitride_c=mmi1x2_nitride_c,
    mmi1x2_nitride_o=mmi1x2_nitride_o,
    bend_euler_c=bend_euler_c,
    straight_c=straight_c,
    mzi_nitride_c=mzi_nitride_c,
    mzi_nitride_o=mzi_nitride_o,
    gc_nitride_c=gc_nitride_c,
)


if __name__ == "__main__":

    mzi = mzi_nitride_c()
    mzi_gc = gf.routing.add_fiber_single(
        component=mzi,
        grating_coupler=gc_nitride_c,
        cross_section=fabc_nitride_cband,
        optical_routing_type=1,
        straight=straight_c,
        bend=bend_euler_c,
        select_ports=select_ports_optical,
    )
    mzi_gc.show()
