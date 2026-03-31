"""
Main application window — orchestrates the 4-column "Precision Observer" layout.
Integrated GIDE V3: Characterize -> Size -> Plot
"""

from __future__ import annotations
import customtkinter as ctk
import os

from core import sizing_engine as se
from core.utils import eng, resource_path
from .panel_setup import PanelSetup
from .panel_sizing import PanelSizing
from .panel_results import PanelResults
from .view_lut_gen import LUTGeneratorView
from .view_plotter import ViewPlotter
from PIL import Image

# --- Precision Observer Tonal Palette ---
C_BASE = "#070e1a"        # Deep void background
C_SURFACE_LOW = "#0c1321" # Sidebar / secondary panels
C_SURFACE_HIGH = "#172030" # Main cards
C_ON_SURFACE = "#e5ebfd"  # Primary text
C_PRIMARY = "#89acff"     # Primary brand / CTA
C_ACCENT = "#68fadd"      # Teal success


class App(ctk.CTk):
    """GIDE V3 — Unified gm/ID Design Suite."""

    def __init__(self):
        super().__init__()

        # ── Window configuration ──────────────────────────────────────
        self.title("Unified Design Studio - Modernized Sizing & Characterization")
        self.geometry("1440x950")
        self.minsize(1280, 850)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        ctk.set_appearance_mode("dark")
        self.configure(fg_color=C_BASE)

        # ── Universal Scaling ─────────────────────────────────────────
        # Increase scaling slightly for Linux/X11 for better clarity
        if os.name == "posix":
            ctk.set_widget_scaling(1.15)
            ctk.set_window_scaling(1.15)
        else:
            ctk.set_widget_scaling(1.0)
            ctk.set_window_scaling(1.0)

        # ── Global Fonts (Cross-Platform Stack) ───────────────────────
        # Priority: Confirmed Linux fonts -> Standard Fallbacks
        font_family = ("Liberation Sans", "DejaVu Sans", "Arial", "sans-serif")

        self.font_h1 = ctk.CTkFont(family=font_family, size=20, weight="bold")
        self.font_label = ctk.CTkFont(family=font_family, size=11)

        # ── Header bar ────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=C_BASE, corner_radius=0)
        header.pack(fill="x", side="top")
        header.pack_propagate(True)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(expand=True, pady=4) # Tight padding

        # Load Logo Image
        # Load Logo Image via resource_path (PyInstaller compatible)
        logo_relative = os.path.join("gui", "assets", "logo.png")
        logo_path = resource_path(logo_relative)
        
        try:
            # Load and scale the logo
            logo_img_pil = Image.open(logo_path)
            # Procedural logo size is exactly (350, 125)
            logo_img = ctk.CTkImage(light_image=logo_img_pil, dark_image=logo_img_pil, size=(350, 145))
            
            self.logo_label = ctk.CTkLabel(title_frame, image=logo_img, text="")
            self.logo_label.pack(pady=2)
        except Exception as e:
            print(f"Could not load logo: {e}")
            # Fallback to text if image fails
            ctk.CTkLabel(
                title_frame, text="GIDE",
                font=ctk.CTkFont(family="Georgia", size=32, weight="bold", slant="italic"),
                text_color="#e5ebfd",
            ).pack()

        # ── Main content area ─────────────────────────────────────────
        content = ctk.CTkFrame(self, fg_color=C_BASE, corner_radius=0)
        content.pack(fill="both", expand=True, padx=0, pady=0)

        # 1. Main Nav (Sidebar)
        # --------------------------------------------------------------
        self.main_nav = ctk.CTkFrame(content, width=220, fg_color=C_BASE, corner_radius=0)
        self.main_nav.pack(side="left", fill="y", padx=0)
        self.main_nav.pack_propagate(False)

        # Global State Variables
        self.data_nmos = None
        self.data_pmos = None
        self.active_device = "nmos"

        self.lut_mgmt_container = ctk.CTkFrame(self.main_nav, fg_color="transparent")
        self.lut_mgmt_container.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            self.lut_mgmt_container, text="LOAD LUT DATA",
            font=ctk.CTkFont(family="Manrope", size=11, weight="bold"),
            text_color="#5c6d8a"
        ).pack(fill="x", padx=24, pady=(24, 8))

        btn_load_frame = ctk.CTkFrame(self.lut_mgmt_container, fg_color="transparent")
        btn_load_frame.pack(fill="x", padx=24, pady=(0, 16))
        
        self.btn_load_n = ctk.CTkButton(
            btn_load_frame, text="Load NMOS Data",
            height=32, font=ctk.CTkFont(size=11), fg_color="transparent",
            border_color="#2A3548", border_width=1, hover_color="#172030", text_color="#8fa3c0",
            command=lambda: self._load_file("nmos")
        )
        self.btn_load_n.pack(fill="x", pady=(0, 4))
        
        self.btn_load_p = ctk.CTkButton(
            btn_load_frame, text="Load PMOS Data",
            height=32, font=ctk.CTkFont(size=11), fg_color="transparent",
            border_color="#2A3548", border_width=1, hover_color="#172030", text_color="#8fa3c0",
            command=lambda: self._load_file("pmos")
        )
        self.btn_load_p.pack(fill="x")

        # Sidebar: Device Type
        ctk.CTkLabel(self.lut_mgmt_container, text="DEVICE TYPE", font=ctk.CTkFont(family="Inter", size=10, weight="bold"), text_color="#8fa3c0", anchor="w").pack(fill="x", padx=24, pady=(0, 8))
        toggle_frame = ctk.CTkFrame(self.lut_mgmt_container, height=36, fg_color="#0c1321", corner_radius=6)
        toggle_frame.pack(fill="x", padx=24, pady=(0, 32))
        toggle_frame.pack_propagate(False)

        self.btn_nmos = ctk.CTkButton(toggle_frame, text="NMOS", width=0, fg_color=C_PRIMARY, text_color=C_BASE, corner_radius=4, hover=False, command=lambda: self._set_device("nmos"))
        self.btn_nmos.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        self.btn_pmos = ctk.CTkButton(toggle_frame, text="PMOS", width=0, fg_color="transparent", text_color="#5c6d8a", corner_radius=4, hover_color="#172030", command=lambda: self._set_device("pmos"))
        self.btn_pmos.pack(side="left", fill="both", expand=True, padx=2, pady=2)

        # Sidebar: Navigation
        self.lbl_workflow = ctk.CTkLabel(self.main_nav, text="WORKFLOW", font=ctk.CTkFont(family="Inter", size=10, weight="bold"), text_color="#8fa3c0", anchor="w")
        self.lbl_workflow.pack(fill="x", padx=24, pady=(0, 8))
        self.nav_items_frames = {}
        nav_items = [
            ("LUTs Generation", True),
            ("Sizing Dashboard", False),
            ("Plotter", False)
        ]
        
        self.view_containers = {}
        for name, active in nav_items:
            bg = C_SURFACE_HIGH if active else "transparent"
            text_col = C_PRIMARY if active else "#8fa3c0"
            f = ctk.CTkFrame(self.main_nav, fg_color=bg, height=40, corner_radius=6)
            f.pack(fill="x", padx=12, pady=4)
            f.pack_propagate(False)
            
            btn = ctk.CTkButton(f, text=f"   {name}", fg_color="transparent", hover_color="#1a2536", anchor="w",
                                font=ctk.CTkFont(size=13, weight="bold" if active else "normal"), 
                                text_color=text_col, command=lambda n=name: self._switch_view(n))
            btn.pack(fill="both", expand=True)
            self.nav_items_frames[name] = {"frame": f, "btn": btn}

        # --- View Containers ---
        self.content_area = ctk.CTkFrame(content, fg_color="transparent", corner_radius=0)
        self.content_area.pack(side="left", fill="both", expand=True)
        
        # 1. LUT Generation View
        self.view_lut = LUTGeneratorView(self.content_area, fg_color="transparent")
        
        # 2. Sizing Dashboard View
        self.view_sizing = ctk.CTkFrame(self.content_area, fg_color="transparent")
        
        # Build Sizing Dashboard content
        setup_container = ctk.CTkFrame(self.view_sizing, width=280, fg_color="transparent", corner_radius=0)
        setup_container.pack(side="left", fill="y", padx=(12, 12), pady=(0, 24))
        setup_container.pack_propagate(False)
        self.panel_setup = PanelSetup(setup_container, fg_color=C_SURFACE_HIGH, corner_radius=12)
        self.panel_setup.pack(fill="both", expand=True)

        results_container = ctk.CTkFrame(self.view_sizing, width=360, fg_color="transparent", corner_radius=0)
        results_container.pack(side="right", fill="y", padx=(12, 24), pady=(0, 24))
        results_container.pack_propagate(False)
        self.panel_results = PanelResults(results_container, fg_color="transparent", corner_radius=0)
        self.panel_results.pack(fill="both", expand=True)

        sizing_container = ctk.CTkFrame(self.view_sizing, fg_color="transparent", corner_radius=0)
        sizing_container.pack(side="left", fill="both", expand=True, padx=12, pady=(0, 24))
        self.panel_sizing = PanelSizing(
            sizing_container, 
            on_calculate=self._on_calculate,
            fg_color=C_SURFACE_LOW, 
            corner_radius=16
        )
        self.panel_sizing.pack(fill="both", expand=True)
        
        # 3. Plotter View
        self.view_plotter = ViewPlotter(self.content_area, get_data_cb=self.get_active_data, fg_color="transparent")
        
        self.view_containers["LUTs Generation"] = self.view_lut
        self.view_containers["Sizing Dashboard"] = self.view_sizing
        self.view_containers["Plotter"] = self.view_plotter

        # Show initial view
        self._switch_view("LUTs Generation")

        # Footer Credit
        ctk.CTkLabel(self.main_nav, text="Author: Hassan Shehata", font=ctk.CTkFont(family="Manrope", size=10), text_color="#5c6d8a").pack(side="bottom", pady=16)

    def _switch_view(self, view_name: str):
        # Update Nav Styles
        for name, dct in self.nav_items_frames.items():
            if name == view_name:
                dct["frame"].configure(fg_color=C_SURFACE_HIGH)
                dct["btn"].configure(text_color=C_PRIMARY, font=ctk.CTkFont(size=13, weight="bold"))
            else:
                dct["frame"].configure(fg_color="transparent")
                dct["btn"].configure(text_color="#8fa3c0", font=ctk.CTkFont(size=13, weight="normal"))
                
        # Swap Content
        for name, container in self.view_containers.items():
            if name == view_name:
                container.pack(fill="both", expand=True)
            else:
                container.pack_forget()

        # Toggle Sidebar LUT Management visibility
        if view_name == "LUTs Generation":
            self.lut_mgmt_container.pack_forget()
        else:
            # Re-pack it before the WORKFLOW label
            self.lut_mgmt_container.pack(fill="x", before=self.lbl_workflow)

    def _set_device(self, dev: str):
        self.active_device = dev
        if dev == "nmos":
            self.btn_nmos.configure(fg_color=C_PRIMARY, text_color=C_BASE)
            self.btn_pmos.configure(fg_color="transparent", text_color="#5c6d8a")
        else:
            self.btn_pmos.configure(fg_color="#ff5555", text_color="#ffffff")
            self.btn_nmos.configure(fg_color="transparent", text_color="#5c6d8a")
        
        # Update tech info summary in sidebar
        if hasattr(self, "panel_setup"):
            self.panel_setup.update_tech_info(self.get_active_data())

    def _load_file(self, device: str):
        from core.data_loader import load_lut
        path = ctk.filedialog.askopenfilename(
            title=f"Select {device.upper()} Data file",
            filetypes=[("Pickle Files", "*.pkl")]
        )
        if not path: return
        try:
            data = load_lut(path, is_pmos=(device == "pmos"))
            if device == "nmos":
                self.data_nmos = data
                self.btn_load_n.configure(border_color=C_PRIMARY, text_color="#e5ebfd")
            else:
                self.data_pmos = data
                self.btn_load_p.configure(border_color="#ff5555", text_color="#e5ebfd")
            self._set_device(device)
            if hasattr(self, "panel_setup"):
                self.panel_setup.status_lbl.configure(text="High Precision Active", text_color=C_ACCENT)
                self.panel_setup.update_tech_info(data) # Ensure tech summary is fresh
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            if hasattr(self, "panel_setup"):
                self.panel_setup.status_lbl.configure(text="Load Failed", text_color="#ff8866")
            from tkinter import messagebox
            messagebox.showerror("Load Error", f"Exception: {e}\n\n{err_msg}")
            print(f"Load error: {e}")

    def get_active_data(self):
        return self.data_nmos if self.active_device == "nmos" else self.data_pmos

    def _on_calculate(self, mode_name: str, params: dict):
        data = self.get_active_data()
        if data is None:
            self.panel_results.show_error("Load a .pkl file first!")
            return
        
        VDS = self.panel_setup.get_VDS()
        VSB = self.panel_setup.get_VSB()
        device_name = self.active_device.upper()
        try:
            univ_params = params.get("universal", {})
            if not univ_params:
                self.panel_results.show_error("Invalid Universal Parameters")
                return

            op = se.size_universal(data, VDS=VDS, VSB=VSB, **univ_params)
            if op.ok:
                self.panel_results.show_result(op, device_name)
                self.panel_sizing.show_prediction(op.W)
            else:
                self.panel_results.show_error(op.msg)
                self.panel_sizing.clear_prediction()
        except Exception as e: self.panel_results.show_error(str(e))
        
    def _on_closing(self):
        """Intercepts the window close event to ensure a clean process kill."""
        # Force terminate any remaining active threads/timers/subprocesses
        if hasattr(self, 'view_lut') and self.view_lut.is_running:
            if self.view_lut.process:
                self.view_lut.process.terminate()
        
        # Destroy main loops
        self.quit()
        self.destroy()
        
        # Hard kill the OS process to prevent Task Manager ghosting
        import os
        os._exit(0)

