from typing import Callable, List, Optional, Tuple, Union

import numpy as np
from numpy import float64, ndarray

from gdsfactory.components.bend_euler import bend_euler
from gdsfactory.components.straight import straight
from gdsfactory.components.taper import taper as taper_function
from gdsfactory.cross_section import strip
from gdsfactory.port import Port
from gdsfactory.routing.manhattan import remove_flat_angles, round_corners
from gdsfactory.routing.utils import get_list_ports_angle
from gdsfactory.types import Coordinate, Coordinates, CrossSectionFactory, Number, Route


def _is_vertical(segment: Coordinate, tol: float = 1e-5) -> bool:
    p0, p1 = segment
    return abs(p0[0] - p1[0]) < tol


def _is_horizontal(segment: Coordinate, tol: float = 1e-5) -> bool:
    p0, p1 = segment
    return abs(p0[1] - p1[1]) < tol


def _segment_sign(s: Coordinate) -> Number:
    p0, p1 = s
    if _is_vertical(s):
        return np.sign(p1[1] - p0[1])

    if _is_horizontal(s):
        return np.sign(p1[0] - p0[0])


def get_ports_x_or_y_distances(
    list_ports: List[Port], ref_point: Coordinate
) -> List[Number]:
    if not list_ports:
        return []

    angle = get_list_ports_angle(list_ports)
    x0 = ref_point[0]
    y0 = ref_point[1]
    if angle in [0, 180]:
        xys = [p.y - y0 for p in list_ports]
    else:
        xys = [p.x - x0 for p in list_ports]
    return xys


def _distance(port1, port2):
    if hasattr(port1, "x"):
        x1, y1 = port1.x, port1.y
    else:
        x1, y1 = port1[0], port1[1]

    if hasattr(port2, "x"):
        x2, y2 = port2.x, port2.y
    else:
        x2, y2 = port2[0], port2[1]

    dx = x1 - x2
    dy = y1 - y2

    return np.sqrt(dx ** 2 + dy ** 2)


def get_bundle_from_waypoints(
    ports1: List[Port],
    ports2: List[Port],
    waypoints: Coordinates,
    straight_factory: Callable = straight,
    taper_factory: Callable = taper_function,
    bend_factory: Callable = bend_euler,
    sort_ports: bool = True,
    cross_section: CrossSectionFactory = strip,
    **kwargs,
) -> List[Route]:
    """Returns list of routes that connect bundle of ports with bundle of routes
    where routes follow a list of waypoints.

    Args:
        ports1: list of ports
        ports2: list of ports
        waypoints: list of points defining a route
        straight_factory: function that returns straights
        taper_factory: function that returns tapers
        bend_factory: function that returns bends
        sort_ports: sorts ports
        cross_section: cross_section
        **kwargs

    """
    if len(ports2) != len(ports1):
        raise ValueError(
            f"Number of start ports should match number of end ports.\
        Got {len(ports1)} {len(ports2)}"
        )

    for p in ports1:
        p.angle = int(p.angle) % 360

    for p in ports2:
        p.angle = int(p.angle) % 360

    start_angle = ports1[0].orientation
    end_angle = ports2[0].orientation
    waypoints = [ports1[0].midpoint] + list(waypoints) + [ports2[0].midpoint]

    # Sort the ports such that the bundle connect the correct corresponding ports.
    angles_to_sorttypes = {
        (0, 180): ("Y", "Y"),
        (0, 90): ("Y", "X"),
        (0, 0): ("Y", "-Y"),
        (0, 270): ("Y", "-X"),
        (90, 0): ("X", "Y"),
        (90, 90): ("X", "-X"),
        (90, 180): ("X", "-Y"),
        (90, 270): ("X", "X"),
        (180, 90): ("Y", "-X"),
        (180, 0): ("Y", "Y"),
        (180, 270): ("Y", "X"),
        (180, 180): ("Y", "-Y"),
        (270, 90): ("X", "X"),
        (270, 270): ("X", "-X"),
        (270, 0): ("X", "-Y"),
        (270, 180): ("X", "Y"),
    }

    dict_sorts = {
        "X": lambda p: p.x,
        "Y": lambda p: p.y,
        "-X": lambda p: -p.x,
        "-Y": lambda p: -p.y,
    }
    key = (start_angle, end_angle)
    sp_st, ep_st = angles_to_sorttypes[key]
    start_port_sort = dict_sorts[sp_st]
    end_port_sort = dict_sorts[ep_st]

    if sort_ports:
        ports1.sort(key=start_port_sort)
        ports2.sort(key=end_port_sort)

    routes = _generate_manhattan_bundle_waypoints(
        ports1=ports1, ports2=ports2, waypoints=list(waypoints), **kwargs
    )

    x = cross_section(**kwargs)
    bends90 = [bend_factory(cross_section=cross_section, **kwargs) for p in ports1]

    if taper_factory and x.info.get("auto_widen", True):
        if callable(taper_factory):
            taper = taper_factory(
                length=x.info.get("taper_length", 0.0),
                width1=ports1[0].width,
                width2=x.info.get("width_wide"),
                layer=ports1[0].layer,
            )
        else:
            # In this case the taper is a fixed cell
            taper = taper_factory
    else:
        taper = None
    connections = [
        round_corners(
            points=pts,
            bend_factory=bend90,
            straight_factory=straight_factory,
            taper=taper,
            cross_section=cross_section,
            **kwargs,
        )
        for pts, bend90 in zip(routes, bends90)
    ]
    return connections


