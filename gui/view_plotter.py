import customtkinter as ctk
from typing import Callable, Optional
from core.data_loader import LUTData

C_BASE = "#070e1a"
C_SURFACE_LOW = "#0c1321" 
C_SURFACE_HIGH = "#172030"
C_PRIMARY = "#89acff"
C_ACCENT = "#68fadd"
C_ON_SURFACE = "#e5ebfd"

class ViewPlotter(ctk.CTkFrame):
    """
    Main container for the Advanced Analog Plotter.
    Contains the left 2x2 plotting grid and the right settings sidebar.
    """
    def __init__(self, master, get_data_cb: Callable[[], Optional[LUTData]], **kwargs):
        super().__init__(master, **kwargs)
        self.get_data = get_data_cb
        
        # Custom browser-style tab bar
        self.tab_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_bar.pack(fill="x", padx=24, pady=(12, 0))
        
        ctk.CTkLabel(
            self.tab_bar, text="Figures", 
            font=ctk.CTkFont(family="Manrope", size=15, weight="bold"),
            text_color="#8fa3c0"
        ).pack(side="left", padx=(0, 12))
        
        self.tabs_container = ctk.CTkFrame(self.tab_bar, fg_color="transparent")
        self.tabs_container.pack(side="left")
        
        self.add_btn = ctk.CTkButton(
            self.tab_bar, text="+", width=32, height=32, 
            corner_radius=16, fg_color=C_SURFACE_HIGH, 
            hover_color=C_SURFACE_LOW, text_color=C_PRIMARY,
            font=ctk.CTkFont(size=20),
            command=self._add_new_figure
        )
        self.add_btn.pack(side="left", padx=8)

        # Main content area where figure frames are swapped
        self.figure_area = ctk.CTkFrame(self, fg_color="transparent")
        self.figure_area.pack(fill="both", expand=True, padx=24, pady=(8, 24))
        
        self.figures = [] # List of {"name": str, "btn": Button, "frame": Frame, "grid": Grid, "sidebar": Sidebar}
        self.active_fig = None
        
        self._add_new_figure()
        
    def _add_new_figure(self):
        num = len(self.figures) + 1
        name = f"Figure {num}"
        
        # 1. Create the Tab Button + Close Button Container
        tab_item = ctk.CTkFrame(self.tabs_container, fg_color="transparent")
        tab_item.pack(side="left", padx=4)
        
        btn = ctk.CTkButton(
            tab_item, text=name, 
            width=100, height=32, corner_radius=8,
            fg_color=C_BASE, text_color="#8fa3c0",
            hover_color=C_SURFACE_LOW,
            command=lambda n=name: self._select_figure(n)
        )
        btn.pack(side="left")
        
        close_btn = ctk.CTkButton(
            tab_item, text="x", width=20, height=20, corner_radius=10,
            fg_color="transparent", text_color="#5c6d8a",
            hover_color="#4a2525", font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda n=name: self._close_figure(n)
        )
        close_btn.pack(side="left", padx=(2, 0))
        
        # 2. Create the Figure Frame (hidden by default)
        fig_frame = ctk.CTkFrame(self.figure_area, fg_color="transparent")
        
        # Layout: Left = Plot Grid, Right = Sidebar
        grid_frame = ctk.CTkFrame(fig_frame, fg_color="transparent")
        grid_frame.pack(side="left", fill="both", expand=True)
        
        sidebar_frame = ctk.CTkFrame(fig_frame, width=340, fg_color=C_SURFACE_LOW, corner_radius=12)
        sidebar_frame.pack(side="right", fill="y", padx=(16, 0))
        sidebar_frame.pack_propagate(False)
        
        from .panel_plot_grid import PanelPlotGrid
        from .panel_plot_sidebar import PanelPlotSidebar
        
        plot_grid = PanelPlotGrid(grid_frame, fg_color="transparent")
        plot_grid.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Closure helper to ensure plot actions target the correct grid
        def run_plot(slot_id, append):
            self._handle_plot_in_fig(plot_grid, plot_sidebar, slot_id, append)

        def run_clear(slot_id):
            slot = plot_grid.get_slot(slot_id)
            if slot: slot.clear_plot()

        plot_sidebar = PanelPlotSidebar(
            sidebar_frame, fg_color="transparent",
            plot_action_cb=run_plot,
            clear_action_cb=run_clear
        )
        plot_sidebar.pack(fill="both", expand=True)

        fig_obj = {
            "name": name,
            "btn": btn,
            "frame": fig_frame,
            "grid": plot_grid,
            "sidebar": plot_sidebar,
            "container": tab_item
        }
        self.figures.append(fig_obj)
        self._select_figure(name)

    def _close_figure(self, name: str):
        # 1. Find the figure
        target_fig = None
        for fig in self.figures:
            if fig["name"] == name:
                target_fig = fig
                break
        
        if not target_fig: return
        
        # 2. Prevent closing the last figure if you want to keep at least one
        # if len(self.figures) <= 1: return 
        
        # 3. Destroy widgets
        target_fig["frame"].destroy()
        target_fig["container"].destroy()
        
        # 4. Remove from list
        self.figures.remove(target_fig)
        
        # 5. Select another figure if any left
        if self.figures:
            self._select_figure(self.figures[-1]["name"])
        else:
            self.active_fig = None
            self._add_new_figure() # Keep at least one figure open

    def _select_figure(self, name: str):
        # Update UI state
        for fig in self.figures:
            f_frame = fig["frame"]
            f_btn = fig["btn"]
            if fig["name"] == name:
                f_btn.configure(fg_color=C_SURFACE_HIGH, text_color=C_PRIMARY)
                f_frame.pack(fill="both", expand=True)
                self.active_fig = fig
            else:
                f_btn.configure(fg_color=C_BASE, text_color="#8fa3c0")
                f_frame.pack_forget()

    def _handle_plot_in_fig(self, grid, sidebar, slot_id, append):
        import numpy as np
        slot = grid.get_slot(slot_id)
        if not slot: return
        
        data = self.get_data()
        if data is None: 
            slot.title_lbl.configure(text=f"Plot Error: No LUT Data Loaded!")
            return
            
        params = sidebar.get_slot_params(slot_id)
        x_axis, y_axis = params["x_axis"], params["y_axis"]
        constants = params["constants"]
        step_cfg = params.get("step_config", {"enabled": False})
        
        # --- Width Validation ---
        absolute_params = {
            "ID", "GM", "GDS", "GMB", "CGG", "CGS", "CGD", 
            "CDD", "CSS", "CDB", "CSB", "SFL", "STH"
        }
        from core.plot_engine import _extract_variables
        needed = _extract_variables(y_axis.upper().replace("/", "_"))
        is_absolute = any(v.upper() in absolute_params for v in needed)
        
        w_val = constants.get("W", 0.0)
        if is_absolute and (w_val is None or w_val <= 0):
            slot.title_lbl.configure(text=f"Plot Error: Width (W) must be specified for absolute parameters!")
            return
            
        from core.plot_engine import generate_plot_data
        try:
            if step_cfg["enabled"]:
                # --- Parametric Step Engine (Discrete List) ---
                step_var = step_cfg["var"]
                step_values = step_cfg["values"]
                
                if not step_values:
                    slot.title_lbl.configure(text=f"Plot Error: No valid step values found!")
                    return

                # Clear if not appending
                if not append: slot.clear_plot()
                
                for i, val in enumerate(step_values):
                    current_constants = constants.copy()
                    # Mapping logic for gm/ID
                    skey = step_var.upper().replace("/", "_")
                    current_constants[skey] = val
                    
                    x_vec, y_vec = generate_plot_data(data, x_axis, y_axis, current_constants)
                    
                    # Custom Label for Steps
                    from core.utils import eng
                    label = f"{step_var}={eng(val)}"
                    slot.plot_data(x_vec, y_vec, label=label, append=True, is_pmos=data.is_pmos)
                
                title = f"Plot {slot_id}: {y_axis} vs {x_axis} (Step: {step_var})"
                slot.set_labels(x_label=x_axis, y_label=y_axis, title=title)
            else:
                # --- Single Curve Plot ---
                x_vec, y_vec = generate_plot_data(data, x_axis, y_axis, constants)
                slot.plot_data(x_vec, y_vec, label=y_axis, append=append, is_pmos=data.is_pmos)
                
                title = f"Plot {slot_id}: {y_axis} vs {x_axis}"
                slot.set_labels(x_label=x_axis, y_label=y_axis, title=title)
        except Exception as e:
            slot.title_lbl.configure(text=f"Plot Error: {str(e)}")
            import traceback
            traceback.print_exc()


