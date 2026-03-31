"""
Advanced Plotting Engine for gm/ID Dashboard.
Evaluates complex multidimensional vector sweeps and mathematical expressions.
"""
from __future__ import annotations

import re
import numpy as np
from typing import Dict, Optional, Tuple

from .data_loader import LUTData
from .lookup_engine import lookup, VALID_RATIOS

# Safely permitted tokens in mathematical expressions
_SAFE_MATH_ATOMS = {
    "log10": np.log10, "LOG10": np.log10,
    "log": np.log, "LOG": np.log,
    "sqrt": np.sqrt, "SQRT": np.sqrt,
    "abs": np.abs, "ABS": np.abs,
    "pi": np.pi, "PI": np.pi,
    "exp": np.exp, "EXP": np.exp,
}

# The base parameters evaluated directly by lookup() 
_LUT_PARAMS = {
    "ID", "VT", "VTH", "VDSAT", "GM", "GMB", "GDS", "CGG", "CGS", "CGD", 
    "CDD", "CSS", "CGB", "CDB", "CSB", "SFL", "STH", "W"
}
_LUT_PARAMS.update(VALID_RATIOS)

def _eval_math(expr: str, vectors: Dict[str, np.ndarray]) -> np.ndarray:
    """Safely evaluates a basic math expression backed by numpy arrays."""
    # Build sandbox environment
    env = _SAFE_MATH_ATOMS.copy()
    env.update(vectors)
    # Strip any potential malicious builtins
    env["__builtins__"] = {}
    
    try:
        # DBG: print(f"EVAL: {expr} | KEYS: {sorted(env.keys())}")
        with np.errstate(divide='ignore', invalid='ignore'):
            res = eval(expr, env)
        
        # Ensure result is a numpy array (eval might return a scalar if expression is simple)
        if not isinstance(res, np.ndarray):
            # If we were expecting an array (most likely), broadcast it
            # But generate_plot_data usually passes vectors.
            pass
            
        # Convert any infs to NaN so matplotlib doesn't crash or behave weirdly
        if isinstance(res, np.ndarray):
            res[~np.isfinite(res)] = np.nan
        elif isinstance(res, (float, int)):
            if not np.isfinite(res):
                res = np.nan
                
        return res
    except Exception as e:
        raise ValueError(f"Failed to evaluate expression '{expr}': {e} | Available indicators: {sorted(env.keys())}")


def _extract_variables(expr: str) -> set[str]:
    """Finds all uppercase alphanumeric variables in the expression."""
    words = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', expr)
    return {w for w in words if w.upper() in _LUT_PARAMS or w.upper() in ["L", "VGS", "VDS", "VSB"]}


