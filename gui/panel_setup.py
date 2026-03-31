"""
Panel 1 — Setup & Globals (Sidebar)

Handles data loading (NMOS/PMOS .pkl files), device type selection,
and global biasing constants (VDS, VSB).
"""

from __future__ import annotations
from typing import Optional
import customtkinter as ctk

from core.utils import parse_eng

# --- Precision Observer Tonal Palette ---
C_BASE = "#070e1a"
C_SURFACE_LOW = "#0c1321" 
C_SURFACE_HIGH = "#172030"
C_SURFACE_HIGHEST = "#1c2637"
C_ON_SURFACE = "#e5ebfd"
C_ON_SURFACE_VARIANT = "#8fa3c0"
C_PRIMARY = "#89acff"
C_PRIMARY_DIM = "#5c85d6"
C_ACCENT = "#68fadd"


class CustomInput(ctk.CTkFrame):
    """A 'machined' input field: recessed background, bottom highlight."""
    def __init__(self, master, placeholder: str = "", default: str = ""):
        super().__init__(master, fg_color="transparent", height=42)
        self.pack_propagate(False)

        self.inner = ctk.CTkFrame(self, fg_color=C_SURFACE_HIGHEST, corner_radius=6)
        self.inner.pack(fill="both", expand=True)

        self.entry = ctk.CTkEntry(
            self.inner, placeholder_text=placeholder,
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=C_ON_SURFACE,
            placeholder_text_color="#5c6d8a",
            fg_color="transparent",
            border_width=0,
            height=38
        )
        self.entry.pack(fill="both", expand=True, padx=8, pady=2)
        if default:
            self.entry.insert(0, default)

        self.highlight = ctk.CTkFrame(self, height=2, fg_color="transparent", corner_radius=0)
        self.highlight.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw", y=-1)

        self.entry.bind("<FocusIn>", self._on_focus)
        self.entry.bind("<FocusOut>", self._on_blur)

    def _on_focus(self, event):
        self.highlight.configure(fg_color=C_PRIMARY_DIM)
        self.inner.configure(corner_radius=4) 

    def _on_blur(self, event):
        self.highlight.configure(fg_color="transparent")
        self.inner.configure(corner_radius=6)

    def get(self) -> str:
        return self.entry.get()

    def set_error(self, is_error: bool):
        if is_error:
            self.highlight.configure(fg_color="#ff8866")
        else:
            self._on_blur(None)


class PanelSetup(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # ── Global Biases (Biasing Constraints Only) ──────────────────
        ctk.CTkLabel(
            container, text="GLOBAL BIASES",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            text_color=C_ON_SURFACE_VARIANT, anchor="w",
        ).pack(fill="x", pady=(0, 16))

        # VDS
        ctk.CTkLabel(
            container, text="Drain-Source (VDS) e.g. 900m",
            font=ctk.CTkFont(size=11), text_color=C_ON_SURFACE_VARIANT, anchor="w"
        ).pack(fill="x", pady=(0, 4))
        
        self.fld_vds = CustomInput(container, default="", placeholder="0.6 (e.g. 600m)")
        self.fld_vds.pack(fill="x", pady=(0, 16))

        # VBS
        ctk.CTkLabel(
            container, text="Source-Bulk (VBS) e.g. 0m",
            font=ctk.CTkFont(size=11), text_color=C_ON_SURFACE_VARIANT, anchor="w"
        ).pack(fill="x", pady=(0, 4))
        
        self.fld_vbs = CustomInput(container, default="", placeholder="0 (e.g. 10m)")
        self.fld_vbs.pack(fill="x", pady=(0, 16))

        # ── Tech Summary (Utilizing empty space) ──────────────────────
        ctk.CTkLabel(
            container, text="TECH SUMMARY",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            text_color=C_ON_SURFACE_VARIANT, anchor="w",
        ).pack(fill="x", pady=(16, 8))

        self.tech_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.tech_frame.pack(fill="x", padx=4)

        self.tech_labels = {}
        for row, (label_text, key) in enumerate([
            ("Channel Length:", "L"),
            ("VGS Range:", "VGS"),
            ("Reference W:", "W"),
            ("Temperature:", "TEMP")
        ]):
            lbl = ctk.CTkLabel(self.tech_frame, text=label_text, font=ctk.CTkFont(size=11), text_color=C_ON_SURFACE_VARIANT, anchor="w")
            lbl.grid(row=row, column=0, sticky="w", pady=2)
            
            val = ctk.CTkLabel(self.tech_frame, text="--", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_ON_SURFACE, anchor="e")
            val.grid(row=row, column=1, sticky="e", pady=2)
            self.tech_frame.columnconfigure(1, weight=1)
            self.tech_labels[key] = val

        # Status block
        self.status_block = ctk.CTkFrame(self, fg_color=C_BASE, height=60, corner_radius=8)
        self.status_block.pack(side="bottom", fill="x", padx=16, pady=20)
        self.status_block.pack_propagate(False)
        ctk.CTkLabel(self.status_block, text="Interpolation Status", font=ctk.CTkFont(size=10), text_color=C_ON_SURFACE_VARIANT, anchor="w").pack(fill="x", padx=12, pady=(10, 0))
        self.status_lbl = ctk.CTkLabel(self.status_block, text="Waiting for .pkl data...", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ff8866", anchor="w")
        self.status_lbl.pack(fill="x", padx=12)

    def update_tech_info(self, data: Optional[any]):
        """Populates the Tech Summary with data from the current LUT."""
        if data is None:
            for lbl in self.tech_labels.values(): lbl.configure(text="--")
            return
            
        from core.utils import eng
        l_min, l_max = data.L.min(), data.L.max()
        v_min, v_max = data.VGS.min(), data.VGS.max()
        
        # Display ranges using engineering notation
        self.tech_labels["L"].configure(text=f"{eng(l_min)}m - {eng(l_max)}m")
        self.tech_labels["VGS"].configure(text=f"{v_min:.1f}V - {v_max:.1f}V")
        self.tech_labels["W"].configure(text=f"{eng(data.W)}m")
        
        # Temperature detection from INFO string metadata
        import re
        # Look for patterns like "temp=27" or "temp: 125"
        temp_match = re.search(r'temp\s*[:=]\s*([-+]?\d+\.?\d*)', data.INFO, re.IGNORECASE)
        temp_str = f"{temp_match.group(1)}°C" if temp_match else "27°C (Def)"
        self.tech_labels["TEMP"].configure(text=temp_str)

    def set_sizing_mode(self, mode_name: str):
        pass # No longer needed in purely Universal model

    def get_L(self) -> Optional[float]:
        return None # Length now handled by Sizing Dashboard DOFs

    def get_gain_target(self) -> Optional[float]:
        return None # Gain now handled by Sizing Dashboard DOFs

    def get_VDS(self) -> float:
        val = self.fld_vds.get().strip() or "0.6"
        try:
            return parse_eng(val)
        except Exception:
            self.fld_vds.set_error(True)
            return 0.6

    def get_VSB(self) -> float:
        val = self.fld_vbs.get().strip() or "0"
        try:
            return parse_eng(val)
        except Exception:
            self.fld_vbs.set_error(True)
            return 0.0
