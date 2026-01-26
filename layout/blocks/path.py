import numpy as np
import gdsfactory as gf
from gdsfactory.path import Path
from typing import Any, List, Union

def bend_spline_asymmetric(angle: float, r1: float, r2: float, npoints: int = 101) -> Path:
    """
    Generates an asymmetric cubic Bézier curve for a bend.
    
    Args:
        angle: Turning angle in degrees.
        r1: Transition length at the start (in-tangent).
        r2: Transition length at the end (out-tangent).
        npoints: Number of points for the spline sampling.
    """
    theta = np.radians(angle)
    
    # Define key geometric anchors
    p0 = np.array([0.0, 0.0])      # Start point
    v  = np.array([r1, 0.0])       # Intersection point of tangents
    p3 = v + np.array([r2 * np.cos(theta), r2 * np.sin(theta)]) # End point
    
    # Cubic Bezier control points (placed at 2/3 of tangent segments for smooth curvature)
    p1 = p0 + (v - p0) * 2/3
    p2 = p3 - (p3 - v) * 2/3
    
    # Cubic Bézier formula: B(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
    t = np.linspace(0, 1, npoints)[:, np.newaxis]
    pts = (1-t)**3 * p0 + 3*(1-t)**2 * t * p1 + 3*(1-t) * t**2 * p2 + t**3 * p3
    
    return Path(pts)

def smooth_asymmetric(
    points: np.ndarray,
    r1: Union[float, List[float]] = 4.0,
    r2: Union[float, List[float]] = 4.0,
    npoints: int = 101,
) -> Path:
    """
    Generates a smooth path using asymmetric splines between waypoints.

    Args:
        points: Array-like waypoints (N, 2).
        r1: In-tangent length for each bend (float or list of length N-2).
        r2: Out-tangent length for each bend (float or list of length N-2).
        npoints: Sampling points per spline.
    """
    points = np.array(points)
    n_waypoints = len(points)
    n_bends = n_waypoints - 2

    if n_bends < 1:
        return Path(points)

    # Convert r1, r2 to lists for uniform processing
    r1_list = [r1] * n_bends if isinstance(r1, (float, int)) else r1
    r2_list = [r2] * n_bends if isinstance(r2, (float, int)) else r2

    # 1. Compute direction vectors and lengths for each segment
    segments = np.diff(points, axis=0)
    seg_lengths = np.linalg.norm(segments, axis=1)
    seg_units = segments / seg_lengths[:, np.newaxis]
    
    # Compute absolute angles of each segment to determine relative turn angles
    angles = np.arctan2(seg_units[:, 1], seg_units[:, 0])
    dtheta = np.degrees(np.diff(angles))
    
    # Normalize angles to range (-180, 180]
    dtheta = (dtheta + 180) % 360 - 180

    # 2. Geometric feasibility check
    for i in range(n_bends):
        # Segment i must accommodate r2 from the previous bend and r1 for the current bend
        needed_at_start = r2_list[i-1] if i > 0 else 0
        needed_at_end = r1_list[i]
        if seg_lengths[i] < (needed_at_start + needed_at_end):
            raise ValueError(f"Segment {i} is too short to fit the specified r1 and r2 values.")

    # 3. Generate and stitch segments
    full_points = []
    current_pos = points[0]
    
    for i in range(n_bends):
        # --- Straight Section ---
        # The line starts at the end of the previous bend and ends at the start of the current bend
        line_start = current_pos
        line_end = points[i+1] - seg_units[i] * r1_list[i]
        
        full_points.append(np.array([line_start, line_end]))

        # --- Bend Section ---
        angle = dtheta[i]
        bend_path = bend_spline_asymmetric(angle=angle, r1=r1_list[i], r2=r2_list[i], npoints=npoints)
        
        # Transform bend points from local coordinate system to global path position
        bend_pts = bend_path.points.copy()
        
        # Rotation based on the entry segment angle
        rot_angle = angles[i]
        c, s = np.cos(rot_angle), np.sin(rot_angle)
        R = np.array([[c, -s], [s, c]])
        
        rotated_bend = (R @ bend_pts.T).T
        moved_bend = rotated_bend + line_end
        
        full_points.append(moved_bend)
        
        # Update current tracker to the end of the bend
        current_pos = moved_bend[-1]

    # Add the final straight segment to the destination waypoint
    last_line = np.array([current_pos, points[-1]])
    full_points.append(last_line)

    # Concatenate all generated points into a single coordinate array
    final_points = np.concatenate(full_points, axis=0)
    
    return Path(final_points)