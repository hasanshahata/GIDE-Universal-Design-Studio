"""
Pickle loader for gm/ID LUT data.
GIDE V3 now exclusively supports Python-generated .pkl files.
"""

from __future__ import annotations

import os
import pickle
import sys
from dataclasses import dataclass
from typing import Optional

import numpy as np

# Ensure backwards compatibility for pickles created with NumPy 1.x but loaded in NumPy 2.x+
try:
    if 'numpy.core.multiarray' not in sys.modules:
        import numpy._core.multiarray
        sys.modules['numpy.core.multiarray'] = numpy._core.multiarray
except Exception:
    pass


# ── Data container ─────────────────────────────────────────────────────

@dataclass
class LUTData:
    """Holds all LUT arrays and grid vectors for one device type."""

    # Grid vectors
    L: np.ndarray       # (nL,)
    VGS: np.ndarray     # (nVGS,)
    VDS: np.ndarray     # (nVDS,)
    VSB: np.ndarray     # (nVSB,)
    W: float            # reference width used in simulation

    # 4-D parameter arrays
    ID: np.ndarray
    VT: np.ndarray
    GM: np.ndarray
    GMB: np.ndarray
    GDS: np.ndarray
    CGG: np.ndarray
    CGS: np.ndarray
    CGD: np.ndarray
    CDD: np.ndarray
    CSS: np.ndarray
    VDSAT: np.ndarray
    VTH: np.ndarray

    # Optional fields
    CSB: Optional[np.ndarray] = None
    CDB: Optional[np.ndarray] = None
    CGB: Optional[np.ndarray] = None
    CSG: Optional[np.ndarray] = None
    CDG: Optional[np.ndarray] = None
    STH: Optional[np.ndarray] = None
    SFL: Optional[np.ndarray] = None
    VA: Optional[np.ndarray] = None
    fT: Optional[np.ndarray] = None
    GM_ID: Optional[np.ndarray] = None
    GM_GDS: Optional[np.ndarray] = None
    ID_W: Optional[np.ndarray] = None

    # Metadata
    is_pmos: bool = False
    INFO: str = ""

    @property
    def ndim_grid(self) -> int:
        return 3 if self.VSB.size <= 1 else 4

    @property
    def grid_vectors(self):
        if self.ndim_grid == 4:
            return (self.L, self.VGS, self.VDS, self.VSB)
        return (self.L, self.VGS, self.VDS)


# ── PMOS absolute-value fields ─────────────────────────────────────────

_ABS_FIELDS = [
    "ID", "GM", "GMB", "GDS",
    "CGG", "CGS", "CSG", "CGD", "CDG", "CGB",
    "CDD", "CSS", "VDSAT", "CSB", "CDB"
]


# ── Preprocessing Helpers ──────────────────────────────────────────────

def _smooth_data(arr: np.ndarray, sigma: float = 0.2) -> np.ndarray:
    """Light Gaussian smoothing to eliminate simulation jitter."""
    try:
        from scipy.ndimage import gaussian_filter
        return gaussian_filter(arr, sigma=sigma)
    except ImportError:
        return arr


# ── Loader ─────────────────────────────────────────────────────────────

