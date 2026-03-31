import matplotlib.pyplot as plt
from matplotlib.backend_bases import Event
import numpy as np
from core.utils import eng

C_PRIMARY = "#89acff"
C_CURSOR_V = "#FFFFFF" # Neutral White
C_CURSOR_H = "#A9A9A9" # Neutral Dark Grey
C_SURFACE_HIGH = "#172030"
C_ON_SURFACE = "#e5ebfd"

class PlotInteractor:
    """
    Handles interactive tools for a matplotlib axes.
    Provides snap-to-data draggable crosshairs via 'v' and 'h' keys,
    and hovering annotations for data readouts.
    """
    def __init__(self, ax, canvas, slot_frame):
        self.ax = ax
        self.canvas = canvas
        self.slot_frame = slot_frame
        
        # State
        self.v_lines = [] # Each entry: {"line": Line2D, "type": "v", "labels": [Annotation, ...]}
        self.h_lines = [] # Each entry: {"line": Line2D, "type": "h", "labels": [Annotation, ...]}
        self.active_draggable = None
        self.permanent_labels = []
        
        # Event hooks
        self.cid_press = self.canvas.mpl_connect("key_press_event", self.on_key)
        self.cid_pick = self.canvas.mpl_connect("button_press_event", self.on_click)
        self.cid_motion = self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.cid_release = self.canvas.mpl_connect("button_release_event", self.on_release)
        
    def get_state(self):
        state = {
            "v_lines": [obj["line"].get_xdata()[0] for obj in self.v_lines],
            "h_lines": [obj["line"].get_ydata()[0] for obj in self.h_lines],
            "perm_labels": []
        }
        for ann in self.permanent_labels:
            # text is in ann.get_text(), xy is in ann.xy
            state["perm_labels"].append({"xy": ann.xy, "text": ann.get_text()})
        return state

    def restore_state(self, state):
        for vx in state.get("v_lines", []):
            line = self.ax.axvline(x=vx, color=C_CURSOR_V, linestyle="--", linewidth=1.5, picker=True, pickradius=5)
            obj = {"line": line, "type": "v", "labels": []}
            self.v_lines.append(obj)
            self._update_cursor_labels(obj)
            
        for hy in state.get("h_lines", []):
            line = self.ax.axhline(y=hy, color=C_CURSOR_H, linestyle="--", linewidth=1.5, picker=True, pickradius=5)
            obj = {"line": line, "type": "h", "labels": []}
            self.h_lines.append(obj)
            self._update_cursor_labels(obj)
            
        for lbl in state.get("perm_labels", []):
            ann = self.ax.annotate(
                lbl["text"],
                xy=lbl["xy"], xytext=(15, 15),
                textcoords="offset points",
                bbox={"boxstyle": "round,pad=0.3", "fc": C_SURFACE_HIGH, "ec": C_PRIMARY, "alpha": 0.9},
                color=C_ON_SURFACE, fontsize=9,
                arrowprops={"arrowstyle": "->", "color": C_PRIMARY, "lw": 1.5},
                zorder=10
            )
            self.permanent_labels.append(ann)
            
        self.canvas.draw_idle()

    def _create_annotation(self, color=C_ON_SURFACE):
        # A floating callout box matching the Precision Observer theme
        ann = self.ax.annotate(
            "", xy=(0,0), xytext=(10, 10),
            textcoords="offset points",
            bbox={"boxstyle": "round,pad=0.3", "fc": C_SURFACE_HIGH, "ec": "#2A3548", "alpha": 0.9},
            color=color, fontsize=9,
            arrowprops={"arrowstyle": "->", "color": color, "lw": 0.5},
            visible=False,
            zorder=10
        )
        return ann
    
    def clear_cursors(self):
        """Removes all interactive elements from the axes and resets state."""
        for obj in self.v_lines + self.h_lines:
            try: obj["line"].remove()
            except: pass
            for ann in obj["labels"]:
                try: ann.remove()
                except: pass
        self.v_lines = []
        self.h_lines = []
        
        for ann in self.permanent_labels:
            try: ann.remove()
            except: pass
        self.permanent_labels = []
        self.canvas.draw_idle()

    def on_key(self, event: Event):
        if not event.inaxes == self.ax: return
        
        if event.key == "v":
            line = self.ax.axvline(x=event.xdata, color=C_CURSOR_V, linestyle="--", linewidth=1.5, picker=True, pickradius=5)
            obj = {"line": line, "type": "v", "labels": []}
            self.v_lines.append(obj)
            self._update_cursor_labels(obj)
            self.canvas.draw_idle()
            
        elif event.key == "h":
            line = self.ax.axhline(y=event.ydata, color=C_CURSOR_H, linestyle="--", linewidth=1.5, picker=True, pickradius=5)
            obj = {"line": line, "type": "h", "labels": []}
            self.h_lines.append(obj)
            self._update_cursor_labels(obj)
            self.canvas.draw_idle()

    def _show_cursor_menu(self, obj, event):
        import tkinter as tk
        from core.utils import parse_eng
        import customtkinter as ctk
        
        canvas = self.canvas.get_tk_widget()
        menu = tk.Menu(canvas, tearoff=0, bg="#2A3548", fg=C_ON_SURFACE, activebackground=C_PRIMARY)
        
        is_v = obj["type"] == "v"
        axis_name = "X" if is_v else "Y"
        
        def delete_cursor():
            obj["line"].remove()
            for ann in obj["labels"]:
                ann.remove()
            if is_v: self.v_lines.remove(obj)
            else: self.h_lines.remove(obj)
            self.canvas.draw_idle()
            
        def move_cursor():
            dialog = ctk.CTkInputDialog(text=f"Enter exact {axis_name} value (e.g. 10m, 1.2):", title="Move Cursor")
            val = dialog.get_input()
            if val:
                try:
                    num = parse_eng(val)
                    if is_v: obj["line"].set_xdata([num, num])
                    else: obj["line"].set_ydata([num, num])
                    self._update_cursor_labels(obj)
                    self.canvas.draw_idle()
                except Exception as e:
                    print(f"Invalid Coordinate: {e}")
                    
        menu.add_command(label="Delete", command=delete_cursor)
        menu.add_command(label=f"Send to {axis_name}...", command=move_cursor)
        
        # Position logic
        gui_evt = getattr(event, 'guiEvent', None)
        if gui_evt:
            menu.tk_popup(gui_evt.x_root, gui_evt.y_root)
        else:
            rx = canvas.winfo_rootx() + int(event.x)
            ry = canvas.winfo_rooty() + (canvas.winfo_height() - int(event.y))
            menu.tk_popup(rx, ry)

    def _add_permanent_label(self, event):
        nearest_trace = None
        min_dist = float('inf')
        best_x, best_y = 0, 0
        
        px, py = event.x, event.y
        
        for trace in self.slot_frame.traces:
            xdata, ydata = trace.get_xdata(), trace.get_ydata()
            if len(xdata) == 0: continue
            
            # Map trace data coordinates to physical display pixels
            xy_pixels = self.ax.transData.transform(np.column_stack([xdata, ydata]))
            dists = np.sqrt((xy_pixels[:, 0] - px)**2 + (xy_pixels[:, 1] - py)**2)
            
            # Ignore NaNs during distance calculation
            dists = np.nan_to_num(dists, nan=np.inf)
            
            if np.all(np.isinf(dists)):
                continue
                
            idx = dists.argmin()
            
            if dists[idx] < 15: # Snapping collision sphere
                if dists[idx] < min_dist:
                    min_dist = dists[idx]
                    nearest_trace = trace
                    best_x, best_y = xdata[idx], ydata[idx]
                    
        if nearest_trace:
            ann = self.ax.annotate(
                f"X: {eng(best_x)}\nY: {eng(best_y)}",
                xy=(best_x, best_y), xytext=(15, 15),
                textcoords="offset points",
                bbox={"boxstyle": "round,pad=0.3", "fc": C_SURFACE_HIGH, "ec": C_PRIMARY, "alpha": 0.9},
                color=C_ON_SURFACE, fontsize=9,
                arrowprops={"arrowstyle": "->", "color": C_PRIMARY, "lw": 1.5},
                zorder=10
            )
            # We track pick events for deletion
            self.permanent_labels.append(ann)
            self.canvas.draw_idle()

    def on_click(self, event: Event):
        if not event.inaxes == self.ax: return
        
        if event.button == 3: # Right Click
            clicked_obj = None
            px, py = event.x, event.y
            
            # Robust pixel-distance check for cursors
            for obj in self.v_lines + self.h_lines:
                line = obj["line"]
                is_v = obj["type"] == "v"
                if is_v:
                    lx = self.ax.transData.transform((line.get_xdata()[0], 0))[0]
                    if abs(lx - px) < 10: 
                        clicked_obj = obj
                        break
                else:
                    ly = self.ax.transData.transform((0, line.get_ydata()[0]))[1]
                    if abs(ly - py) < 10:
                        clicked_obj = obj
                        break
                    
            if clicked_obj:
                self._show_cursor_menu(clicked_obj, event)
                return
                
            # Check permanent labels right-click deletion
            for ann in self.permanent_labels:
                if ann.contains(event)[0]:
                    ann.remove()
                    self.permanent_labels.remove(ann)
                    self.canvas.draw_idle()
                    return
            
            # If nothing specific was clicked, show general plot menu (Log Scales)
            self._show_general_menu(event)
            
        elif event.button == 1: # Left Click
            # Check if we clicked any draggable line
            for obj in self.v_lines + self.h_lines:
                line = obj["line"]
                contains, _ = line.contains(event)
                if contains:
                    self.active_draggable = obj
                    return
            
            # If no cursor clicked, spawn a persistent annotation
            self._add_permanent_label(event)

    def on_release(self, event: Event):
        if self.active_draggable:
            self.active_draggable = None
            self.canvas.draw_idle()

    def on_motion(self, event: Event):
        if not event.inaxes == self.ax: return
        
        if self.active_draggable:
            obj = self.active_draggable
            is_v = obj["type"] == "v"
            new_val = event.xdata if is_v else event.ydata
            if is_v: obj["line"].set_xdata([new_val, new_val])
            else: obj["line"].set_ydata([new_val, new_val])
            self._update_cursor_labels(obj)
            self.canvas.draw_idle()

    def _find_intersections(self, data, target):
        """Finds all indices where the data crosses the target value."""
        valid = np.isfinite(data)
        clean_data = data[valid]
        clean_idx = np.where(valid)[0]
        
        if len(clean_data) < 2:
            if len(clean_data) == 1:
                return [clean_idx[0]]
            return []
            
        diffs = np.diff(clean_idx)
        signs = np.sign(clean_data - target)
        
        valid_crossings = np.where((np.diff(signs) != 0) & (diffs == 1))[0]
        
        indices = []
        for i in valid_crossings:
            if abs(clean_data[i] - target) < abs(clean_data[i+1] - target):
                indices.append(clean_idx[i])
            else:
                indices.append(clean_idx[i+1])
                
        # Remove duplicates
        indices = list(dict.fromkeys(int(i) for i in indices))
        
        # If no crossings, fallback to absolute closest point
        if not indices and len(clean_data) > 0:
            min_idx = np.argmin(np.abs(clean_data - target))
            indices.append(int(clean_idx[min_idx]))
            
        return indices

    def _update_cursor_labels(self, obj):
        is_v = obj["type"] == "v"
        line = obj["line"]
        new_val = line.get_xdata()[0] if is_v else line.get_ydata()[0]
        
        traces = self.slot_frame.traces
        if not traces:
            for ann in obj["labels"]: ann.set_visible(False)
            return

        # We might need multiple labels per trace if there are multiple intersections.
        # So we collect all (x, y, text) points to label first.
        label_points = []

        for trace in traces:
            xdata, ydata = trace.get_xdata(), trace.get_ydata()
            if len(xdata) == 0:
                continue
                
            if is_v:
                indices = self._find_intersections(xdata, new_val)
            else:
                indices = self._find_intersections(ydata, new_val)
                
            lbl = trace.get_label()
            prefix = f"{lbl}\n" if (lbl and lbl != "_nolegend_") else ""
            
            for idx in indices:
                snap_x, snap_y = xdata[idx], ydata[idx]
                text = prefix + f"X: {eng(snap_x)}\nY: {eng(snap_y)}"
                label_points.append((snap_x, snap_y, text))

        # Ensure enough annotation objects exist
        while len(obj["labels"]) < len(label_points):
            obj["labels"].append(self._create_annotation(color=C_CURSOR_V if is_v else C_CURSOR_H))
            
        # Hide excess labels
        for ann in obj["labels"][len(label_points):]:
            ann.set_visible(False)
            
        # Update and show needed labels
        for i, (x, y, text) in enumerate(label_points):
            ann = obj["labels"][i]
            ann.xy = (x, y)
            ann.set_text(text)
            ann.set_visible(True)

    def _show_general_menu(self, event):
        import tkinter as tk
        canvas = self.canvas.get_tk_widget()
        menu = tk.Menu(canvas, tearoff=0, bg="#2A3548", fg=C_ON_SURFACE, 
                        activebackground=C_PRIMARY, font=("Inter", 10))
        
        x_log = self.ax.get_xscale() == "log"
        y_log = self.ax.get_yscale() == "log"
        
        def toggle_log_x():
            self.ax.set_xscale("log" if not x_log else "linear")
            self.slot_frame._format_axes()
            self.canvas.draw_idle()

        def toggle_log_y():
            self.ax.set_yscale("log" if not y_log else "linear")
            self.slot_frame._format_axes()
            self.canvas.draw_idle()
            
        menu.add_command(label="✓ Log Scale X" if x_log else "  Log Scale X", command=toggle_log_x)
        menu.add_command(label="✓ Log Scale Y" if y_log else "  Log Scale Y", command=toggle_log_y)
        
        # Position logic
        gui_evt = getattr(event, 'guiEvent', None)
        if gui_evt:
            menu.tk_popup(gui_evt.x_root, gui_evt.y_root)
        else:
            rx = canvas.winfo_rootx() + int(event.x)
            ry = canvas.winfo_rooty() + (canvas.winfo_height() - int(event.y))
            menu.tk_popup(rx, ry)

    def refresh_all_labels(self):
        """Called when plot data changes to update static cursor readouts."""
        for obj in self.v_lines + self.h_lines:
            self._update_cursor_labels(obj)
        self.canvas.draw_idle()
