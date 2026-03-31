"""
Sizing engine — 5 operating modes for transistor sizing.

Each mode takes global biases (L, VDS, VSB) plus mode-specific targets
and returns a full operating-point summary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.interpolate import interp1d
from scipy.optimize import brentq, root, minimize

from .data_loader import LUTData
from .lookup_engine import lookup
from .reverse_lookup import lookupVGS
from .utils import eng


# ── Bucket Definitions (Degrees of Freedom) ───────────────────────────

PARAM_TO_BUCKET = {
    "GM_ID": 1, "VGS": 1, "fT": 1, "ID_W": 1,
    "L": 2, "GM_GDS": 2, "VA": 2,
    "ID": 3, "W": 3, "GM": 3
}

VAR_LABELS = {
    "GM_ID": "gm/ID", "VGS": "VGS", "fT": "fT", "ID_W": "ID/W",
    "L": "Length", "GM_GDS": "Gain", "VA": "VA",
    "ID": "Target ID", "W": "Target Width", "GM": "Target gm"
}


# ── Operating-point container ──────────────────────────────────────────

@dataclass
class OperatingPoint:
    """Complete operating-point summary for a sized transistor."""
    ok: bool = False
    msg: str = ""

    # Geometry
    W: float = 0.0
    L: float = 0.0

    # Biasing
    VGS: float = 0.0
    VT: float = 0.0
    VDSAT: float = 0.0
    VDS: float = 0.0
    VSB: float = 0.0

    # Current
    ID: float = 0.0
    ID_W: float = 0.0

    # Small signal
    gm: float = 0.0
    gds: float = 0.0
    gmb: float = 0.0
    gm_id: float = 0.0
    gm_gds: float = 0.0  # intrinsic gain V/V

    # High frequency
    fT: float = 0.0
    Cgg: float = 0.0
    Cgd: float = 0.0
    Cdd: float = 0.0
    Css: float = 0.0
    
    # Early Voltage
    VA: float = 0.0


# ── Helper: extract full OP from (gm/ID, L, ID, VDS, VSB) ─────────────

def _extract_op(
    data: LUTData,
    gmid_val: float,
    L: Optional[float],
    ID: float,
    VDS: float,
    VSB: float,
    gain_target: Optional[float] = None,
) -> OperatingPoint:
    """Given a known gm/ID operating point, extract every parameter.
    If L is None, finds L using gain_target first.
    """
    op = OperatingPoint()
    try:
        # Resolve L if missing
        if L is None:
            if gain_target is None:
                op.msg = "Internal Error: L and gain_target both missing"
                return op
            L = _find_L_for_target_gain(data, gmid_val, gain_target, VDS, VSB)
            if L is None:
                op.msg = f"Cannot achieve gm/gds = {gain_target:.1f} at gm/ID = {gmid_val:.1f}"
                return op
        # ID/W → W
        idw = lookup(data, "ID_W", cross_var="GM_ID", cross_val=gmid_val,
                     L=L, VDS=VDS, VSB=VSB)
        idw = float(np.squeeze(idw))
        
        if not np.isfinite(idw):

            op.msg = "Operating point out of LUT bounds (extrapolation failed)"
            return op
        if abs(idw) < 1e-18:
            op.msg = "ID/W near zero — operating point not reachable"
            return op

        W = ID / idw


        # VGS
        vgs = lookupVGS(data, target_var="GM_ID", target_val=gmid_val, L=L, VDS=VDS, VSB=VSB)
        vgs = float(np.squeeze(vgs))

        # VT, VDSAT at that VGS
        vt = float(np.squeeze(lookup(data, "VT", L=L, VGS=vgs, VDS=VDS, VSB=VSB)))
        vdsat = float(np.squeeze(lookup(data, "VDSAT", L=L, VGS=vgs, VDS=VDS, VSB=VSB)))

        # Small signal
        gm = gmid_val * ID
        gain = float(np.squeeze(
            lookup(data, "GM_GDS", cross_var="GM_ID", cross_val=gmid_val,
                   L=L, VDS=VDS, VSB=VSB)
        ))
        gds = gm / gain if gain != 0 else 0.0
        
        # Early Voltage
        va = float(np.squeeze(
            lookup(data, "VA", L=L, VGS=vgs, VDS=VDS, VSB=VSB)
        ))
        op.VA = va


        # gmb: lookup returns total GMB for the reference-width device
        gmb_raw = float(np.squeeze(
            lookup(data, "GMB", L=L, VGS=vgs, VDS=VDS, VSB=VSB)
        ))
        # Scale: (GMB_ref / W_ref) * W_target
        gmb = (gmb_raw / data.W) * W

        # High frequency
        gm_cgg = float(np.squeeze(
            lookup(data, "GM_CGG", cross_var="GM_ID", cross_val=gmid_val,
                   L=L, VDS=VDS, VSB=VSB)
        ))
        fT = gm_cgg / (2 * np.pi)

        # Capacitances (per-width, then scale)
        cgg_w = float(np.squeeze(
            lookup(data, "CGG_W", cross_var="GM_ID", cross_val=gmid_val,
                   L=L, VDS=VDS, VSB=VSB)
        ))
        cgd_w = float(np.squeeze(
            lookup(data, "CGD_W", cross_var="GM_ID", cross_val=gmid_val,
                   L=L, VDS=VDS, VSB=VSB)
        ))
        cdd_w = float(np.squeeze(
            lookup(data, "CDD_W", cross_var="GM_ID", cross_val=gmid_val,
                   L=L, VDS=VDS, VSB=VSB)
        ))
        css_w = float(np.squeeze(
            lookup(data, "CSS_W", cross_var="GM_ID", cross_val=gmid_val,
                   L=L, VDS=VDS, VSB=VSB)
        ))

        op.ok = True
        op.W = W
        op.L = L
        op.VGS = vgs
        op.VT = vt
        op.VDSAT = vdsat
        op.VDS = VDS
        op.VSB = VSB
        op.ID = ID
        op.ID_W = idw
        op.gm = gm
        op.gds = gds
        op.gmb = gmb
        op.gm_id = gmid_val
        op.gm_gds = gain
        op.fT = fT
        op.VA = float(np.squeeze(
            lookup(data, "VA", cross_var="GM_ID", cross_val=gmid_val,
                   L=L, VDS=VDS, VSB=VSB)
        ))
        op.Cgg = abs(cgg_w) * W
        op.Cgd = abs(cgd_w) * W
        op.Cdd = abs(cdd_w) * W
        op.Css = abs(css_w) * W

    except Exception as e:
        op.msg = str(e)

    return op


# ── Helper: find gm/ID that yields a target parameter ─────────────────

def _find_gmid_for_target(
    data: LUTData,
    target_param: str,
    target_value: float,
    L: float,
    VDS: float,
    VSB: float,
    gmid_range: Optional[tuple[float, float]] = None,
) -> Optional[float]:
    """Find the gm/ID value that produces *target_value* of *target_param*.

    Special cases:
      - If target_param == 'VGS', use robust 1D interpolation from VGS -> gm/ID.
      - Otherwise, use Brent's method on the residual.
    """
    if gmid_range is None:
        if data.GM_ID is not None:
            # Bound dynamically but enforce physical realism 
            # (gm/ID peaking mathematically to infinity is a simulation artifact)
            lb = max(2.0, float(np.nanmin(data.GM_ID[data.GM_ID > 0])))
            ub = min(35.0, float(np.nanmax(data.GM_ID)))
            gmid_range = (lb, ub)
        else:
            gmid_range = (2.0, 30.0)

    # 0. DIRECT CALCULATION for VGS (Extract gm/ID curve at fixed L)
    if target_param == "VGS":
        try:
            # 1. Get gm/ID across all VGS at this L
            vgs_vec = data.VGS
            gmid_curve = np.squeeze(lookup(data, "GM_ID", cross_var="VGS", 
                                           cross_val=vgs_vec, L=L, VDS=VDS, VSB=VSB))
            
            # 2. Robust 1D interpolation: VGS -> gm/ID
            f = interp1d(vgs_vec, gmid_curve, kind='linear', fill_value="extrapolate")
            g_res = float(f(target_value))
            
            # 3. Physical boundaries based on LUT
            lb, ub = gmid_range
            if g_res < lb or g_res > ub:
                 return None
            return g_res
        except Exception:
            return None

    def residual(gmid):
        val = float(np.squeeze(
            lookup(data, target_param, cross_var="GM_ID", cross_val=gmid,
                   L=L, VDS=VDS, VSB=VSB)
        ))
        return val - target_value

    # Evaluate at endpoints to check for sign change
    fa, fb = np.nan, np.nan
    try:
        # Add tiny epsilon to avoid exact boundary NaNs
        lb = gmid_range[0] + 1e-4
        ub = gmid_range[1] - 1e-4
        fa = residual(lb)
        fb = residual(ub)
    except Exception:
        pass

    if np.isfinite(fa) and np.isfinite(fb) and fa * fb <= 0:
        try:
            return float(brentq(residual, lb, ub, xtol=1e-6))
        except Exception:
            pass

    # No sign change at ends, OR NaNs encountered — try scanning with vectorized lookup for speed
    gmid_scan = np.linspace(gmid_range[0] + 1e-4, gmid_range[1] - 1e-4, 200)
    with np.errstate(divide='ignore', invalid='ignore'):
        vals = np.squeeze(lookup(data, target_param, cross_var="GM_ID", 
                                 cross_val=gmid_scan, L=float(L), VDS=VDS, VSB=VSB))
        vals = vals - target_value
        
    finite_mask = np.isfinite(vals)
    if not np.any(finite_mask): return None
    
    gmid_finite = gmid_scan[finite_mask]
    vals_finite = vals[finite_mask]
    
    sign_changes = np.where(np.diff(np.sign(vals_finite)))[0]
    if len(sign_changes) == 0:
        return None
        
    # Use the first crossing
    idx = sign_changes[0]
    try:
        return float(brentq(residual, gmid_finite[idx], gmid_finite[idx + 1], xtol=1e-11))
    except Exception:
        return None


def _find_L_for_target_gain(
    data: LUTData,
    gmid: float,
    target_val: float,
    VDS: float,
    VSB: float,
    target_var: str = "GM_GDS"
) -> Optional[float]:
    """Find the Channel Length (L) that produces *target_val* of *target_var* at a fixed gm/ID.
    
    Uses a discrete grid scan before Brent optimization to safely handle 
    deep-submicron non-monotonicities (e.g. gain roll-off from Short-Channel Effects).
    """    
    def residual(L):
        # lookup gain (GM_GDS) or other var at this specific L and gmid
        val = float(np.squeeze(
            lookup(data, target_var, cross_var="GM_ID", cross_val=gmid,
                   L=L, VDS=VDS, VSB=VSB)
        ))
        return val - target_val

    L_vec = np.sort(data.L)
    candidates = []
    prev_L = None
    prev_res = None
    
    for L_curr in L_vec:
        try:
            L_curr_flt = float(L_curr)
            res_curr = residual(L_curr_flt)
            
            if not np.isfinite(res_curr):
                prev_L, prev_res = L_curr_flt, res_curr
                continue
                
            if abs(res_curr) < 1e-9:
                return L_curr_flt
                
            if prev_res is not None and np.isfinite(prev_res):
                if prev_res * res_curr < 0:
                    candidates.append((prev_L, L_curr_flt))
                    
            prev_L, prev_res = L_curr_flt, res_curr
        except Exception:
            continue

    # Attempt to solve within found brackets
    for bracket in candidates:
        try:
            return float(brentq(residual, bracket[0], bracket[1], xtol=1e-9))
        except Exception:
            continue
            
    return None


# ── Public sizing functions ────────────────────────────────────────────

def size_mode1_ota(
    data: LUTData,
    gmid: float,
    L: Optional[float],
    VDS: float,
    VSB: float,
    ID: Optional[float] = None,
    gm: Optional[float] = None,
    gain_target: Optional[float] = None,
) -> OperatingPoint:
    """Mode 1: Standard OTA — given gm/ID and (ID or gm).
    If L is None, gain_target must be provided.
    """
    if ID is None and gm is not None:
        ID = gm / gmid
    if ID is None or ID <= 0:
        op = OperatingPoint()
        op.msg = "Provide a valid ID or gm"
        return op
    if ID is None:
        return OperatingPoint(ok=False, msg="ID is required for Mode 1")
    return _extract_op(data, gmid, L, ID, VDS, VSB, gain_target=gain_target)


def size_mode2_rf(
    data: LUTData,
    fT_target: float,
    L: float,
    VDS: float,
    VSB: float,
    ID: Optional[float] = None,
    gm: Optional[float] = None,
    W: Optional[float] = None,
) -> OperatingPoint:
    """Mode 2: High-Speed/RF — strictly requires L (1D lookup)."""
    msg = _check_ft_bounds(data, fT_target, L, VDS, VSB)
    if msg: return OperatingPoint(ok=False, msg=msg)

    target_gm_cgg = fT_target * 2 * np.pi
    gmid = _find_gmid_for_target(data, "GM_CGG", target_gm_cgg, L, VDS, VSB)
    
    if gmid is None:
        return OperatingPoint(ok=False, msg=f"Cannot achieve fT={eng(fT_target, 'Hz')} at L={eng(L, 'm')}")

    if ID is None and gm is not None:
        ID = gm / gmid
    if ID is None and W is not None:
        idw = float(np.squeeze(lookup(data, "ID_W", cross_var="GM_ID", cross_val=gmid, L=L, VDS=VDS, VSB=VSB)))
        ID = idw * W
    if ID is None or ID <= 0:
        return OperatingPoint(ok=False, msg="Provide a valid ID or W")

    return _extract_op(data, float(gmid), L, float(ID), VDS, VSB)


def size_mode3_gain(
    data: LUTData,
    gain_target_mode: float,
    L: float,
    VDS: float,
    VSB: float,
    ID: Optional[float] = None,
    gm: Optional[float] = None,
) -> OperatingPoint:
    """Mode 3: Target Intrinsic Gain.
    Now strictly requires L to be fixed (1D lookup).
    """
    # 1. Bounds check
    msg = _check_gain_bounds(data, gain_target_mode, L, VDS, VSB)
    if msg: return OperatingPoint(ok=False, msg=msg)

    gmid = _find_gmid_for_target(data, "GM_GDS", gain_target_mode, L, VDS, VSB)
    
    if gmid is None or L is None:
        op = OperatingPoint()
        op.msg = f"Cannot achieve gain = {gain_target_mode:.1f} V/V"
        return op

    if ID is None and gm is not None:
        ID = float(gm) / float(gmid)
    if ID is None or ID <= 0:
        return OperatingPoint(ok=False, msg="Provide a valid ID or gm")

    return _extract_op(data, float(gmid), L, float(ID), VDS, VSB)


def size_mode4_vgs(
    data: LUTData,
    VGS: float,
    L: Optional[float],
    VDS: float,
    VSB: float,
    W: Optional[float] = None,
    ID: Optional[float] = None,
    gain_target: Optional[float] = None,
) -> OperatingPoint:
    """Mode 4: Voltage-Driven (Classic) — given VGS and (W or ID)."""
    if L is None:
        if gain_target is None:
            op = OperatingPoint(); op.msg = "L and gain_target both missing"; return op
        # Resolve L from gain_target and VGS
        # First find gm/ID at this VGS and trial L
        idw_trial = float(np.squeeze(lookup(data, "ID", L=np.min(data.L), VGS=VGS, VDS=VDS, VSB=VSB)))
        gmw_trial = float(np.squeeze(lookup(data, "GM", L=np.min(data.L), VGS=VGS, VDS=VDS, VSB=VSB)))
        gmid_trial = gmw_trial / idw_trial if idw_trial != 0 else 10.0
        L = _find_L_for_target_gain(data, gmid_trial, gain_target, VDS, VSB)
        if L is None: 
            op = OperatingPoint(); op.msg = "Cannot achieve gain target"; return op

    op = OperatingPoint()
    try:
        # Forward lookup at the given VGS
        idw = float(np.squeeze(
            lookup(data, "ID", L=L, VGS=VGS, VDS=VDS, VSB=VSB)
        )) / data.W
        gmw = float(np.squeeze(
            lookup(data, "GM", L=L, VGS=VGS, VDS=VDS, VSB=VSB)
        )) / data.W

        if W is not None:
            ID_calc = idw * W
        elif ID is not None:
            W = ID / idw if abs(idw) > 1e-18 else 0.0
            ID_calc = ID
        else:
            op.msg = "Provide W or ID"
            return op

        gmid_val = gmw / idw if abs(idw) > 1e-18 else 0.0
        return _extract_op(data, gmid_val, L, ID_calc, VDS, VSB, gain_target=gain_target)

    except Exception as e:
        op.msg = str(e)
        return op


def size_mode5_density(
    data: LUTData,
    id_w_target: float,
    L: float,
    VDS: float,
    VSB: float,
    ID: Optional[float] = None,
    gm: Optional[float] = None,
) -> OperatingPoint:
    """Mode 5: Current Density — given ID/W and ID."""
    # Find the gm/ID corresponding to this ID/W
    gmid = _find_gmid_for_target(data, "ID_W", id_w_target, L, VDS, VSB)
    
    if gmid is None:
        op = OperatingPoint()
        op.msg = f"Cannot achieve ID/W = {id_w_target:.3g} at L = {L}"
        return op

    if ID is None and gm is not None:
        ID = float(gm) / float(gmid)
    if ID is None or ID <= 0:
        return OperatingPoint(ok=False, msg="Provide a valid ID or gm")

    return _extract_op(data, float(gmid), L, float(ID), VDS, VSB)


def size_mode6_2d_opt(
    data: LUTData,
    fT_target: float,
    gain_target: float, # This acts as a fallback or minimum acceptable gain now
    VDS: float,
    VSB: float,
    ID: Optional[float] = None,
    gm: Optional[float] = None,
    grid_snap_nm: float = 5.0  # Foundry manufacturing grid (e.g., 5nm)
) -> OperatingPoint:
    """Mode 6: 2D Optimization — Constrained Optimization for (gm/ID, L).
    
    ENGINEERING FIX: 
    Instead of an over-constrained least squares compromise, this uses SLSQP 
    to MAXIMIZE Intrinsic Gain while maintaining fT >= fT_target.
    Finally, it snaps the Channel Length (L) to a realistic manufacturing grid.
    """
    # 1. Bounds check (global for technology limits)
    L_min, L_max = np.min(data.L), np.max(data.L)
    if data.GM_ID is not None:
        gmid_min = max(2.0, float(np.nanmin(data.GM_ID[data.GM_ID > 0])))
        gmid_max = min(35.0, float(np.nanmax(data.GM_ID)))
    else:
        gmid_min, gmid_max = 2.0, 30.0
    
    ft_base_op = _extract_op(data, L=L_min, gmid_val=gmid_min, ID=1.0, VDS=VDS, VSB=VSB)
    ft_max = ft_base_op.fT
    
    if fT_target > ft_max:
        return OperatingPoint(ok=False, msg=f"fT={eng(fT_target, 'Hz')} impossible (Max: {eng(ft_max, 'Hz')})")

    # 2. Define Objective Function (Minimize -Gain -> Maximize Gain)
    def objective(p):
        gmid_val, L_val = p
        op = _extract_op(data, gmid_val, L_val, 1.0, VDS, VSB)
        return -op.gm_gds  # Negative for maximization

    # 3. Define Inequality Constraint (fT >= fT_target  =>  fT - fT_target >= 0)
    def constraint_ft(p):
        gmid_val, L_val = p
        op = _extract_op(data, gmid_val, L_val, 1.0, VDS, VSB)
        return op.fT - fT_target

    # 4. Define Bounds
    bounds = [(gmid_min, gmid_max), (L_min, L_max)]
    
    # 5. Optimization using SLSQP
    x0 = [15.0, np.median(data.L)] # Initial guess
    
    try:
        res = minimize(
            objective, 
            x0, 
            method='SLSQP', 
            bounds=bounds,
            constraints={'type': 'ineq', 'fun': constraint_ft},
            options={'ftol': 1e-4, 'disp': False}
        )
        
        if not res.success:
            return OperatingPoint(ok=False, msg=f"2D Solver Failed: {res.message}")
            
        best_gmid, best_L_raw = res.x
        
        # 6. Manufacturing Grid Snapping (DIRECTIONAL SPEED-PRIORITY)
        # Convert L to nanometers, round to nearest grid_snap_nm
        best_L_nm = best_L_raw * 1e9
        
        # Try standard rounding first
        L_snap1_nm = np.round(best_L_nm / grid_snap_nm) * grid_snap_nm
        L_snap1 = L_snap1_nm * 1e-9
        L_snap1 = np.clip(L_snap1, L_min, L_max)
        
        # Check fT at standard-rounded L
        op1 = _extract_op(data, float(best_gmid), float(L_snap1), 1.0, VDS, VSB)
        
        if op1.fT >= fT_target:
            best_L_snapped = L_snap1
            best_L_snapped_nm = L_snap1_nm
        else:
            # Violation! Snap DOWN to ensure fT >= fT_target (since fT ~ 1/L^2)
            L_snap2_nm = np.floor(best_L_nm / grid_snap_nm) * grid_snap_nm
            L_snap2 = L_snap2_nm * 1e-9
            best_L_snapped = np.clip(L_snap2, L_min, L_max)
            best_L_snapped_nm = L_snap2_nm

        # 7. Calculate ID based on gm if provided (Standard RF Flow)
        if ID is None and gm is not None:
            ID = float(gm) / float(best_gmid)
            
        if ID is None:
             return OperatingPoint(ok=False, msg="Target ID or Target gm is required to calculate Width (W)")
             
        # 8. Extract final operating point with the SNAPPED dimensions
        final_op = _extract_op(data, float(best_gmid), float(best_L_snapped), float(ID), VDS, VSB)
        
        # 9. Final Fallback Warning
        if final_op.fT < fT_target * 0.98: # 2% tolerance if tech limit reached
            final_op.msg = f"Warning: Speed limit reached. fT={eng(final_op.fT, 'Hz')} (Target: {eng(fT_target, 'Hz')}) at L={best_L_snapped_nm}nm."
            
        return final_op

    except Exception as e:
        return OperatingPoint(ok=False, msg=f"2D Optimization Error: {e}")


# ── Universal Sizing Engine (Degrees of Freedom) ──────────────────────

def size_universal(data: LUTData, VDS: float, VSB: float, **kwargs) -> OperatingPoint:
    """Universal Sizing Engine — Pick 3 variables (one from each bucket).
    
    1. Inversion Level: {GM_ID, VGS, fT, ID_W}
    2. Geometry/Gain: {L, GM_GDS, VA}
    3. Scaling: {ID, W, GM}
    """
    # 1. Validation: Must have exactly 3 parameters from 3 different buckets
    buckets_found = {}
    for k, v in kwargs.items():
        if v is None: continue
        bucket = PARAM_TO_BUCKET.get(k)
        if bucket:
            if bucket in buckets_found:
                return OperatingPoint(ok=False, msg=f"Conflict: Multiple parameters from Bucket {bucket} selected.")
            buckets_found[bucket] = (k, v)
    
    if len(buckets_found) < 3:
         missing = [b for b in [1, 2, 3] if b not in buckets_found]
         return OperatingPoint(ok=False, msg=f"Missing parameters from Buckets: {missing}")

    p1_name, p1_val = buckets_found[1]
    p2_name, p2_val = buckets_found[2]
    p3_name, p3_val = buckets_found[3]

    # 2. Strict Boundary Guard (No Extrapolation)
    L_min, L_max = np.min(data.L), np.max(data.L)
    if p2_name == "L":
        if p2_val < L_min or p2_val > L_max:
            return OperatingPoint(ok=False, msg=f"Requested L={eng(p2_val, 'm')} is outside PDK limits.")

    try:
        # 3. Solver Routing
        
        # Determine L first
        L = None
        if p2_name == "L":
            L = p2_val
        
        # Determine gm/ID (Inversion Level)
        gmid = None
        if p1_name == "GM_ID":
            gmid = p1_val
        elif p1_name == "VGS" and L is not None:
            # If L is known, we can directly map VGS to gmid
            id_ref = float(np.squeeze(lookup(data, "ID", L=L, VGS=p1_val, VDS=VDS, VSB=VSB)))
            gm_ref = float(np.squeeze(lookup(data, "GM", L=L, VGS=p1_val, VDS=VDS, VSB=VSB)))
            gmid = gm_ref / id_ref if id_ref > 0 else None
        
        # CASE A: Inversion and L are known (DIRECT)
        if L is not None and gmid is not None:
             # Just need to handle p3 (Scaling)
             ID = None
             if p3_name == "ID": ID = p3_val
             elif p3_name == "GM": ID = p3_val / gmid
             elif p3_name == "W":
                 idw = float(np.squeeze(lookup(data, "ID_W", cross_var="GM_ID", cross_val=gmid, L=L, VDS=VDS, VSB=VSB)))
                 ID = idw * p3_val
             return _extract_op(data, float(gmid), float(L), float(ID), VDS, VSB)

        # CASE B: Iterative L-Search (Target Gain or VA)
        if L is None and gmid is not None:
            target_var = "GM_GDS" if p2_name == "GM_GDS" else "VA"
            L_solved = _find_L_for_target_gain(data, gmid, p2_val, VDS, VSB, target_var=target_var)
            if L_solved is None:
                return OperatingPoint(ok=False, msg=f"Target {VAR_LABELS[p2_name]} unattainable at {VAR_LABELS[p1_name]}={p1_val}.")
            
            # Resolve Scaling (p3)
            ID = None
            if p3_name == "ID": ID = p3_val
            elif p3_name == "GM": ID = p3_val / gmid
            elif p3_name == "W":
                idw = float(np.squeeze(lookup(data, "ID_W", cross_var="GM_ID", cross_val=gmid, L=L_solved, VDS=VDS, VSB=VSB)))
                ID = idw * p3_val
            return _extract_op(data, float(gmid), float(L_solved), float(ID), VDS, VSB)

        # CASE C: Iterative Inversion-Search (Target fT or ID/W with known L)
        if L is not None and gmid is None:
            target_var = "fT" if p1_name == "fT" else "ID_W"
            target_val = p1_val
            gmid_solved = _find_gmid_for_target(data, target_var, target_val, L, VDS, VSB)
            if gmid_solved is None:
                return OperatingPoint(ok=False, msg=f"Target {VAR_LABELS[p1_name]} unattainable at L={eng(L, 'm')}.")
            
            # Resolve Scaling (p3)
            ID = None
            if p3_name == "ID": ID = p3_val
            elif p3_name == "GM": ID = p3_val / gmid_solved
            elif p3_name == "W":
                idw = float(np.squeeze(lookup(data, "ID_W", cross_var="GM_ID", cross_val=gmid_solved, L=L, VDS=VDS, VSB=VSB)))
                ID = idw * p3_val
            return _extract_op(data, float(gmid_solved), float(L), float(ID), VDS, VSB)
        
        # CASE D: Double Search (Inversion and L both unknown)
        if L is None and gmid is None:
            # 1. MANDATORY FOOLPROOF ALGORITHM: Step 1: Discrete Grid Sweep
            t1_var = "fT" if p1_name == "fT" else ("ID_W" if p1_name == "ID_W" else "VGS")
            t2_var = "GM_GDS" if p2_name == "GM_GDS" else "VA"
            
            best_L_discrete = float(data.L[0])
            best_gmid_discrete = None
            min_abs_err = float('inf')
            
            grid_results = [] # Store (L, error, gmid) for bracket detection
            for L_val in data.L:
                try:
                    L_float = float(L_val)
                    gmid_i = _find_gmid_for_target(data, t1_var, p1_val, L_float, VDS, VSB)
                    if gmid_i is None: continue
                    
                    val2 = float(np.squeeze(lookup(data, t2_var, cross_var="GM_ID", 
                                                  cross_val=gmid_i, L=L_float, 
                                                  VDS=VDS, VSB=VSB)))
                    err = val2 - p2_val
                    grid_results.append((L_float, err, gmid_i))
                    
                    if abs(err) < min_abs_err:
                        min_abs_err = abs(err)
                        best_L_discrete = L_float
                        best_gmid_discrete = gmid_i
                except:
                    continue
            
            # STEP 2: Find Zero-Crossing Bracket in the grid results
            bracket = None
            for i in range(len(grid_results) - 1):
                (l1, e1, g1), (l2, e2, g2) = grid_results[i], grid_results[i+1]
                if e1 * e2 <= 0: # Sign flip detected!
                    bracket = (l1, l2)
                    break
            
            # STEP 3: Refine with brentq ONLY if bracket is found
            L_solved = best_L_discrete
            gmid_solved = best_gmid_discrete
            
            if bracket:
                def objective(L_test):
                    gx = _find_gmid_for_target(data, t1_var, p1_val, float(L_test), VDS, VSB)
                    if gx is None: return 1.0 # Should not happen inside bracket
                    vx = float(np.squeeze(lookup(data, t2_var, cross_var="GM_ID", 
                                                cross_val=gx, L=float(L_test), 
                                                VDS=VDS, VSB=VSB)))
                    return vx - p2_val
                
                try:
                    L_solved = brentq(objective, bracket[0], bracket[1], xtol=1e-12)
                    gmid_solved = _find_gmid_for_target(data, t1_var, p1_val, L_solved, VDS, VSB)
                except ValueError:
                    L_solved = best_L_discrete # Safe fallback
                    gmid_solved = best_gmid_discrete
            
            if gmid_solved is None:
                return OperatingPoint(ok=False, msg="No solution found in PDK range.")

            # 4. Resolve Scaling (p3)
            ID = None
            if p3_name == "ID": ID = p3_val
            elif p3_name == "GM": ID = p3_val / gmid_solved
            elif p3_name == "W":
                idw = float(np.squeeze(lookup(data, "ID_W", cross_var="GM_ID", cross_val=gmid_solved, 
                                              L=L_solved, VDS=VDS, VSB=VSB)))
                ID = idw * p3_val
            
            return _extract_op(data, float(gmid_solved), float(L_solved), float(ID), VDS, VSB)

    except (ValueError, RuntimeError) as e:
        return OperatingPoint(ok=False, msg=f"Solver Error: {str(e)}")
    except Exception as e:
        return OperatingPoint(ok=False, msg=f"Unexpected Error: {str(e)}")





def _check_ft_bounds(data: LUTData, target: float, L: float, VDS: float, VSB: float) -> Optional[str]:
    """Check if target fT is achievable at this L."""
    op_strong = _extract_op(data, L=L, gmid_val=5.0, ID=1.0, VDS=VDS, VSB=VSB)
    max_achievable = op_strong.fT
    if target > max_achievable * 1.05:
        return f"Target fT ({eng(target, 'Hz')}) exceeds tech limit ({eng(max_achievable, 'Hz')}) at L={eng(L, 'm')}."
    return None

def _check_gain_bounds(data: LUTData, target: float, L: float, VDS: float, VSB: float) -> Optional[str]:
    """Check if target Gain is achievable at this L."""
    op_weak = _extract_op(data, L=L, gmid_val=25.0, ID=1.0, VDS=VDS, VSB=VSB)
    max_gain = op_weak.gm_gds
    if target > max_gain * 1.1:
        return f"Target Gain ({target:.1f}) exceeds tech limit ({max_gain:.1f}) at L={eng(L, 'm')}."
    return None
