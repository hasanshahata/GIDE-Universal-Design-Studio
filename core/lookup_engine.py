"""
Forward lookup engine for gm/ID LUT data.

Python port of MATLAB ``lookup.m`` with three interpolation modes:

* **Mode 1** – Simple field at (L, VGS, VDS, VSB)
* **Mode 2** – Ratio of two fields (e.g. GM_ID, GM_GDS)
* **Mode 3** – Cross-lookup: one ratio as a function of another

All N-D interpolation uses :class:`scipy.interpolate.RegularGridInterpolator`.
"""

from __future__ import annotations

from typing import Optional, Union

import numpy as np
from scipy.interpolate import RegularGridInterpolator, interp1d, PchipInterpolator

from .data_loader import LUTData

# ── Valid ratio names (must match MATLAB VALID_RATIOS) ─────────────────

VALID_RATIOS = {
    "GM_ID", "GM_GDS", "GM_CGG", "GM_CGD", "ID_W",
    "CGG_W", "CGD_W", "CDD_W", "CSS_W", "CSG_W", "CDG_W",
    "GMB_GM", "GDS_GM",
}


def _is_ratio(name: str) -> bool:
    return name.upper() in {r.upper() for r in VALID_RATIOS}


def _split_ratio(name: str):
    """Split 'NUM_DEN' → ('NUM', 'DEN')."""
    idx = name.index("_")
    return name[:idx], name[idx + 1:]


def _get_field(data: LUTData, name: str) -> np.ndarray:
    """Retrieve a raw field array from the LUT."""
    arr = getattr(data, name, None)
    if arr is None:
        raise KeyError(f"Field '{name}' not found in LUT data")
    return np.asarray(arr, dtype=np.float64)


def _make_interpolator(data: LUTData, values: np.ndarray) -> RegularGridInterpolator:
    """Build a RegularGridInterpolator over the LUT grid."""
    grid = data.grid_vectors
    # Trim values to match grid dimensions (3D or 4D)
    v = values
    if data.ndim_grid == 3 and v.ndim == 4:
        v = v[:, :, :, 0]
    return RegularGridInterpolator(
        grid, v, method="linear", bounds_error=False, fill_value=None
    )


def _interp_at(
    data: LUTData,
    values: np.ndarray,
    L: float,
    VGS: Union[float, np.ndarray],
    VDS: float,
    VSB: float,
) -> np.ndarray:
    """Interpolate *values* at given bias point(s).

    Returns a 1-D array with one element per VGS value.
    """
    interp = _make_interpolator(data, values)
    # Convert inputs to at least 1D
    L_arr = np.atleast_1d(np.asarray(L, dtype=np.float64))
    VGS_arr = np.atleast_1d(np.asarray(VGS, dtype=np.float64))
    VDS_arr = np.atleast_1d(np.asarray(VDS, dtype=np.float64))
    VSB_arr = np.atleast_1d(np.asarray(VSB, dtype=np.float64))

    # Broadcast to common shape
    b_L, b_VGS, b_VDS, b_VSB = np.broadcast_arrays(L_arr, VGS_arr, VDS_arr, VSB_arr)

    if data.ndim_grid == 4:
        pts = np.column_stack([
            b_L.ravel(),
            b_VGS.ravel(),
            b_VDS.ravel(),
            b_VSB.ravel(),
        ])
    else:
        pts = np.column_stack([
            b_L.ravel(),
            b_VGS.ravel(),
            b_VDS.ravel(),
        ])

    return interp(pts).reshape(b_VGS.shape)


# ── Public API ─────────────────────────────────────────────────────────

