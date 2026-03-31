import customtkinter as ctk
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from typing import List
from tkinter import Menu

# Configure matplotlib for dark theme "Precision Observer"
matplotlib.use("TkAgg")

C_BASE = "#070e1a"
C_SURFACE_LOW = "#0c1321"
C_SURFACE_HIGH = "#172030"
C_ON_SURFACE = "#e5ebfd"
C_ON_SURFACE_VARIANT = "#8fa3c0"
C_PRIMARY = "#89acff"

plt.rcParams.update({
    "lines.color": C_ON_SURFACE,
    "patch.edgecolor": C_ON_SURFACE,
    "text.color": C_ON_SURFACE,
    "axes.facecolor": C_SURFACE_LOW,
    "axes.edgecolor": "#2A3548",
    "axes.labelcolor": C_ON_SURFACE_VARIANT,
    "xtick.color": C_ON_SURFACE_VARIANT,
    "ytick.color": C_ON_SURFACE_VARIANT,
    "grid.color": "#2A3548",
    "figure.facecolor": "none",
    "figure.edgecolor": "none",
    "savefig.facecolor": C_SURFACE_LOW,
    "savefig.edgecolor": C_SURFACE_LOW,
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial", "sans-serif"],
    "axes.spines.top": False,
    "axes.spines.right": False,
})

COLD_PALETTE = [
    "#68fadd", "#89acff", "#a78bfa", "#3b82f6", "#2dd4bf", 
    "#4ade80", "#22d3ee", "#6366f1", "#a855f7", "#ec4899",
    "#0ea5e9", "#14b8a6", "#c084fc", "#818cf8", "#38bdf8",
    "#34d399", "#5eead4", "#7dd3fc", "#93c5fd", "#c4b5fd"
]
WARM_PALETTE = [
    "#ff5555", "#ff9e64", "#facc15", "#f471b5", "#fb7185",
    "#fb923c", "#fcd34d", "#fca5a5", "#fda4af", "#f43f5e",
    "#ea580c", "#d97706", "#be123c", "#9f1239", "#881337",
    "#fb7185", "#f472b6", "#fb923c", "#fde047", "#f87171"
]


TRACE_COLORS = COLD_PALETTE # Default

