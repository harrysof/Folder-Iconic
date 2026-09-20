"""Dependency-free SVG path flattener supporting M, L, H, V, C, Q, Z, A (arc)."""
import re
import math

def _tokenize(d):
    return re.findall(r'[MLHVCQZAmlhvcqza]|-?\d*\.?\d+(?:e-?\d+)?', d)

def flatten_path(d, samples_per_curve=24, samples_per_arc=24):
    tokens = _tokenize(d)
    i = 0
    cx, cy = 0.0, 0.0
    start_x, start_y = 0.0, 0.0
    points = []
    cmd = None

    def nextf():
        nonlocal i
        v = float(tokens[i])
        i += 1
        return v

    while i < len(tokens):
        t = tokens[i]
        if t in 'MLHVCQZAmlhvcqza':
            cmd = t
            i += 1
        # else: repeated implicit command with same letter, keep cmd

        if cmd in ('M', 'm'):
            x = nextf(); y = nextf()
            if cmd == 'm' and points:
                x += cx; y += cy
            cx, cy = x, y
            start_x, start_y = cx, cy
            points.append((cx, cy))
            cmd = 'L' if cmd == 'M' else 'l'  # subsequent pairs are implicit lineto
        elif cmd in ('L', 'l'):
            x = nextf(); y = nextf()
            if cmd == 'l':
                x += cx; y += cy
            cx, cy = x, y
            points.append((cx, cy))
        elif cmd in ('H', 'h'):
            x = nextf()
            if cmd == 'h':
                x += cx
            cx = x
            points.append((cx, cy))
        elif cmd in ('V', 'v'):
            y = nextf()
            if cmd == 'v':
                y += cy
            cy = y
            points.append((cx, cy))
        elif cmd in ('C', 'c'):
            x1 = nextf(); y1 = nextf()
            x2 = nextf(); y2 = nextf()
            x = nextf(); y = nextf()
            if cmd == 'c':
                x1 += cx; y1 += cy
                x2 += cx; y2 += cy
                x += cx; y += cy
            for s in range(1, samples_per_curve+1):
                t_ = s / samples_per_curve
                mt = 1 - t_
                px = mt**3*cx + 3*mt**2*t_*x1 + 3*mt*t_**2*x2 + t_**3*x
                py = mt**3*cy + 3*mt**2*t_*y1 + 3*mt*t_**2*y2 + t_**3*y
                points.append((px, py))
            cx, cy = x, y
        elif cmd in ('Q', 'q'):
            x1 = nextf(); y1 = nextf()
            x = nextf(); y = nextf()
            if cmd == 'q':
                x1 += cx; y1 += cy
                x += cx; y += cy
            for s in range(1, samples_per_curve+1):
                t_ = s / samples_per_curve
                mt = 1 - t_
                px = mt**2*cx + 2*mt*t_*x1 + t_**2*x
                py = mt**2*cy + 2*mt*t_*y1 + t_**2*y
                points.append((px, py))
            cx, cy = x, y
        elif cmd in ('A', 'a'):
            rx = nextf(); ry = nextf()
            xrot = nextf()
            large_arc = nextf()
            sweep = nextf()
            x = nextf(); y = nextf()
            if cmd == 'a':
                x += cx; y += cy
            arc_pts = _arc_to_points(cx, cy, rx, ry, xrot, large_arc, sweep, x, y, samples_per_arc)
            points.extend(arc_pts)
            cx, cy = x, y
        elif cmd in ('Z', 'z'):
            points.append((start_x, start_y))
            cx, cy = start_x, start_y
        else:
            raise ValueError(f"Unsupported command: {cmd}")
    return points


def _arc_to_points(x0, y0, rx, ry, xrot_deg, large_arc, sweep, x1, y1, n):
    """Convert SVG elliptical arc to a list of points (endpoint parameterization)."""
    if rx == 0 or ry == 0:
        return [(x1, y1)]
    phi = math.radians(xrot_deg)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)

    dx2 = (x0 - x1) / 2.0
    dy2 = (y0 - y1) / 2.0
    x1p = cos_phi * dx2 + sin_phi * dy2
    y1p = -sin_phi * dx2 + cos_phi * dy2

    rx, ry = abs(rx), abs(ry)
    lam = (x1p**2) / (rx**2) + (y1p**2) / (ry**2)
    if lam > 1:
        s = math.sqrt(lam)
        rx *= s
        ry *= s

    sign = -1 if large_arc == sweep else 1
    num = rx**2*ry**2 - rx**2*y1p**2 - ry**2*x1p**2
    den = rx**2*y1p**2 + ry**2*x1p**2
    co = sign * math.sqrt(max(0, num/den)) if den != 0 else 0
    cxp = co * (rx*y1p/ry)
    cyp = co * (-ry*x1p/rx)

    cx = cos_phi*cxp - sin_phi*cyp + (x0+x1)/2
    cy = sin_phi*cxp + cos_phi*cyp + (y0+y1)/2

    def angle(ux, uy, vx, vy):
        dot = ux*vx + uy*vy
        length = math.sqrt(ux**2+uy**2) * math.sqrt(vx**2+vy**2)
        ang = math.acos(max(-1, min(1, dot/length)))
        if ux*vy - uy*vx < 0:
            ang = -ang
        return ang

    theta1 = angle(1, 0, (x1p-cxp)/rx, (y1p-cyp)/ry)
    dtheta = angle((x1p-cxp)/rx, (y1p-cyp)/ry, (-x1p-cxp)/rx, (-y1p-cyp)/ry)

    if sweep == 0 and dtheta > 0:
        dtheta -= 2*math.pi
    elif sweep == 1 and dtheta < 0:
        dtheta += 2*math.pi

    pts = []
    for i in range(1, n+1):
        t = theta1 + dtheta * i / n
        ex = cx + rx*math.cos(t)*cos_phi - ry*math.sin(t)*sin_phi
        ey = cy + rx*math.cos(t)*sin_phi + ry*math.sin(t)*cos_phi
        pts.append((ex, ey))
    return pts