def generate_plot_data(
    data: LUTData,
    x_axis: str,
    y_axis: str,
    constants: Dict[str, float]
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates X and Y vectors for a plot.
    """
    x_var = x_axis.upper()
    
    EXTRINSIC_PARAMS = {
        "ID", "GM", "GDS", "GMB",
        "CGG", "CGS", "CSG", "CGD", "CDG", "CGB",
        "CDD", "CSS", "CDB", "CSB", "SFL", "STH"
    }
    
    # ── 1. Determine the Sweep Point ──
    if x_var == "VGS":
        sweep_vec = np.linspace(float(data.VGS.min()), float(data.VGS.max()), 100)
    elif x_var == "VDS":
        sweep_vec = np.linspace(float(data.VDS.min()), float(data.VDS.max()), 100)
    elif x_var == "VSB":
        sweep_vec = np.linspace(float(data.VSB.min()), float(data.VSB.max()), 50)
    elif x_var == "L":
        sweep_vec = np.linspace(float(data.L.min()), float(data.L.max()), 50)
    elif x_var in ("GM_ID", "GM/ID"):
        min_val = max(2.0, float(np.nanmin(data.GM_ID[data.GM_ID > 0]))) if data.GM_ID is not None else 2.0
        max_val = min(35.0, float(np.nanmax(data.GM_ID))) if data.GM_ID is not None else 30.0
        sweep_vec = np.linspace(min_val, max_val, 100)
    elif x_var in ("ID_W", "ID/W"):
        min_val = float(np.nanmin(data.ID_W)) if data.ID_W is not None else 1e-3
        max_val = float(np.nanmax(data.ID_W)) if data.ID_W is not None else 10.0
        min_val = max(min_val, 1e-12)
        sweep_vec = np.logspace(np.log10(min_val), np.log10(max_val), 100)
    else:
        sweep_vec = np.linspace(0.1, 10, 100)

    # ── 2. Constants ──
    l_val = constants.get("L", float(data.L.min()))
    vds_val = constants.get("VDS", float(data.VDS.max() / 2))
    vsb_val = constants.get("VSB", 0.0)
    vgs_val = constants.get("VGS", 0.6)
    gmid_val = constants.get("GM_ID", constants.get("GM/ID", 15.0))
    w_user = constants.get("W", 1.0)
    scale = w_user / data.W


    # ── 3. Strategy Detection (Stable Layout Logic) ──
    # Check if we are in an inversion-based cross-lookup mode.
    # We are in cross-lookup if:
    # 1. X-axis itself is a ratio (gm/ID or ID/W)
    # 2. X-axis is geometry/voltage, but we have a target ratio in constants (e.g. Step Variable is gm/ID)
    
    # Priority 1: X-Axis is the ratio
    x_ratio_name = None
    if x_var in ["GM_ID", "GM/ID", "ID_W", "ID/W"]:
        x_ratio_name = x_var.upper().replace("/", "_")
        is_cross_lookup = True
        target_ratio_val = sweep_vec
    # Priority 2: Constant ratio provided (from Step Engine or Strategy Dropdown)
    else:
        # Detect if we should use GM_ID or ID_W as bias target
        bias_mode = constants.get("_BIAS_MODE", "VGS")
        # Step Variable takes priority over Strategy Dropdown
        # skey = step_var.upper().replace("/", "_") in view_plotter.py
        if "GM_ID" in constants or "GM/ID" in constants:
            x_ratio_name = "GM_ID"
            is_cross_lookup = True
            target_ratio_val = constants.get("GM_ID", constants.get("GM/ID"))
        elif "ID_W" in constants or "ID/W" in constants:
            x_ratio_name = "ID_W"
            is_cross_lookup = True
            target_ratio_val = constants.get("ID_W", constants.get("ID/W"))
        elif bias_mode == "GM_ID" and x_var in ["L", "VDS", "VSB"]:
            x_ratio_name = "GM_ID"
            is_cross_lookup = True
            target_ratio_val = gmid_val
        else:
            is_cross_lookup = False
            target_ratio_val = None

    # ── 4. Expression Normalization ──
    y_expr_orig = y_axis.upper().strip()
    y_expr = y_expr_orig
    
    # Apply aliases
    if y_expr == "FT": y_expr = "GM / (2 * 3.14159 * np.abs(CGG))"
    elif y_expr == "GM_ID * FT": y_expr = "(GM/ID) * (GM / (2 * 3.14159 * np.abs(CGG)))"
    elif y_expr == "CDD / CGG": y_expr = "np.abs(CDD) / np.abs(CGG)"
    elif y_expr == "VEARLY": y_expr = "np.abs(ID / GDS)"
    elif y_expr == "VDSAT": y_expr = "np.abs(VDSAT)"
    elif y_expr == "VTH": y_expr = "VTH"
    
    # ── 5. Variable Extraction & Vector Build ──
    needed_vars = _extract_variables(y_expr)
    vectors = {"np": np}
    
    # Determine bias points for lookup
    if is_cross_lookup:
        # Cross-Lookup Mode: 
        # Geometric/Voltage vectors
        L_vec = sweep_vec if x_var == "L" else np.full_like(sweep_vec, l_val)
        VDS_vec = sweep_vec if x_var == "VDS" else np.full_like(sweep_vec, vds_val)
        VSB_vec = sweep_vec if x_var == "VSB" else np.full_like(sweep_vec, vsb_val)

        from .reverse_lookup import solve_vgs
        vgs_vec = solve_vgs(data, target_var=x_ratio_name, target_val=target_ratio_val, L=L_vec, VDS=VDS_vec, VSB=VSB_vec)
        
        vectors.update({"L": L_vec, "VGS": vgs_vec, "VDS": VDS_vec, "VSB": VSB_vec})
        for var in needed_vars:
            if var not in vectors:
                vectors[var] = lookup(data, var, L=L_vec, VGS=vgs_vec, VDS=VDS_vec, VSB=VSB_vec)
    else:
        bias = {"L": l_val, "VDS": vds_val, "VSB": vsb_val, "VGS": vgs_val}
        bias[x_var] = sweep_vec
        vectors.update({k: (np.full_like(sweep_vec, v) if np.isscalar(v) else v) for k, v in bias.items()})
        for var in needed_vars:
            if var not in vectors:
                vectors[var] = lookup(data, var, **bias)

    # ── 5. Scaling & Eval ──
    for var in needed_vars:
        if var.upper() in EXTRINSIC_PARAMS and var in vectors:
            vectors[var] *= scale
            
    y_final = _eval_math(y_expr, vectors)
    return sweep_vec, y_final