class PlotPopup(ctk.CTkToplevel):
    """A pop-out window for inspecting a plot at full scale."""
    def __init__(self, master, slot_id, title, x_data_list, y_data_list, labels, colors, interactor_state, x_label, y_label, is_log_x=False, is_log_y=False):
        super().__init__(master)
        self.title(f"GIDE Plot Detail: {title}")
        self.geometry("900x700")
        self.after(200, lambda: self.focus_force())
        
        # Controls Frame
        ctrl = ctk.CTkFrame(self, height=48, fg_color=C_SURFACE_LOW)
        ctrl.pack(fill="x", side="top")
        
        ctk.CTkLabel(ctrl, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=16)
        
        btn_save = ctk.CTkButton(
            ctrl, text="SAVE IMAGE", width=120, height=32, fg_color=C_PRIMARY, text_color=C_BASE,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_plot
        )
        btn_save.pack(side="right", padx=12, pady=8)
        
        # New Figure (Increase DPI for Linux clarity)
        self.fig, self.ax = plt.subplots(figsize=(8, 6), dpi=120)
        self.fig.patch.set_facecolor(C_SURFACE_LOW)
        self.ax.set_facecolor(C_SURFACE_LOW)
        
        self.ax.set_xlabel(x_label, color=C_ON_SURFACE_VARIANT)
        self.ax.set_ylabel(y_label, color=C_ON_SURFACE_VARIANT)
        
        if is_log_x: self.ax.set_xscale("log")
        else: self.ax.set_xscale("linear")
        if is_log_y: self.ax.set_yscale("log")
        else: self.ax.set_yscale("linear")
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)
        
        # Enable Interactivity
        self.traces = []
        for i, (x, y) in enumerate(zip(x_data_list, y_data_list)):
            color = colors[i] if i < len(colors) else COLD_PALETTE[i % len(COLD_PALETTE)]
            line, = self.ax.plot(x, y, color=color, label=labels[i] if i < len(labels) else "", linewidth=2)
            self.traces.append(line)
            
        from .plot_interactions import PlotInteractor
        self.interactor = PlotInteractor(self.ax, self.canvas, self)
        
        # Restore cursors and taps
        if interactor_state:
            self.interactor.restore_state(interactor_state)
            
        # Draw legend
        if self.traces:
            self.ax.legend(
                loc="upper right", 
                frameon=False, 
                labelcolor="#8fa3c0", 
                fontsize=10
            )
        
        # Interactive Toolbar
        toolbar_frame = ctk.CTkFrame(self, height=40, fg_color=C_SURFACE_LOW)
        toolbar_frame.pack(fill="x", side="bottom")
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side="left", padx=10)
        
        self._format_axes()
        self.canvas.draw()

    def _save_plot(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("PDF Document", "*.pdf"), ("SVG Graphics", "*.svg")]
        )
        if path:
            self.canvas.draw() # Ensure everything is rendered before saving
            self.fig.savefig(path, dpi=300, bbox_inches="tight")

    def _format_axes(self):
        self.ax.set_facecolor(C_SURFACE_LOW)
        self.fig.patch.set_facecolor(C_SURFACE_LOW)
        self.ax.tick_params(colors=C_ON_SURFACE_VARIANT)
        for spine in self.ax.spines.values():
            spine.set_edgecolor("#2A3548")
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.xaxis.label.set_color(C_ON_SURFACE_VARIANT)
        self.ax.yaxis.label.set_color(C_ON_SURFACE_VARIANT)
        self.ax.grid(True, linestyle="--", alpha=0.5, color="#2A3548")
        
        self.ax.yaxis.get_offset_text().set_color(C_ON_SURFACE_VARIANT)
        self.ax.xaxis.get_offset_text().set_color(C_ON_SURFACE_VARIANT)
        
        for axis, scale in zip([self.ax.xaxis, self.ax.yaxis], [self.ax.get_xscale(), self.ax.get_yscale()]):
            if scale == "log":
                axis.set_major_formatter(ticker.LogFormatterSciNotation())
                axis.set_major_locator(ticker.LogLocator(base=10.0, numticks=10))
            else:
                axis.set_major_formatter(ticker.EngFormatter())
                axis.set_major_locator(ticker.MaxNLocator(nbins=6))

