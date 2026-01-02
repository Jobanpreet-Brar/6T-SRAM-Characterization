
import math
import numpy as np
import pandas as pd
from collections import deque
def print_lobe_points(lobe_name, placement):
    pts = square_points_from_placement(placement)
    s = pts["side"]
    print(f"{lobe_name} lobe (max-square side = {s:.6f} V):")
    print(f"  P1 bottom-left : ({pts['bottom_left'][0]:.6f},  {pts['bottom_left'][1]:.6f})")
    print(f"  P2 bottom-right: ({pts['bottom_right'][0]:.6f}, {pts['bottom_right'][1]:.6f})")
    print(f"  P3 top-right   : ({pts['top_right'][0]:.6f},   {pts['top_right'][1]:.6f})")
    print(f"  P4 top-left    : ({pts['top_left'][0]:.6f},    {pts['top_left'][1]:.6f})")


def square_points_from_placement(placement):
    x0, y0, s = placement
    return {
        "bottom_left":  (x0,     y0),
        "bottom_right": (x0 + s, y0),
        "top_right":    (x0 + s, y0 + s),
        "top_left":     (x0,     y0 + s),
        "side": s
    }
def sliding_min(arr, k):
    dq = deque()
    out = np.empty(len(arr) - k + 1)
    for i, v in enumerate(arr):
        while dq and dq[0] <= i - k:
            dq.popleft()
        while dq and arr[dq[-1]] >= v:
            dq.pop()
        dq.append(i)
        if i >= k - 1:
            out[i - k + 1] = arr[dq[0]]
    return out

def sliding_max(arr, k):
    dq = deque()
    out = np.empty(len(arr) - k + 1)
    for i, v in enumerate(arr):
        while dq and dq[0] <= i - k:
            dq.popleft()
        while dq and arr[dq[-1]] <= v:
            dq.pop()
        dq.append(i)
        if i >= k - 1:
            out[i - k + 1] = arr[dq[0]]
    return out

def max_square_in_lobe(x, yU, yL, tol=1e-4):
    dx = float(x[1] - x[0])
    s_hi = min(float(x[-1] - x[0]), float(np.max(yU) - np.min(yL)))

    def feasible(s):
        k = int(math.ceil(s / dx)) + 1
        k = max(k, 2)
        if k > len(x):
            return False, None, None

        minU = sliding_min(yU, k)
        maxL = sliding_max(yL, k)
        clearance = minU - maxL

        idx = int(np.argmax(clearance))
        return clearance[idx] >= s, idx, k

    lo, hi = 0.0, s_hi
    best = 0.0
    best_idx = None
    best_k = None

    for _ in range(45):
        mid = (lo + hi) / 2
        ok, idx, k = feasible(mid)
        if ok:
            best = mid
            best_idx, best_k = idx, k
            lo = mid
        else:
            hi = mid

    placement = None
    if best_idx is not None:
        i = best_idx
        j = i + best_k - 1
        x0 = float(x[i])
        y0 = float(np.max(yL[i:j+1]))  # bottom must clear the highest lower-curve point in window
        placement = (x0, y0, best)

    return best, placement

def compute_snm_from_butterfly_csv(csv_path, vdd=1.8, ngrid=20001):
    df = pd.read_csv(csv_path)

    # These are exactly the columns in your CSVs
    x1 = df["Q vs Qb X"].to_numpy(dtype=float)
    y1 = df["Q vs Qb Y"].to_numpy(dtype=float)
    x2 = df["Qb vs Q X"].to_numpy(dtype=float)  # mirror curve x
    y2 = df["Qb vs Q Y"].to_numpy(dtype=float)  # mirror curve y

    m1 = ~(np.isnan(x1) | np.isnan(y1))
    m2 = ~(np.isnan(x2) | np.isnan(y2))
    x1, y1 = x1[m1], y1[m1]
    x2, y2 = x2[m2], y2[m2]

    # Uniform x-grid for stable window sizing
    xg = np.linspace(0, vdd, ngrid)

    s1 = np.argsort(x1)
    s2 = np.argsort(x2)
    y1g = np.interp(xg, x1[s1], y1[s1])
    y2g = np.interp(xg, x2[s2], y2[s2])

    yU = np.maximum(y1g, y2g)
    yL = np.minimum(y1g, y2g)

    # Split lobes near metastable crossing (closest sign-change to mid)
    diff = y1g - y2g
    changes = np.where(np.diff(np.signbit(diff)))[0]
    mid = int(changes[np.argmin(np.abs(changes - len(xg)//2))]) if len(changes) else len(xg)//2

    snm_left, place_left = max_square_in_lobe(xg[:mid+1], yU[:mid+1], yL[:mid+1])
    snm_right, place_right = max_square_in_lobe(xg[mid:], yU[mid:], yL[mid:])

    snm = min(snm_left, snm_right)

    return {
        "SNM": snm,
        "SNM_left": snm_left,
        "SNM_right": snm_right,
        "placement_left": place_left,
        "placement_right": place_right,
    }


def print_snm_report(title, res):
    print("\n" + "="*70)
    print(f"{title}")
    print("="*70)
    print(f"SNM (reported)      : {res['SNM']:.6f} V  ({res['SNM']*1e3:.1f} mV)")
    print(f"SNM_left  (lobe)    : {res['SNM_left']:.6f} V  ({res['SNM_left']*1e3:.1f} mV)")
    print(f"SNM_right (lobe)    : {res['SNM_right']:.6f} V  ({res['SNM_right']*1e3:.1f} mV)")
    print()
    print_lobe_points("LEFT",  res["placement_left"])
    print()
    print_lobe_points("RIGHT", res["placement_right"])
    print("="*70)

    
if __name__ == "__main__":
    hold_csv = "data/Butterfly_hold.csv"
    read_csv = "data/Butterfly_read_Qb_0.csv"

    hold = compute_snm_from_butterfly_csv(hold_csv, vdd=1.8)
    read = compute_snm_from_butterfly_csv(read_csv, vdd=1.8)

    print_snm_report("HOLD (HSNM)", hold)
    print_snm_report("READ (RSNM)", read)


