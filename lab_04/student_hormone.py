"""Lab04: complete the two TODOs. Use only the Python standard library."""
import math

def receptor(h, h_min=0.0, h_max=1.0):
    """Normalize then clamp to [0,1]. Reject nonfinite values or invalid range."""
    if not all(math.isfinite(value) for value in (h, h_min, h_max)):
        raise ValueError("h and receptor bounds must be finite")
    if h_max <= h_min:
        raise ValueError("h_max must be greater than h_min")
    return max(0.0, min(1.0, (h - h_min) / (h_max - h_min)))

def step(h, stimulus, dt, prod, clear, bind):
    """Return dict with h,r,raw,p,c,b,fault.

    Invalid stimulus (NaN, infinity, outside [0,1]): reset to h=r=0,
    set raw=p=c=b=0 and fault=1. Valid: use OLD h and receptor(h)
    for all rates; update once, clamp h, read NEW receptor, fault=0.
    dt and rates have already been validated by the runner.
    """
    if not math.isfinite(stimulus) or not 0.0 <= stimulus <= 1.0:
        return dict(h=0.0, r=0.0, raw=0.0, p=0.0, c=0.0, b=0.0, fault=1)

    h_old = h
    r_old = receptor(h_old)
    p = prod * stimulus
    c = clear * h_old
    b = bind * r_old
    raw = h_old + dt * (p - c - b)
    h_new = max(0.0, min(1.0, raw))
    return dict(h=h_new, r=receptor(h_new), raw=raw, p=p, c=c, b=b, fault=0)