class PlotSlot(ctk.CTkFrame):
    """A single graph container inside the 2x2 grid."""
    def __init__(self, master, slot_id: str, title: str, **kwargs):
        super().__init__(master, fg_color=C_SURFACE_LOW, corner_radius=12, border_width=1, border_color="#2A3548", **kwargs)
        self.slot_id = slot_id
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 0))
        
        self.title_lbl = ctk.CTkLabel(
            header, text=title, font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C_ON_SURFACE, anchor="w"
        )
        self.title_lbl.pack(side="left", fill="x", expand=True)
        
        self.btn_maximize = ctk.CTkButton(
            header, text="⛶", width=28, height=28, 
            fg_color=C_SURFACE_HIGH, hover_color="#2A3548", corner_radius=6,
            command=self._on_maximize
        )
        self.btn_maximize.pack(side="right")
        
        # Matplotlib Figure (Increase DPI for Linux clarity)
        self.fig, self.ax = plt.subplots(figsize=(4, 3), dpi=115)
        self.fig.patch.set_alpha(0.0) # Transparent background to match frame
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.configure(bg=C_SURFACE_LOW, highlightthickness=0)
        self.canvas_widget.pack(fill="both", expand=True, padx=8, pady=8)
        
        self.traces = []  # Store references to line objects
        
        # Initial empty state plotting config
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.ax.set_xlabel("X-Axis")
        self.ax.set_ylabel("Y-Axis")
        
        from .plot_interactions import PlotInteractor
        self.interactor = PlotInteractor(self.ax, self.canvas, self)
        
        self._format_axes()
        self.canvas.draw()
        
    def _format_axes(self):
        self.ax.set_facecolor(C_SURFACE_LOW)
        self.fig.patch.set_facecolor(C_SURFACE_LOW)
        self.ax.tick_params(colors=C_ON_SURFACE_VARIANT)
        for spine in self.ax.spines.values():
            spine.set_edgecolor("#2A3548")
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.xaxis.label.set_color(C_ON_SURFACE_VARIANT)
        self.ax.yaxis.label.set_color(C_ON_SURFACE_VARIANT)
        self.ax.grid(True, linestyle="--", alpha=0.5, color="#2A3548")
        
        self.ax.yaxis.get_offset_text().set_color(C_ON_SURFACE_VARIANT)
        self.ax.xaxis.get_offset_text().set_color(C_ON_SURFACE_VARIANT)
        
        for axis, scale in zip([self.ax.xaxis, self.ax.yaxis], [self.ax.get_xscale(), self.ax.get_yscale()]):
            if scale == "log":
                axis.set_major_formatter(ticker.LogFormatterSciNotation())
                axis.set_major_locator(ticker.LogLocator(base=10.0, numticks=10))
            else:
                axis.set_major_formatter(ticker.EngFormatter())
                axis.set_major_locator(ticker.MaxNLocator(nbins=6))

    def _on_maximize(self):
        # Collect all trace data for the popup
        x_data_list = [line.get_xdata() for line in self.traces]
        y_data_list = [line.get_ydata() for line in self.traces]
        labels = [line.get_label() for line in self.traces]
        colors = [line.get_color() for line in self.traces]
        
        inter_state = None
        if hasattr(self, 'interactor') and self.interactor:
            inter_state = self.interactor.get_state()
        
        PlotPopup(
            self, self.slot_id, self.title_lbl.cget("text"),
            x_data_list, y_data_list, labels, colors, inter_state,
            self.ax.get_xlabel(), self.ax.get_ylabel(),
            is_log_x=(self.ax.get_xscale() == "log"),
            is_log_y=(self.ax.get_yscale() == "log")
        )

    def plot_data(self, x, y, label: str, append: bool = False, is_pmos: bool = False):
        if not append:
            self.ax.clear()
            self.traces = []
            if self.interactor:
                self.interactor.clear_cursors()
            self._format_axes()
            
        palette = WARM_PALETTE if is_pmos else COLD_PALETTE
        color = palette[len(self.traces) % len(palette)]
        line, = self.ax.plot(x, y, color=color, label=label, linewidth=1.5)
        self.traces.append(line)
        
        if label:
            self.ax.legend(frameon=False, loc="best", labelcolor=C_ON_SURFACE_VARIANT)
            
        self._format_axes()
        self.canvas.draw()
        if self.interactor:
            self.interactor.refresh_all_labels()

    def set_labels(self, x_label: str, y_label: str, title: str = ""):
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        if title:
            self.title_lbl.configure(text=title)
        self.canvas.draw()

    def clear_plot(self):
        self.ax.clear()
        self.traces = []
        if self.interactor:
            self.interactor.clear_cursors()
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.ax.set_xlabel("X-Axis")
        self.ax.set_ylabel("Y-Axis")
        self.title_lbl.configure(text=f"{self.slot_id}: (Empty)")
        self.canvas.draw()

class PanelPlotGrid(ctk.CTkFrame):
    """A 2x2 grid holding 4 PlotSlots."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)
        
        self.slots = {}
        
        self.slots["Graph-1"] = PlotSlot(self, slot_id="Graph-1", title="Graph-1: (Empty)")
        self.slots["Graph-1"].grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        
        self.slots["Graph-2"] = PlotSlot(self, slot_id="Graph-2", title="Graph-2: (Empty)")
        self.slots["Graph-2"].grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

    def get_slot(self, slot_id: str) -> PlotSlot:
        return self.slots.get(slot_id)