def lookup(
    data: LUTData,
    outvar: str,
    *,
    L: Optional[float] = None,
    VGS: Optional[Union[float, np.ndarray]] = None,
    VDS: Optional[float] = None,
    VSB: float = 0.0,
    # Mode-3 cross-lookup parameters
    cross_var: Optional[str] = None,
    cross_val: Optional[Union[float, np.ndarray]] = None,
    method: str = "pchip",
) -> np.ndarray:
    """Query the LUT for *outvar*.

    Parameters
    ----------
    data : LUTData
        Loaded lookup table.
    outvar : str
        Output variable.  Can be a raw field (``'ID'``, ``'GM'``, …) or
        a ratio (``'GM_ID'``, ``'GM_GDS'``, …).
    L, VGS, VDS, VSB : float or array
        Bias-point coordinates.  Defaults mirror the MATLAB function.
    cross_var, cross_val : str, array
        For Mode 3 cross-lookups, the independent ratio name and its
        desired values (e.g. ``cross_var='GM_ID'``,
        ``cross_val=np.arange(5, 25, 0.5)``).
    method : str
        Interpolation method for the 1-D cross-lookup step
        (``'pchip'`` or ``'linear'``).

    Returns
    -------
    np.ndarray
        Interpolated result.
    """
    # Defaults
    if L is None:
        L = float(data.L.min())
    if VDS is None:
        VDS = float(data.VDS.max() / 2)
    if VGS is None:
        VGS = data.VGS.copy()

    out_ratio = _is_ratio(outvar)
    cross_ratio = cross_var is not None and _is_ratio(cross_var)

    # ── Determine mode ──
    if cross_ratio:
        mode = 3
    elif out_ratio:
        mode = 2
    else:
        mode = 1

    # ── Build y-data ──
    # Prioritize pre-calculated fields if they exist raw in the LUT
    if getattr(data, outvar, None) is not None:
        ydata = _get_field(data, outvar)
    elif out_ratio:
        num_name, den_name = _split_ratio(outvar)
        num_f = _get_field(data, num_name)
        den_f = _get_field(data, den_name)
        with np.errstate(divide='ignore', invalid='ignore'):
            ydata = num_f / den_f

    else:
        ydata = _get_field(data, outvar)

    # ── Mode 3: cross-lookup ──
    if mode == 3:
        if cross_ratio:
            xnum, xden = _split_ratio(cross_var)
            with np.errstate(divide='ignore', invalid='ignore'):
                xdata = _get_field(data, xnum) / _get_field(data, xden)
        else:
            xdata = _get_field(data, cross_var)
        xdesired = np.atleast_1d(np.asarray(cross_val, dtype=np.float64)).ravel()

        # Interpolate x and y onto the grid at (L, VGS_full, VDS, VSB)
        x_curve = _interp_at(data, xdata, L, data.VGS, VDS, VSB)
        y_curve = _interp_at(data, ydata, L, data.VGS, VDS, VSB)

        # Remove NaNs
        mask = np.isfinite(x_curve) & np.isfinite(y_curve)
        x_curve = x_curve[mask]
        y_curve = y_curve[mask]

        if len(x_curve) < 2:
            return np.full_like(xdesired, np.nan)

        # Remove any non-monotonic numerical noise points to ensure strict monotonicity
        if x_curve[-1] < x_curve[0]:
            xc = x_curve[::-1]
            yc = y_curve[::-1]
        else:
            xc = x_curve
            yc = y_curve

        keep = [0]
        last_x = xc[0]
        for i in range(1, len(xc)):
            if xc[i] > last_x + 1e-12:
                keep.append(i)
                last_x = xc[i]
                
        xc = xc[keep]
        yc = yc[keep]

        if len(xc) < 2:
            return np.full_like(xdesired, np.nan)

        # 1-D interpolation: y as a function of x
        if method == "pchip":
            f = PchipInterpolator(xc, yc, extrapolate=False)
        else:
            try:
                f = interp1d(xc, yc, kind=method, bounds_error=False,
                             fill_value=np.nan)
            except ValueError:
                f = interp1d(xc, yc, kind="linear", bounds_error=False,
                             fill_value=np.nan)
        return f(xdesired)

    # ── Modes 1 & 2: direct interpolation ──
    return _interp_at(data, ydata, L, VGS, VDS, VSB)
