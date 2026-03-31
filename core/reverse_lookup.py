"""
Reverse VGS lookup for gm/ID methodology.

Python port of MATLAB ``lookupVGS.m``.  Finds the gate-source voltage
that produces a target gm/ID (or other ratio) at a given bias point.
"""

from __future__ import annotations

from typing import Union

import numpy as np
from scipy.interpolate import interp1d, PchipInterpolator

from .data_loader import LUTData
from .lookup_engine import lookup


def lookupVGS(
    data: LUTData,
    *,
    L: float | None = None,
    VDS: float | None = None,
    VSB: float = 0.0,
    target_var: str = "GM_ID",
    target_val: Union[float, np.ndarray] = 15.0,
    method: str = "pchip",
) -> np.ndarray:
    """Find VGS for a target ratio (e.g. GM_ID, ID_W) at the given bias point.

    Parameters
    ----------
    data : LUTData
        Loaded lookup table.
    L : float
        Channel length.
    VDS : float
        Drain-source voltage.
    VSB : float
        Bulk-source voltage.
    target_var : str
        The variable to search against (default "GM_ID").
    target_val : float or array
        The value to look up.
    method : str
        Interpolation method.

    Returns
    -------
    np.ndarray
        The VGS value(s).
    """
    if L is None:
        L = float(data.L.min())
    if VDS is None:
        VDS = float(data.VDS.max() / 2)

    target = np.atleast_1d(np.asarray(target_val, dtype=np.float64)).ravel()

    # Build target_var vs VGS curve at the specified (L, VDS, VSB)
    vgs_vec = data.VGS.copy()
    curve = lookup(
        data, target_var,
        L=L, VGS=vgs_vec, VDS=VDS, VSB=VSB,
    )

    # Remove NaN entries
    mask = np.isfinite(curve)
    curve_clean = curve[mask]
    vgs_clean = vgs_vec[mask]

    if len(curve_clean) < 2:
        return np.full_like(target, np.nan)

    # Ratio is monotonically varying with VGS
    # Remove any non-monotonic numerical noise points to ensure strict monotonicity
    if curve_clean[-1] < curve_clean[0]:
        cc = curve_clean[::-1]
        vc = vgs_clean[::-1]
    else:
        cc = curve_clean
        vc = vgs_clean

    keep = [0]
    last_x = cc[0]
    for i in range(1, len(cc)):
        if cc[i] > last_x + 1e-12:
            keep.append(i)
            last_x = cc[i]
            
    curve_sorted = cc[keep]
    vgs_sorted = vc[keep]

    if len(curve_sorted) < 2:
        return np.full_like(target, np.nan)

    if method == "pchip":
        f = PchipInterpolator(curve_sorted, vgs_sorted, extrapolate=False)
    else:
        try:
            f = interp1d(curve_sorted, vgs_sorted, kind=method,
                         bounds_error=False, fill_value=np.nan)
        except Exception:
            f = interp1d(curve_sorted, vgs_sorted, kind="linear",
                         bounds_error=False, fill_value=np.nan)

    result = f(target)
    return result


def solve_vgs(
    data: LUTData,
    target_var: str,
    target_val: Union[float, np.ndarray],
    L: Union[float, np.ndarray],
    VDS: Union[float, np.ndarray],
    VSB: Union[float, np.ndarray] = 0.0,
) -> np.ndarray:
    """Vectorized VGS solver that handles N-dimensional broadcasting.
    
    Can solve for a single target across multiple bias points (e.g. L sweep)
    OR solve for multiple targets at a single bias point (e.g. GM_ID sweep).
    """
    t_arr = np.atleast_1d(np.asarray(target_val, dtype=np.float64))
    l_arr = np.atleast_1d(np.asarray(L, dtype=np.float64))
    vds_arr = np.atleast_1d(np.asarray(VDS, dtype=np.float64))
    vsb_arr = np.atleast_1d(np.asarray(VSB, dtype=np.float64))
    
    # Broadcast all to a common shape
    b_t, b_l, b_vds, b_vsb = np.broadcast_arrays(t_arr, l_arr, vds_arr, vsb_arr)
    
    results = np.zeros(b_t.shape)
    it = np.nditer([b_t, b_l, b_vds, b_vsb], flags=['multi_index'])
    while not it.finished:
        idx = it.multi_index
        vgs_val = lookupVGS(
            data, 
            target_var=target_var, 
            target_val=b_t[idx], 
            L=b_l[idx], 
            VDS=b_vds[idx], 
            VSB=b_vsb[idx]
        )
        results[idx] = float(np.squeeze(vgs_val))
        it.iternext()
        
    return results