def load_lut(filepath: str, is_pmos: bool = False) -> LUTData:
    """Load a LUT file (exclusively .pkl) and return a :class:`LUTData` instance."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"LUT file not found: {filepath}")

    with open(filepath, 'rb') as f:
        d = pickle.load(f)

    # Smart unit detection for L and W
    raw_L = np.ascontiguousarray(d['L'], dtype=np.float64).ravel()
    l_scale = 1.0 if np.max(raw_L) < 1e-3 else 1e-6
    
    raw_W = float(d.get("W", d.get("w", 1.0)))
    nf = int(d.get("NFING", d.get("fingers", d.get("nf", 1))))
    raw_W_total = raw_W * nf
    w_scale = 1.0 if raw_W_total < 1e-3 else 1e-6
    
    # Dynamic key detection for GMB/ids variants
    gmb_src = 'gmb' if 'gmb' in d else 'gmbs'
    id_src = 'ids' if 'ids' in d else 'ID'
    va_src = next((k for k in ['va', 'vearly', 'v_early'] if k in d), 'va')
    
    mapping = {
        'ID': id_src, 'GM': 'gm', 'GDS': 'gds', 'VT': 'vth', 'VTH': 'vth',
        'GMB': gmb_src, 'CGG': 'cgg', 'CGS': 'cgs', 'CGD': 'cgd',
        'CDD': 'cdd', 'CSS': 'css', 'VDSAT': 'vdsat', 'fT': 'fT',
        'GM_ID': 'GM_ID', 'GM_GDS': 'GM_GDS', 'VA': va_src
    }


    
    data_args = {
        'L': raw_L * l_scale,
        'VGS': np.ascontiguousarray(d['VGS'], dtype=np.float64).ravel(),
        'VDS': np.ascontiguousarray(d['VDS'], dtype=np.float64).ravel(),
        'VSB': np.ascontiguousarray(d['VSB'], dtype=np.float64).ravel(),
        'W': raw_W_total * w_scale,
        'is_pmos': is_pmos,
        'INFO': str(d.get('INFO', ''))
    }
    
    for target, source in mapping.items():
        if source in d:
            data_args[target] = np.ascontiguousarray(d[source], dtype=np.float64)
        else:
            # Fallback to None so derive_field() or lookup logic can handle them
            data_args[target] = None

    data = LUTData(**data_args)
    
    # Optional fields
    for k_in, k_out in [('csg', 'CSG'), ('cdg', 'CDG'), ('cgb', 'CGB'), ('csb', 'CSB'), ('cdb', 'CDB')]:
        if k_in in d:
            setattr(data, k_out, np.ascontiguousarray(d[k_in], dtype=np.float64))

    # PMOS Magnitude Enforcement: Fix for negative ID/GM/etc. causing inversion/convergence issues
    if is_pmos:
        for fname in _ABS_FIELDS:
            arr = getattr(data, fname, None)
            if isinstance(arr, np.ndarray):
                setattr(data, fname, np.abs(arr))

    # Preprocessing & Derived Fields
    for fname in ["ID", "GM", "CGG"]:
        arr = getattr(data, fname, None)
        if arr is not None:
            # Light smoothing for solver stability
            clean_arr = _smooth_data(arr)
            setattr(data, fname, clean_arr)

    # 4. Calculate Early Voltage (VA = ID / GDS) if not provided
    if (data.VA is None or np.all(data.VA == 0)) and data.ID is not None and data.GDS is not None:
        with np.errstate(divide='ignore', invalid='ignore'):
            data.VA = data.ID / data.GDS

            data.VA[~np.isfinite(data.VA)] = 0.0
            # Light smoothing for VA as it's often noisy
            data.VA = _smooth_data(data.VA)

    # 5. Dynamic Ratio Derivation (Smart Loader)
    # This ensures that gm/ID, fT, etc. are always synchronized with the 
    # possibly absolute-magnified and smoothed physics data.
    with np.errstate(divide='ignore', invalid='ignore'):
        if data.ID is not None and data.GM is not None:
            data.GM_ID = data.GM / data.ID
        
        if data.ID is not None:
            data.ID_W = data.ID / data.W
            
        if data.GM is not None and data.GDS is not None:
            data.GM_GDS = data.GM / data.GDS
            
        if data.GM is not None and data.CGG is not None:
            # fT = gm / (2 * pi * Cgg)
            data.fT = data.GM / (2 * np.pi * np.abs(data.CGG))

        # Handle NaNs/Infs from potential divide-by-zero
        for field in ["GM_ID", "ID_W", "GM_GDS", "fT"]:
            arr = getattr(data, field, None)
            if isinstance(arr, np.ndarray):
                arr[~np.isfinite(arr)] = 0.0

    return data
