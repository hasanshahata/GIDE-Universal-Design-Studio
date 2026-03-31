import customtkinter as ctk
from typing import Callable, Dict, Any
from core.utils import parse_eng

C_BASE = "#070e1a"
C_SURFACE_LOW = "#0c1321"
C_SURFACE_HIGH = "#172030"
C_ON_SURFACE = "#e5ebfd"
C_ON_SURFACE_VARIANT = "#8fa3c0"
C_PRIMARY = "#89acff"

class PlotSidebarTab(ctk.CTkFrame):
    """Controls for a single plot slot."""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        # --- Axis Setup ---
        lbl = ctk.CTkLabel(self, text="AXIS DEFINITIONS", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_ON_SURFACE_VARIANT)
        lbl.pack(anchor="w", pady=(10, 8), padx=12)
        
        # X-Axis Dropdown (Expanded)
        ctk.CTkLabel(self, text="X-Axis (Sweep)", font=ctk.CTkFont(size=11), text_color=C_ON_SURFACE).pack(anchor="w", padx=12)
        self.combo_x = ctk.CTkComboBox(
            self, values=["VGS", "GM/ID", "ID/W", "L", "VDS", "VSB"],
            command=self._on_xaxis_changed,
            fg_color=C_SURFACE_HIGH, border_color="#2A3548", button_color=C_SURFACE_HIGH
        )
        self.combo_x.pack(fill="x", padx=12, pady=(2, 12))
        
        # Y-Axis Categorized Options
        ctk.CTkLabel(self, text="Y-Axis (Expression or Parameter)", font=ctk.CTkFont(size=11), text_color=C_ON_SURFACE).pack(anchor="w", padx=12)
        
        # Categorized parameters (Verified against LUT schema)
        self.y_intrinsic = [
            "GM_ID", "GM_GDS", "ID_W", "FT", "VTH", "VDSAT",
            "GM_ID * FT", "CDD / CGG", "Vearly"
        ]
        self.y_extrinsic = [
            "ID", "GM", "GDS", "GMB",
            "CGG", "CGS", "CGD", "CDD", "CSS"
        ]
        y_values = self.y_intrinsic + self.y_extrinsic
        
        self.fld_y = ctk.CTkComboBox(
            self, values=y_values,
            command=self._update_ui_state, # Added command to detect Y axis change
            fg_color=C_SURFACE_HIGH, border_color="#2A3548", button_color=C_SURFACE_HIGH,
            text_color=C_ON_SURFACE
        )
        self.fld_y.set("GM_ID")
        self.fld_y.pack(fill="x", padx=12, pady=(2, 12))
        
        # --- Bias Constants & Strategy ---
        lbl2 = ctk.CTkLabel(self, text="BIAS CONDITIONS & STRATEGY", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_ON_SURFACE_VARIANT)
        lbl2.pack(anchor="w", pady=(16, 8), padx=12)
        
        # Biasing strategy frame (Permanent)
        strat_f = ctk.CTkFrame(self, fg_color="#0c1321", corner_radius=8)
        strat_f.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkLabel(strat_f, text="Characterization Mode", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_ON_SURFACE_VARIANT).pack(anchor="w", padx=10, pady=(6, 2))
        self.combo_strat = ctk.CTkComboBox(
            strat_f, values=["Constant Voltage (VGS)", "Constant gm/ID"],
            height=28, command=self._update_ui_state,
            fg_color=C_SURFACE_HIGH, border_color="#2A3548", button_color=C_SURFACE_HIGH
        )
        self.combo_strat.pack(fill="x", padx=10, pady=(0, 10))

        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="x", padx=12)
        self.inputs = {}
        
        def make_input(row, col, label, default, key):
            f = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
            f.grid(row=row, column=col, sticky="ew", padx=(0 if col==0 else 8, 8 if col==0 else 0), pady=4)
            txt_lbl = ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=11), text_color=C_ON_SURFACE_VARIANT)
            txt_lbl.pack(anchor="w")
            ent = ctk.CTkEntry(f, fg_color=C_SURFACE_HIGH, border_color="#2A3548", height=28, text_color=C_ON_SURFACE, placeholder_text=str(default), placeholder_text_color="#5c6d8a")
            ent.pack(fill="x")
            self.inputs[key] = {"frame": f, "label": txt_lbl, "ent": ent}
            setattr(self, f"ent_{key}", ent)
            
        make_input(0, 0, "Length L (m)", "180n", "L")
        make_input(0, 1, "VDS (V)", "0.9", "VDS")
        make_input(1, 0, "VSB (V)", "0.0", "VSB")
        make_input(1, 1, "Width W (m)", "1.0", "W")
        make_input(2, 0, "Static VGS (V)", "0.6", "VGS")
        make_input(2, 1, "Target gm/ID", "15", "GM_ID")
        
        self.grid_frame.grid_columnconfigure((0, 1), weight=1)


        # --- Parametric Sweep Section ---
        lbl3 = ctk.CTkLabel(self, text="PARAMETRIC SWEEP ENGINE", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_ON_SURFACE_VARIANT)
        lbl3.pack(anchor="w", pady=(24, 8), padx=12)
        
        self.step_enable = ctk.CTkCheckBox(
            self, text="Enable Multi-Curve Sweep", 
            font=ctk.CTkFont(size=11), text_color=C_ON_SURFACE, 
            command=self._update_ui_state,
            fg_color=C_PRIMARY, hover_color=C_PRIMARY
        )
        self.step_enable.pack(anchor="w", padx=12, pady=(0, 10))
        
        self.step_container = ctk.CTkFrame(self, fg_color="#0c1321", corner_radius=12)
        self.step_container.pack(fill="x", padx=12, pady=(0, 12))
        
        # Step Variable
        step_header = ctk.CTkFrame(self.step_container, fg_color="transparent")
        step_header.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(step_header, text="Step Variable", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_ON_SURFACE_VARIANT).pack(side="left")
        
        self.combo_step_var = ctk.CTkComboBox(
            self.step_container, values=["VGS", "L", "VDS", "VSB", "gm/ID", "ID/W"], 
            height=28, command=self._on_stepvar_changed,
            fg_color=C_SURFACE_HIGH, border_color="#2A3548", button_color=C_SURFACE_HIGH
        )
        self.combo_step_var.pack(fill="x", padx=10, pady=(4, 12))
        
        # Unified Values Entry
        ctk.CTkLabel(self.step_container, text="Values (e.g. 1u, 2u, 3u OR 0.4 : 0.2 : 1.0)", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_ON_SURFACE_VARIANT).pack(anchor="w", padx=10)
        self.ent_step_values = ctk.CTkEntry(
            self.step_container, fg_color=C_SURFACE_HIGH, border_color="#2A3548", 
            height=32, font=ctk.CTkFont(size=11, family="Consolas"), 
            text_color=C_ON_SURFACE, placeholder_text="180n, 360n, 540n"
        )
        self.ent_step_values.pack(fill="x", padx=10, pady=(4, 12))

        self._on_xaxis_changed(self.combo_x.get())

    def _on_xaxis_changed(self, choice: str):
        # Update available step variables to exclude the current X-axis
        # Physics-based constraint: VGS, gm/ID, and ID/W are bijectively linked (Inversion Group).
        # Selecting one as X-Axis disqualifies all three from being Step Variables.
        inversion_group = {"VGS", "GM_ID", "ID_W"}
        all_vars = ["VGS", "L", "VDS", "VSB", "gm/ID", "ID/W"]
        
        current_x = choice.upper().replace("/", "_")
        is_in_inversion = current_x in inversion_group
        
        available = []
        for v in all_vars:
            v_norm = v.upper().replace("/", "_")
            if is_in_inversion:
                if v_norm not in inversion_group:
                    available.append(v)
            else:
                if v_norm != current_x:
                    available.append(v)
                    
        old_val = self.combo_step_var.get()
        self.combo_step_var.configure(values=available)
        if old_val in available: self.combo_step_var.set(old_val)
        else: self.combo_step_var.set(available[0])
        self._update_ui_state()

    def _on_stepvar_changed(self, choice: str):
        self._update_ui_state()

    def _update_ui_state(self, *args):
        """Stable UI State Manager. Only disables/gray-outs widgets. No pack_forget."""
        x_axis = self.combo_x.get().upper().replace("/", "_")
        y_axis = self.fld_y.get().upper().replace(" ", "")
        strat = self.combo_strat.get()
        step_active = self.step_enable.get() == 1
        step_var = self.combo_step_var.get().upper().replace("/", "_")

        # Define which constants are relevant based on architecture
        # 1. Reset all to NORMAL
        for key, w_group in self.inputs.items():
            self._set_widget_active(w_group, True)

        # 2. X-axis is always fixed (disabled in constants)
        if x_axis in self.inputs:
            self._set_widget_active(self.inputs[x_axis], False)

        # 3. Y-axis decoupling (Width W only matters for absolute parameters)
        # We detect if expression contains extrinsic fields, but NOT ratios like GM_GDS, GM_ID, etc.
        extrinsic = {"ID", "GM", "GDS", "GMB", "CGG", "CGS", "CGD", "CDD", "CSS", "SFL", "STH"}
        
        # Parse tokens by replacing math symbols with spaces, then check exact matches
        import re
        tokens = re.split(r'[^A-Z0-9_a-z]+', y_axis)
        
        # Check if the Y-axis contains an extrinsic parameter, EXCEPT for standard intrinsic ratios
        intrinsic_ratios = {"GM_ID", "GM_GDS", "ID_W"}
        is_absolute = False
        
        if y_axis not in intrinsic_ratios:
            for token in tokens:
                if token in extrinsic and y_axis != "ID_W":
                    is_absolute = True
                    break
            
        if not is_absolute:
            self._set_widget_active(self.inputs["W"], False)

        # 4. Biasing Strategy Logic & Inversion Mutual Exclusion
        inversion_group = {"VGS", "GM_ID", "ID_W"}
        x_is_inversion = x_axis in inversion_group
        step_is_inversion = step_active and (step_var in inversion_group)

        if x_is_inversion or step_is_inversion:
            # If we are sweeping or stepping an inversion metric, we CANNOT have constant VGS/gmID inputs
            self._set_widget_active(self.inputs["VGS"], False)
            self._set_widget_active(self.inputs["GM_ID"], False)
            self.combo_strat.configure(state="disabled", text_color="#5c6d8a")
        else:
            self.combo_strat.configure(state="normal", text_color=C_ON_SURFACE)
            if strat == "Constant Voltage (VGS)":
                self._set_widget_active(self.inputs["VGS"], True)
                self._set_widget_active(self.inputs["GM_ID"], False)
            else:
                self._set_widget_active(self.inputs["VGS"], False)
                self._set_widget_active(self.inputs["GM_ID"], True)

        # 5. Step Engine logic
        if step_active:
            self.ent_step_values.configure(state="normal", text_color=C_ON_SURFACE)
            self.combo_step_var.configure(state="normal", text_color=C_ON_SURFACE)
            # If a variable is being stepped, it's NOT a constant anymore
            if step_var in self.inputs:
                self._set_widget_active(self.inputs[step_var], False)
        else:
            self.ent_step_values.configure(state="disabled", text_color="#5c6d8a")
            self.combo_step_var.configure(state="disabled", text_color="#5c6d8a")

    def _set_widget_active(self, group, active: bool):
        st = "normal" if active else "disabled"
        clr = C_ON_SURFACE if active else "#5c6d8a"
        group["label"].configure(text_color=clr)
        group["ent"].configure(state=st, text_color=clr)

    def get_params(self) -> Dict[str, Any]:
        """Collect params with List-Based step parsing."""
        from core.utils import parse_eng_list
        
        # Determine strategy
        strat = self.combo_strat.get()
        use_gmid = (strat == "Constant gm/ID")
        
        constants = {}
        for k, group in self.inputs.items():
            if group["ent"].cget("state") == "normal":
                constants[k] = parse_eng(group["ent"].get())
        
        # Inject biasing strategy marker for backend
        constants["_BIAS_MODE"] = "GM_ID" if use_gmid else "VGS"
        
        params = {
            "x_axis": self.combo_x.get(),
            "y_axis": self.fld_y.get().strip(),
            "constants": constants,
            "step_config": {
                "enabled": self.step_enable.get() == 1,
                "var": self.combo_step_var.get(),
                "values": parse_eng_list(self.ent_step_values.get())
            }
        }
        return params


