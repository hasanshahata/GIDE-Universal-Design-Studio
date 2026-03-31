"""
Modular Sizing Dashboard — Universal Degrees of Freedom Model

Unified Sizing Engine Interface:
- Purely Universal Design: No more legacy sizing modes.
- Top-Level Variable Pickers: Select any three independent design variables.
- One Variable per Bucket: Backend logic enforces a physically valid design point.
"""

from __future__ import annotations
from typing import Callable, Optional
import customtkinter as ctk

from core.sizing_engine import OperatingPoint
from core.utils import eng
from .panel_setup import C_BASE, C_SURFACE_LOW, C_SURFACE_HIGH, C_SURFACE_HIGHEST, C_ON_SURFACE, C_ON_SURFACE_VARIANT, C_PRIMARY, C_PRIMARY_DIM, C_ACCENT


class PanelSizing(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_calculate: Callable[[str, dict], None],
        on_mode_change: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.on_calculate = on_calculate
        self.on_mode_change_cb = on_mode_change

        # Bucket mapping for Universal Mode (Updated Unit Display)
        self.VAR_TO_BUCKET = {
            "gm/ID (V⁻¹)": 1, "VGS (V)": 1, "fT (Hz)": 1, "ID/W (A/m)": 1,
            "Length (m)": 2, "Gain (V/V)": 2, "Early Voltage (VA)": 2,
            "Target ID (A)": 3, "Target Width (m)": 3, "Target gm (S)": 3
        }
        self.ALL_VARS = list(self.VAR_TO_BUCKET.keys())
        
        # Padding container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=48, pady=24)


        # ── Header ──────────────────────────────────────────────────
        ctk.CTkLabel(
            container, text="Universal Sizing Engine",
            font=ctk.CTkFont(family="Manrope", size=24, weight="bold"),
            text_color=C_ON_SURFACE,
        ).pack(anchor="w", pady=(0, 4))
        
        ctk.CTkLabel(
            container, text="Configure 3 Degrees of Freedom across design buckets",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=C_ON_SURFACE_VARIANT,
        ).pack(anchor="w", pady=(0, 32))

        # ── Column Selectors (ABOVE the rectangles) ────────────────
        self.header_frame = ctk.CTkFrame(container, fg_color="transparent", height=85)
        self.header_frame.pack(fill="x", pady=(0, 10))
        self.header_frame.grid_propagate(False)
        self.header_frame.columnconfigure((0, 1, 2), weight=1, uniform="cols")

        # Bucket Titles
        bucket_titles = ["Inversion Level", "Geometry & Performance", "Target Scaling"]
        for i, title in enumerate(bucket_titles):
            ctk.CTkLabel(
                self.header_frame, text=title.upper(),
                font=ctk.CTkFont(family="Inter", size=9, weight="bold"),
                text_color=C_ON_SURFACE_VARIANT
            ).grid(row=0, column=i, sticky="sw", pady=(0, 6), padx=4)

        self.pickers = []
        for i in range(3):
            # Wrapper frame to provide the rectangular border (since ctk.CTkOptionMenu doesn't support border_width/border_color)
            wrapper = ctk.CTkFrame(
                self.header_frame, fg_color=C_SURFACE_HIGH, 
                border_width=1, border_color=C_SURFACE_HIGHEST,
                corner_radius=8
            )
            wrapper.grid(row=1, column=i, sticky="nw", padx=(4, 12))

            p = ctk.CTkOptionMenu(
                wrapper, values=[], height=32, width=175,
                fg_color=C_SURFACE_HIGH, 
                button_color=C_SURFACE_HIGHEST,
                text_color=C_PRIMARY,
                font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                anchor="w", 
                command=self._on_variable_change
            )
            p.pack(fill="both", expand=True, padx=2, pady=2)
            self.pickers.append(p)

        # ── Inputs Frames (The "Rectangles") ────────────────────────
        self.inputs_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.inputs_frame.pack(fill="x", pady=(0, 24))
        self.inputs_frame.columnconfigure((0, 1, 2), weight=1, uniform="cols")

        self.col1 = ctk.CTkFrame(self.inputs_frame, fg_color=C_BASE, corner_radius=12, height=130)
        self.col1.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.col1.pack_propagate(False)

        self.col2 = ctk.CTkFrame(self.inputs_frame, fg_color=C_BASE, corner_radius=12, height=130)
        self.col2.grid(row=0, column=1, sticky="nsew", padx=(10, 10))
        self.col2.pack_propagate(False)

        self.col3 = ctk.CTkFrame(self.inputs_frame, fg_color=C_BASE, corner_radius=12, height=130)
        self.col3.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        self.col3.pack_propagate(False)

        # Centered Entry Fields (Pure Placeholders, no default values)
        self.fld_val1 = ctk.CTkEntry(self.col1, font=ctk.CTkFont(family="Manrope", size=28, weight="bold"), text_color=C_ON_SURFACE, fg_color="transparent", border_width=0, justify="center", placeholder_text="---")
        self.fld_val1.place(relx=0.5, rely=0.5, anchor="center")
        
        self.fld_val2 = ctk.CTkEntry(self.col2, font=ctk.CTkFont(family="Manrope", size=28, weight="bold"), text_color=C_ON_SURFACE, fg_color="transparent", border_width=0, justify="center", placeholder_text="---")
        self.fld_val2.place(relx=0.5, rely=0.5, anchor="center")

        self.fld_val3 = ctk.CTkEntry(self.col3, font=ctk.CTkFont(family="Manrope", size=28, weight="bold"), text_color=C_ON_SURFACE, fg_color="transparent", border_width=0, justify="center", placeholder_text="---")
        self.fld_val3.place(relx=0.5, rely=0.5, anchor="center")

        # Set default selections
        self.pickers[0].set("gm/ID (V⁻¹)")
        self.pickers[1].set("Length (m)")
        self.pickers[2].set("Target ID (A)")
        self._update_universal_options()

        # ── Prediction Outcome ──────────────────────────────────────
        self.predict_frame = ctk.CTkFrame(container, fg_color=C_SURFACE_HIGH, corner_radius=12, height=130)
        self.predict_frame.pack(fill="x", pady=(16, 0))
        self.predict_frame.pack_propagate(False)

        ctk.CTkLabel(self.predict_frame, text="WIDTH PREDICTION", font=ctk.CTkFont(family="Inter", size=10, weight="bold"), text_color=C_ON_SURFACE_VARIANT).place(relx=0.1, rely=0.15, anchor="nw")
        self.lbl_optimal = ctk.CTkLabel(self.predict_frame, text="Optimal Solution Found", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_ACCENT, fg_color="#0d2424", corner_radius=6, padx=12, pady=4)
        
        self.lbl_W_pred = ctk.CTkLabel(self.predict_frame, text="--", font=ctk.CTkFont(family="Manrope", size=36, weight="bold"), text_color=C_ON_SURFACE)
        self.lbl_W_pred.place(relx=0.5, rely=0.55, anchor="center")
        self.lbl_W_unit = ctk.CTkLabel(self.predict_frame, text="µm", font=ctk.CTkFont(size=16, weight="bold"), text_color="#5c6d8a")
        self.lbl_W_unit.place(relx=0.66, rely=0.6, anchor="center")

        # ── Compute Button ──────────────────────────────────────────
        bottom_area = ctk.CTkFrame(container, fg_color="transparent")
        bottom_area.pack(side="bottom", fill="x", pady=(32, 0))

        self.btn_calc = ctk.CTkButton(
            bottom_area, text="⚡ RUN UNIVERSAL SOLVER",
            height=54,
            font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            fg_color=C_PRIMARY,
            text_color=C_BASE,
            hover_color=C_PRIMARY_DIM,
            corner_radius=8,
            command=self._do_calc
        )
        self.btn_calc.pack(fill="x")

    def _on_variable_change(self, _=None):
        self._update_universal_options()
        self.clear_prediction()

    def _update_universal_options(self):
        """Cross-column filtering: Enforce one variable per design bucket."""
        for i in range(3):
            current_sel = self.pickers[i].get()
            # Buckets used by other columns
            others = [self.pickers[j].get() for j in range(3) if i != j]
            consumed_buckets = {self.VAR_TO_BUCKET.get(v) for v in others if v in self.VAR_TO_BUCKET}
            
            # This column can only use variables in unused buckets
            available = [v for v in self.ALL_VARS if self.VAR_TO_BUCKET.get(v) not in consumed_buckets]
            self.pickers[i].configure(values=available)
            
            # If current selection became illegal, force it to first available
            if current_sel not in available:
                if available: self.pickers[i].set(available[0])

    def _do_calc(self):
        self.btn_calc.configure(text="⚡ Calculating...")
        try:
            from core.utils import parse_eng
            # Use value or fall back to 0 if empty/placeholder
            v1_raw = self.fld_val1.get().strip()
            v2_raw = self.fld_val2.get().strip()
            v3_raw = self.fld_val3.get().strip()

            v1 = parse_eng(v1_raw) if v1_raw else 0.0
            v2 = parse_eng(v2_raw) if v2_raw else 0.0
            v3 = parse_eng(v3_raw) if v3_raw else 0.0

            NAME_TO_KEY = {
                "gm/ID (V⁻¹)": "GM_ID", "VGS (V)": "VGS", "fT (Hz)": "fT", "ID/W (A/m)": "ID_W",
                "Length (m)": "L", "Gain (V/V)": "GM_GDS", "Early Voltage (VA)": "VA",
                "Target ID (A)": "ID", "Target Width (m)": "W", "Target gm (S)": "GM"
            }

            universal_payload = {
                NAME_TO_KEY[self.pickers[0].get()]: v1,
                NAME_TO_KEY[self.pickers[1].get()]: v2,
                NAME_TO_KEY[self.pickers[2].get()]: v3
            }

            # Route to app-level calculate (always Universal Mode)
            self.on_calculate("Universal", {"universal": universal_payload})
            self.btn_calc.configure(text="⚡ RUN UNIVERSAL SOLVER")
        except Exception as e:
            self.btn_calc.configure(text=f"ERROR: {str(e)}")

    def show_prediction(self, W: float):
        W_um = W * 1e6
        self.lbl_W_pred.configure(text=f"{W_um:.2f}", text_color=C_ON_SURFACE)
        self.lbl_optimal.place(relx=0.9, rely=0.15, anchor="ne")

    def clear_prediction(self):
        self.lbl_W_pred.configure(text="--", text_color="#5c6d8a")
        self.lbl_optimal.place_forget()
