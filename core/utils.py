from __future__ import annotations
"""
Engineering notation formatter & parser for the gm/ID sizing dashboard.
"""

import sys
import os
import re
import math

# ── Asset Management ──────────────────────────────────────────────────
def resource_path(relative_path: str) -> str:
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Fallback to current directory for development
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# ── Prefix tables ──────────────────────────────────────────────────────
_PREFIXES = [
    ("T", 12), ("G", 9), ("M", 6), ("k", 3), ("", 0),
    ("m", -3), ("μ", -6), ("u", -6), ("n", -9), ("p", -12),
    ("f", -15), ("a", -18),
]

# Robust suffix mapping (case-insensitive where possible, preserved for m/M)
_PREFIX_MAP = {
    "T": 12, "tera": 12,
    "G": 9, "giga": 9,
    "M": 6, "meg": 6, "mega": 6,
    "k": 3, "K": 3, "kilo": 3,
    "m": -3, "milli": -3,
    "u": -6, "μ": -6, "micro": -6,
    "n": -9, "nano": -9,
    "p": -12, "pico": -12,
    "f": -15, "femto": -15,
    "a": -18, "atto": -18,
}


def eng(value: float, unit: str = "") -> str:
    """Format *value* in engineering notation with SI prefix + *unit*.

    Examples
    --------
    >>> eng(1.23e-3, "A")
    '1.230 mA'
    >>> eng(45.6e9, "Hz")
    '45.60 GHz'
    """
    if not math.isfinite(value):
        return f"{value} {unit}".strip()
    if value == 0:
        return f"0 {unit}".strip()

    ax = abs(value)
    for prefix, exp in _PREFIXES:
        if ax >= 10 ** exp:
            v = value / 10 ** exp
            if abs(v) >= 100:
                s = f"{v:.1f}"
            elif abs(v) >= 10:
                s = f"{v:.2f}"
            else:
                s = f"{v:.3f}"
            return f"{s} {prefix}{unit}".strip()

    # Fallback for extremely small values
    v = value / 1e-18
    return f"{v:.3f} a{unit}".strip()


def parse_eng(text: str) -> float:
    """Parse an engineering-notation string and return a float.

    Accepts formats like '17G', '1700meg', '1700M', '1.2m', '0.5μ', '3.3'.
    Case-insensitive except for 'M' (Mega) and 'm' (milli) priority.

    Returns float('nan') on failure.
    """
    if isinstance(text, (int, float)):
        return float(text)

    text = text.strip()
    if not text:
        return float("nan")

    # Match number + optional suffix string
    # Capture 1: Value part (including optional e-notation)
    # Capture 2: Suffix part (letters and μ/µ symbols)
    m = re.match(
        r"^([+-]?[\d.]+(?:[eE][+-]?\d+)?)\s*([a-zA-Zμµ]*)",
        text,
    )
    if not m:
        try:
            return float(text)
        except ValueError:
            return float("nan")

    num_str, suffix = m.group(1), m.group(2)
    
    if not suffix:
        try:
            return float(num_str)
        except ValueError:
            return float("nan")

    # 1. Exact case-sensitive match (prioritizes M/m)
    exp = _PREFIX_MAP.get(suffix)
    if exp is None:
        # 2. Case-insensitive fallback
        exp = _PREFIX_MAP.get(suffix.lower())
    
    if exp is None:
        # If still not found, check if only the first char matches a prefix
        # (SPICE compatibility for things like '1uA')
        for i in range(min(4, len(suffix)), 0, -1):
            s_try = suffix[:i]
            exp = _PREFIX_MAP.get(s_try)
            if exp is None:
                exp = _PREFIX_MAP.get(s_try.lower())
            if exp is not None:
                break

    if exp is None:
        try:
            return float(num_str)
        except ValueError:
            return float("nan")

    try:
        return float(num_str) * 10 ** exp
    except ValueError:
        return float("nan")


def parse_eng_list(text: str) -> list[float]:
    """Parse a list of engineering-notation values.
    Supports:
    - Comma-separated: '180n, 360n, 540n'
    - Colon-range (Start:Step:Stop): '0.4 : 0.1 : 1.0'
    """
    if not text or not text.strip():
        return []

    # 1. Colon Range (MATLAB style Start:Step:Stop)
    if ":" in text:
        parts = [p.strip() for p in text.split(":")]
        if len(parts) == 3:
            import numpy as np
            try:
                start = parse_eng(parts[0])
                step = parse_eng(parts[1])
                stop = parse_eng(parts[2])
                if any(not math.isfinite(x) for x in [start, step, stop]):
                    return []
                # Handle cases where step is zero or infinite
                if step == 0: return [start]
                
                # Use np.arange-like logic with an epsilon to include the endpoint
                vals = np.arange(start, stop + (abs(step) / 100), step)
                return vals.tolist()
            except Exception:
                return []

    # 2. Discrete List (Comma or Semicolon separated)
    raw_parts = text.replace(";", ",").split(",")
    results = []
    for p in raw_parts:
        if not p.strip(): continue
        val = parse_eng(p.strip())
        if math.isfinite(val):
            results.append(val)
            
    return results
