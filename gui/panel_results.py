"""
Panel 3 — Operating Point Results (Right Sidebar)

Displays extracted operating-point parameters grouped into distinct cards
floating on the base canvas.
Precision Observer Style:
- Cards with `surface_container_high`
- No borders, spacing-based grouping
- Teal/Orange status dots
- Right-aligned values, subtle left-aligned labels
"""

from __future__ import annotations

import math
import os
from datetime import datetime
from typing import Optional

import customtkinter as ctk

from core.sizing_engine import OperatingPoint
from core.utils import eng
from .panel_setup import C_BASE, C_SURFACE_LOW, C_SURFACE_HIGH, C_ON_SURFACE, C_ON_SURFACE_VARIANT, C_PRIMARY, C_ACCENT


class PanelResults(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._cards: list[ctk.CTkFrame] = []
        self._last_op: Optional[OperatingPoint] = None
        self._last_device: str = "NMOS"

    # ── Public API ─────────────────────────────────────────────────────

    def show_result(self, op: OperatingPoint, device: str = "NMOS"):
        self.clear()
        self._last_op = op
        self._last_device = device

        if not op.ok:
            self.show_error(op.msg or "Calculation failed")
            return

        # ── Dimensions (Primary Geometry) ────────────────────────────
        c0 = self._add_card("DIMENSIONS", is_success=True)
        g0 = ctk.CTkFrame(c0, fg_color="transparent")
        g0.pack(fill="x", padx=16, pady=(8, 16))
        self._add_grid_item(g0, 0, 0, "Width (W)", eng(op.W, "m"))
        self._add_grid_item(g0, 0, 1, "Length (L)", eng(op.L, "m"))

        # ── Biasing Metrics ──────────────────────────────────────────
        c1 = self._add_card("BIASING METRICS", is_alert=True)
        g1 = ctk.CTkFrame(c1, fg_color="transparent")
        g1.pack(fill="x", padx=16, pady=(8, 16))
        
        self._add_grid_item(g1, 0, 0, "ID", eng(op.ID, "A"))
        self._add_grid_item(g1, 0, 1, "ID/W", eng(op.ID_W, "A/m"))
        
        self._add_grid_item(g1, 1, 0, "gm/ID", f"{op.gm_id:.2f} V/V")
        self._add_grid_item(g1, 1, 1, "VGS", eng(op.VGS, "V"))
        
        self._add_grid_item(g1, 2, 0, "VT", eng(op.VT, "V"))
        self._add_grid_item(g1, 2, 1, "VDSAT", eng(op.VDSAT, "V"))

        self._add_grid_item(g1, 3, 0, "VDS", eng(op.VDS, "V"))
        self._add_grid_item(g1, 3, 1, "Early Voltage (VA)", eng(op.VA, "V"))

        # ── Small Signal Parameters ──────────────────────────────────

        c2 = self._add_card("SMALL SIGNAL PARAMETERS", is_success=True)
        
        # Grid layout for small signal (like the mockup)
        grid = ctk.CTkFrame(c2, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(8, 16))
        
        # Row 1 (gm / gds)
        self._add_grid_item(grid, 0, 0, "gm", eng(op.gm, "S"))
        self._add_grid_item(grid, 0, 1, "gds", eng(op.gds, "S"))
        
        # Row 2 (gm/gds inner / intrinsic)
        gain_db = 20 * math.log10(abs(op.gm_gds)) if op.gm_gds > 0 else 0
        self._add_grid_item(grid, 1, 0, "gm/gds (Gain)", f"{op.gm_gds:.1f} V/V")
        self._add_grid_item(grid, 1, 1, "Intrinsic Gain", f"{gain_db:.1f} dB")


        # ── High Frequency Performance ───────────────────────────────
        c3 = self._add_card("HIGH FREQUENCY PERFORMANCE", is_error=True)
        
        # Top massive row for fT
        tr = ctk.CTkFrame(c3, fg_color="transparent")
        tr.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(tr, text="Transit Frequency (fT)", font=ctk.CTkFont(size=12), text_color=C_ON_SURFACE_VARIANT).pack(side="left")
        
        ft_val = eng(op.fT, "Hz")
        num, unit = ft_val.split(" ")
        ctk.CTkLabel(tr, text=f" {unit}", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_ON_SURFACE).pack(side="right")
        ctk.CTkLabel(tr, text=num, font=ctk.CTkFont(family="Inter", size=18, weight="bold"), text_color=C_ON_SURFACE).pack(side="right")

        # Bottom caps row
        caps_frame = ctk.CTkFrame(c3, fg_color="transparent")
        caps_frame.pack(fill="x", padx=16, pady=(8, 16))
        self._add_cap_box(caps_frame, "Cgg", eng(op.Cgg, "F"))
        self._add_cap_box(caps_frame, "Cgd", eng(op.Cgd, "F"))
        self._add_cap_box(caps_frame, "Cdd", eng(op.Cdd, "F"))

        # ── Export Interaction ───────────────────────────────────────
        btn_export = ctk.CTkButton(
            self, text="💾 EXPORT DESIGN REPORT",
            height=48, fg_color="transparent",
            border_color=C_PRIMARY, border_width=1,
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=C_PRIMARY, hover_color=C_SURFACE_HIGH,
            command=self._on_export_click
        )
        btn_export.pack(fill="x", pady=(8, 16))
        self._cards.append(btn_export)

    def _on_export_click(self):
        if not self._last_op: return
        
        filename = ctk.filedialog.asksaveasfilename(
            title="Save Design Report",
            defaultextension=".md",
            filetypes=[("Markdown Report", "*.md"), ("CSV Design Log", "*.csv")],
            initialfile=f"design_{self._last_device.lower()}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        )
        
        if not filename: return
        
        ext = os.path.splitext(filename)[1].lower()
        
        try:
            if ext == ".md":
                # 1. Generate Markdown Report
                report = self._generate_markdown()
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"Markdown report saved to {filename}")
                
            elif ext == ".csv":
                # 2. Append to/Create CSV Log
                csv_data = self._generate_csv()
                write_header = not os.path.exists(filename)
                with open(filename, "a", encoding="utf-8") as f:
                    if write_header:
                        # Full comprehensive header for all design parameters
                        header = "Timestamp,Device,W,L,VGS,VT,VDSAT,VDS,VSB,ID,ID/W,gm,gds,gmb,gm/ID,Gain(V/V),fT,Cgg,Cgd,Cdd,Css,VA"
                        f.write(header + "\n")
                    f.write(csv_data + "\n")
                print(f"Data row appended to {filename}")
                
        except Exception as e:
            self.show_error(f"Export Failed: {str(e)}")

    def _generate_markdown(self) -> str:
        op = self._last_op
        dev = self._last_device.upper()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return f"""# GIDE Professional Design Report
**Date**: {now}
**Device Profile**: {dev} Transistor

## 1. Design Constraints (Biasing)
| Parameter | Value |
|:---|:---|
| Drain-Source Voltage (VDS) | {eng(op.VDS, 'V')} |
| Source-Bulk Voltage (VSB) | {eng(op.VSB, 'V')} |
| Gate-Source Voltage (VGS) | {eng(op.VGS, 'V')} |

## 2. Calculated Dimensions
| Parameter | Value |
|:---|:---|
| **Width (W)** | **{eng(op.W, 'm')}** |
| **Length (L)** | **{eng(op.L, 'm')}** |

## 3. Operating Point Metrics
| Metric | Value |
|:---|:---|
| Drain Current (ID) | {eng(op.ID, 'A')} |
| Current Density (ID/W) | {eng(op.ID_W, 'A/m')} |
| Transconductance (gm) | {eng(op.gm, 'S')} |
| Output Conductance (gds) | {eng(op.gds, 'S')} |
| **gm/ID Efficiency** | **{op.gm_id:.2f} V/V** |
| **Intrinsic Gain** | **{op.gm_gds:.2f} V/V** |

## 4. AC & Parasitics
| Metric | Value |
|:---|:---|
| **Transit Frequency (fT)** | **{eng(op.fT, 'Hz')}** |
| Gate Cap (Cgg) | {eng(op.Cgg, 'F')} |
| Gate-Drain Cap (Cgd) | {eng(op.Cgd, 'F')} |
| Drain Cap (Cdd) | {eng(op.Cdd, 'F')} |

---
*Generated by GIDE Unified Design Studio*
"""

    def _generate_csv(self) -> str:
        op = self._last_op
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # All-parameter log for professional traceability
        params = [
            now, self._last_device, op.W, op.L, op.VGS, op.VT, op.VDSAT, op.VDS, op.VSB, 
            op.ID, op.ID_W, op.gm, op.gds, op.gmb, op.gm_id, op.gm_gds, op.fT, 
            op.Cgg, op.Cgd, op.Cdd, op.Css, op.VA
        ]
        return ",".join(str(p) for p in params)

    def show_error(self, msg: str):
        self.clear()
        c = self._add_card("ERROR", is_error=True)
        lbl = ctk.CTkLabel(
            c, text=msg,
            font=ctk.CTkFont(size=13),
            text_color="#ff8866",
            wraplength=260, justify="left"
        )
        lbl.pack(padx=16, pady=16, anchor="w")

    def clear(self):
        for w in self._cards:
            w.destroy()
        self._cards.clear()


    # ── Builders ───────────────────────────────────────────────────────

    def _add_card(self, title: str, is_alert=False, is_success=False, is_error=False) -> ctk.CTkFrame:
        c = ctk.CTkFrame(self, fg_color=C_SURFACE_HIGH, corner_radius=12)
        c.pack(fill="x", pady=(0, 16))
        self._cards.append(c)

        hdr = ctk.CTkFrame(c, fg_color="transparent", height=40)
        hdr.pack(fill="x", padx=16, pady=(12, 4))
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr, text=title,
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            text_color=C_ON_SURFACE_VARIANT,
        ).pack(side="left")

        # Status dot
        dot_color = "transparent"
        if is_alert: dot_color = "#f4a261" # soft orange
        elif is_success: dot_color = C_ACCENT # teal
        elif is_error: dot_color = "#e63946" # red
        
        if dot_color != "transparent":
            # Simple circle via huge corner_radius on a 8x8 frame
            ctk.CTkFrame(hdr, width=8, height=8, corner_radius=10, fg_color=dot_color).pack(side="right")
        
        return c

    def _add_row(self, card: ctk.CTkFrame, label: str, value: str):
        r = ctk.CTkFrame(card, fg_color="transparent", height=32)
        r.pack(fill="x", padx=16, pady=2)
        r.pack_propagate(False)

        ctk.CTkLabel(r, text=label, font=ctk.CTkFont(size=12), text_color=C_ON_SURFACE_VARIANT).pack(side="left")
        
        # Split unit if possible
        parts = value.split(" ")
        num = parts[0]
        unit = " ".join(parts[1:]) if len(parts) > 1 else ""

        if unit:
            ctk.CTkLabel(r, text=f" {unit}", font=ctk.CTkFont(size=10), text_color="#5c6d8a").pack(side="right", pady=(2,0))
            ctk.CTkLabel(r, text=num, font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color=C_ON_SURFACE).pack(side="right")
        else:
            ctk.CTkLabel(r, text=value, font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color=C_ON_SURFACE).pack(side="right")

    def _add_grid_item(self, parent: ctk.CTkFrame, row: int, col: int, label: str, value: str):
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=row, column=col, sticky="nsew", padx=4, pady=8)
        parent.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(cell, text=label, font=ctk.CTkFont(size=11), text_color=C_ON_SURFACE_VARIANT, anchor="w").pack(fill="x")
        
        parts = value.split(" ")
        num = parts[0]
        unit = " ".join(parts[1:]) if len(parts) > 1 else ""
        
        val_frame = ctk.CTkFrame(cell, fg_color="transparent")
        val_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(val_frame, text=num, font=ctk.CTkFont(family="Manrope", size=16, weight="bold"), text_color=C_ON_SURFACE).pack(side="left")
        if unit:
            ctk.CTkLabel(val_frame, text=f" {unit}", font=ctk.CTkFont(size=11), text_color="#5c6d8a").pack(side="left", pady=(4,0))

    def _add_cap_box(self, parent: ctk.CTkFrame, label: str, value: str):
        box = ctk.CTkFrame(parent, fg_color="#070e1a", corner_radius=6)
        box.pack(side="left", fill="x", expand=True, padx=4)

        ctk.CTkLabel(box, text=label, font=ctk.CTkFont(size=10), text_color=C_ON_SURFACE_VARIANT).pack(pady=(6, 0))
        
        parts = value.split(" ")
        num = parts[0]
        unit = " ".join(parts[1:]) if len(parts) > 1 else ""

        val_frame = ctk.CTkFrame(box, fg_color="transparent")
        val_frame.pack(pady=(0, 6))
        ctk.CTkLabel(val_frame, text=num, font=ctk.CTkFont(size=12, weight="bold"), text_color=C_ON_SURFACE).pack(side="left")
        if unit:
            ctk.CTkLabel(val_frame, text=f" {unit}", font=ctk.CTkFont(size=9), text_color="#5c6d8a").pack(side="left", pady=(2,0))