class PanelPlotSidebar(ctk.CTkFrame):
    """The master sidebar managing tabs for Plots 1A-1B with a sticky action footer."""
    def __init__(self, master, plot_action_cb: Callable, clear_action_cb: Callable, **kwargs):
        super().__init__(master, **kwargs)
        self.plot_action_cb = plot_action_cb
        self.clear_action_cb = clear_action_cb
        
        # 1. Main Content Area (Scrollable)
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", 
            scrollbar_button_color=C_SURFACE_HIGH
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.tabview = ctk.CTkTabview(
            self.scroll_frame, fg_color="transparent", segmented_button_fg_color=C_BASE,
            segmented_button_selected_color=C_SURFACE_HIGH, segmented_button_unselected_color=C_BASE,
            text_color="#8fa3c0"
        )
        self.tabview.pack(fill="both", expand=True, padx=4, pady=4)
        
        self.tabs = {}
        for slot in ["Graph-1", "Graph-2"]:
            t = self.tabview.add(slot)
            t_content = PlotSidebarTab(t)
            t_content.pack(fill="both", expand=True)
            self.tabs[slot] = t_content
            
        # 2. Sticky Footer (Action Buttons)
        footer = ctk.CTkFrame(self, fg_color="#0c1321", corner_radius=0, height=80)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False) # Maintain fixed height
        
        btn_grid = ctk.CTkFrame(footer, fg_color="transparent")
        btn_grid.pack(expand=True)
        
        # PLOT
        self.btn_plot = ctk.CTkButton(
            btn_grid, text="PLOT", font=ctk.CTkFont(size=12, weight="bold"), 
            width=100, height=36,
            command=lambda: self._handle_action(append=False)
        )
        self.btn_plot.pack(side="left", padx=5)
        
        # APPEND
        self.btn_append = ctk.CTkButton(
            btn_grid, text="APPEND", font=ctk.CTkFont(size=12), 
            width=100, height=36, fg_color=C_SURFACE_HIGH, 
            border_color="#2A3548", border_width=1, hover_color="#2A3548",
            command=lambda: self._handle_action(append=True)
        )
        self.btn_append.pack(side="left", padx=5)
        
        # CLEAR
        self.btn_clear = ctk.CTkButton(
            btn_grid, text="CLEAR", font=ctk.CTkFont(size=12), 
            width=80, height=36, fg_color="#4a2525", hover_color="#ff5555",
            command=lambda: self._handle_clear()
        )
        self.btn_clear.pack(side="left", padx=5)

    def _get_active_slot(self) -> str:
        return self.tabview.get()

    def _handle_action(self, append: bool):
        slot = self._get_active_slot()
        self.plot_action_cb(slot, append)

    def _handle_clear(self):
        slot = self._get_active_slot()
        self.clear_action_cb(slot)

    def get_slot_params(self, slot: str) -> Dict[str, Any]:
        return self.tabs[slot].get_params()
