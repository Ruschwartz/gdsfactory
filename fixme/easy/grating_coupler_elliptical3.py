from typing import Tuple, Optional

import numpy as np

import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.geometry.functions import DEG2RAD
from gdsfactory.tech import LAYER
from gdsfactory.types import Layer, Floats
from gdsfactory.components.grating_coupler_elliptical import (
    grating_tooth_points,
    grating_taper_points,
)


@gf.cell
def grating_coupler_elliptical_arbitrary(
    wg_width: float = 0.5,
    taper_length: float = 16.6,
    taper_angle: float = 60.0,
    wavelength: float = 1.554,
    fiber_angle: float = 15.0,
    grating_line_widths: Floats = [0.343] * 26,
    grating_line_gaps: Floats = [0.343] * 26,
    neff: float = 2.638,  # tooth effective index
    nclad: float = 1.443,
    layer: Tuple[int, int] = LAYER.WG,
    big_last_tooth: bool = False,
    layer_slab: Optional[Tuple[int, int]] = LAYER.SLAB150,
    polarization: str = "te",
    fiber_marker_width: float = 11.0,
    fiber_marker_layer: Layer = gf.LAYER.TE,
    spiked: bool = True,
) -> Component:
    r"""Grating coupler with parametrization based on Lumerical FDTD simulation.

    The ellipticity is derived from Lumerical knowdledge base

    Args:
        polarization: te or tm
        taper_length: taper length from input
        taper_angle: grating flare angle
        wavelength: grating transmission central wavelength (um)
        fiber_angle: fibre polish angle in degrees
        grating_line_width
        wg_width: waveguide width
        neff: tooth effective index
        layer: LAYER.WG
        p_start: period start first grating teeth
        n_periods: number of periods
        big_last_tooth: adds a big_last_tooth
        layer_slab
        fiber_marker_width
        fiber_marker_layer
        nclad
        spiked: grating teeth have sharp spikes to avoid non-manhattan drc errors


    .. code::

                      fiber

                   /  /  /  /
                  /  /  /  /
                _|-|_|-|_|-|___
        WG  o1  ______________|
    """

    # Compute some ellipse parameters
    sthc = np.sin(fiber_angle * DEG2RAD)
    d = neff ** 2 - nclad ** 2 * sthc ** 2
    a1 = wavelength * neff / d
    b1 = wavelength / np.sqrt(d)
    x1 = wavelength * nclad * sthc / d

    a1 = round(a1, 3)
    b1 = round(b1, 3)
    x1 = round(x1, 3)

    # https://en.wikipedia.org/wiki/Ellipse
    c = (a1 ** 2 - b1 ** 2) ** 0.5

    # e = (1 - (b1 / a1) ** 2) ** 0.5
    # print(e)

    c = gf.Component()
    c.info.polarization = polarization
    c.info.wavelength = wavelength

    xi = taper_length
    for grating_line_width, grating_line_gap in zip(
        grating_line_widths, grating_line_gaps
    ):
        p = xi / a1
        pts = grating_tooth_points(
            p * a1, p * b1, p * x1, grating_line_width, taper_angle, spiked=spiked
        )
        c.add_polygon(pts, layer)
        xi += grating_line_gap + grating_line_width

    # Make the taper
    p = taper_length / a1
    a_taper = p * a1
    b_taper = p * b1
    x_taper = p * x1

    x_output = a_taper + x_taper - taper_length + grating_line_width / 2
    pts = grating_taper_points(
        a_taper, b_taper, x_output, x_taper, taper_angle, wg_width=wg_width
    )
    c.add_polygon(pts, layer)

    if polarization.lower() == "te":
        polarization_marker_layer = gf.LAYER.TE
    else:
        polarization_marker_layer = gf.LAYER.TM

    x = (taper_length + xi) / 2

    circle = gf.components.circle(
        radius=fiber_marker_width / 2, layer=polarization_marker_layer
    )
    circle_ref = c.add_ref(circle)
    circle_ref.movex(x)

    name = f"vertical_{polarization.lower()}"
    c.add_port(
        name=name,
        midpoint=[x, 0],
        width=fiber_marker_width,
        orientation=0,
        layer=fiber_marker_layer,
        port_type=name,
    )

    # Add port
    c.add_port(
        name="o1", midpoint=[x_output, 0], width=wg_width, orientation=180, layer=layer
    )

    if layer_slab:
        _rl = xi + grating_line_width + 2.0
        _rhw = _rl * np.tan(fiber_angle * DEG2RAD) + 2.0
        c.add_polygon([(0, _rhw), (_rl, _rhw), (_rl, -_rhw), (0, -_rhw)], layer_slab)
    return c


if __name__ == "__main__":
    c = grating_coupler_elliptical_arbitrary(fiber_angle=8)
    c.show()