def snap_route_to_end_point_x(route, x):
    y1, y2 = [p[1] for p in route[-2:]]
    return route[:-2] + [(x, y1), (x, y2)]


def snap_route_to_end_point_y(
    route: List[Union[ndarray, Tuple[float64, float64]]], y: float64
) -> List[Union[ndarray, Tuple[float64, float64]]]:
    x1, x2 = [p[0] for p in route[-2:]]
    return route[:-2] + [(x1, y), (x2, y)]


def _generate_manhattan_bundle_waypoints(
    ports1: List[Port],
    ports2: List[Port],
    waypoints: Coordinates,
    separation: Optional[float] = None,
    **kwargs,
) -> Coordinates:
    """
    Args:
        ports1: list of ports must face the same direction
        ports2: list of ports must face the same direction
        waypoints: from one point within the ports1 bank
            to another point within the ports2 bank
    """
    waypoints = remove_flat_angles(waypoints)
    way_segments = [(p0, p1) for p0, p1 in zip(waypoints, waypoints[1:])]
    offsets_start = get_ports_x_or_y_distances(ports1, waypoints[0])
    if separation:
        if offsets_start[0] == 0:
            offsets_mid = [
                np.sign(offsets_start[1]) * separation * i
                for i, o in enumerate(offsets_start)
            ]
        elif offsets_start[-1] == 0:
            offsets_mid = [
                np.sign(offsets_start[-2]) * separation * i
                for i, o in enumerate(offsets_start)
            ]
            offsets_mid.reverse()
        else:
            raise ValueError("Expected offset = 0 at either start or end of route.")
    else:
        offsets_mid = offsets_start

    start_angle = ports1[0].orientation
    if start_angle in [90, 270]:
        offsets_start = [-_d for _d in offsets_start]
        offsets_mid = [-_d for _d in offsets_mid]
    end_angle = ports2[0].orientation

    def _displace_segment_copy(s, a, sh=1, sv=1):
        sign_seg = _segment_sign(s)
        if _is_horizontal(s):
            dp = (0, sh * sign_seg * a)
        elif _is_vertical(s):
            dp = (sv * sign_seg * a, 0)
        else:
            raise ValueError(f"Segment should be manhattan, got {s}")

        displaced_seg = [np.array(p) + dp for p in s]
        return displaced_seg

    def _displace_segment_copy_group1(s, a):
        return _displace_segment_copy(s, a, sh=1, sv=-1)

    def _intersection(s1, s2):
        if _is_horizontal(s1) and _is_vertical(s2):
            sh, sv = s1, s2
        elif _is_horizontal(s2) and _is_vertical(s1):
            sh, sv = s2, s1
        else:

            if _is_horizontal(s1):
                s1_dir = "h"
            elif _is_vertical(s1):
                s1_dir = "v"
            else:
                s1_dir = "u"

            if _is_horizontal(s2):
                s2_dir = "h"
            elif _is_vertical(s2):
                s2_dir = "v"
            else:
                s2_dir = "u"

            raise ValueError(
                "s1 / s2 should be h/v or v/h. Got \
            {} {} {} {}".format(
                    s1_dir, s2_dir, s1, s2
                )
            )
        return (sv[0][0], sh[0][1])

    N = len(ports1)
    routes = []
    _make_segment = _displace_segment_copy_group1
    for i in range(N):
        prev_seg_sep = offsets_start[i]
        route = []

        for j, seg in enumerate(way_segments):
            if j == 0:
                seg_sep = prev_seg_sep
            else:
                seg_sep = offsets_mid[i]
            d_seg = _make_segment(seg, seg_sep)

            if j == 0:
                start_point = d_seg[0]
            else:
                prev_seg = way_segments[j - 1]
                tmp_seg = _make_segment(prev_seg, prev_seg_sep)
                start_point = _intersection(d_seg, tmp_seg)

            route += [start_point]

            # If last point before the ports, adjust the separation to the end ports
            if j == len(way_segments) - 1:
                end_point = ports2[i].position
                route += [end_point]

                if end_angle in [0, 180]:
                    route = snap_route_to_end_point_y(route, end_point[1])
                else:
                    route = snap_route_to_end_point_x(route, end_point[0])
            prev_seg_sep = seg_sep
        routes += [route]

    for route, start_point in zip(routes, ports1):
        route[0] = start_point.midpoint
    return routes


if __name__ == "__main__":
    import gdsfactory.tests.test_get_bundle_from_waypoints as t

    # c = t.test_get_bundle_from_waypointsC(None, check=False)
    c = t.test_get_bundle_from_waypointsB(None, check=False)
    c.show()
