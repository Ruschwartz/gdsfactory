from __future__ import annotations

from functools import partial

import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.typings import ComponentSpec, CrossSectionSpec


@gf.cell
def coupler90(
    gap: float = 0.2,
    radius: float = 10.0,
    bend: ComponentSpec = "bend_euler",
    straight: ComponentSpec = "straight",
    cross_section: CrossSectionSpec = "strip",
    cross_section_bend: CrossSectionSpec | None = None,
) -> Component:
    r"""Straight coupled to a bend.

    Args:
        gap: um.
        radius: um.
        straight: for straight.
        bend: bend spec.
        cross_section: cross_section spec.
        cross_section_bend: optional bend cross_section spec.

    .. code::

            o3
             |
            /
           /
       o2_/
       o1___o4

    """
    c = Component()
    x = gf.get_cross_section(cross_section, radius=radius)
    xs_bend = cross_section_bend or cross_section

    bend90 = gf.get_component(
        bend,
        radius=radius,
        cross_section=xs_bend,
    )
    bend_ref = c << bend90
    straight_component = gf.get_component(
        straight,
        cross_section=cross_section,
        length=bend90.ports["o2"].dcenter[0] - bend90.ports["o1"].dcenter[0],
    )
    wg_ref = c << straight_component
    width = x.width

    pbw = bend_ref.ports["o1"]
    bend_ref.dmovey(pbw.dy + gap + width)
    c.add_ports(wg_ref.ports, prefix="wg")
    c.add_ports(bend_ref.ports, prefix="bend")
    c.auto_rename_ports()
    return c


coupler90circular = partial(coupler90, bend="bend_circular")


if __name__ == "__main__":
    c = coupler90(radius=10, cross_section_bend="strip_heater_metal")
    c.show()
