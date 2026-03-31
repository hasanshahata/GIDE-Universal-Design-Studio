import os
import json
import subprocess
import customtkinter as ctk
import re
import sys
import threading
import time

# Ensure parent directory is in path so we can import 'core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
try:
    from core.utils import parse_eng
except ImportError:
    parse_eng = float # Fallback

# --- Tonal Palette (Consistent with App) ---
C_BG_MAIN = "#070e1a"
C_SURFACE = "#172030"
C_SURFACE_HOVER = "#242f42"
C_TEXT_PRIMARY = "#e5ebfd"
C_TEXT_SECONDARY = "#8fa3c0"
C_BRAND = "#89acff"
C_SUCCESS = "#68fadd"
C_WARNING = "#f59e0b"
C_DANGER = "#ef4444"

class LUTGeneratorView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.pdk_vars = {}
        self.sweep_vars = {}
        
        # State management
        self.process = None
        self.is_running = False
        self.start_gen_time = 0
        self.found_signals = {}
        
        self._build_main_area()
        self._build_pdk_tab()
        self._build_sweep_tab()
        
        # Initial status
        self.after(1000, self._validate_pdk)
        
    def _build_main_area(self):
        self.main_view = ctk.CTkFrame(self, fg_color="transparent")
        self.main_view.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
        self.main_view.grid_columnconfigure(0, weight=1)
        self.main_view.grid_rowconfigure(1, weight=1)
        
        # Tabview
        self.tabview = ctk.CTkTabview(self.main_view, fg_color=C_SURFACE, text_color=C_TEXT_SECONDARY,
                                      segmented_button_selected_color=C_SURFACE_HOVER,
                                      segmented_button_selected_hover_color=C_SURFACE_HOVER,
                                      segmented_button_unselected_color=C_BG_MAIN,
                                      corner_radius=12)
        self.tabview.grid(row=1, column=0, sticky="nsew")
        
        self.tab_pdk = self.tabview.add("PDK SETTINGS")
        self.tab_sweep = self.tabview.add("SWEEP PARAMETERS")
        
        # Bottom Bar
        self.bottom_bar = ctk.CTkFrame(self.main_view, fg_color="transparent")
        self.bottom_bar.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        
        self._build_stats_cards(self.bottom_bar)
        
        self.btn_generate = ctk.CTkButton(self.bottom_bar, text="Generate LUTs  ⚡", font=ctk.CTkFont(size=14, weight="bold"),
                                          fg_color=C_BRAND, text_color=C_BG_MAIN, hover_color="#8db0ff", height=45, command=self._on_generate)
        self.btn_generate.pack(side="right", padx=10)

    def _build_stats_cards(self, parent):
        cards_frame = ctk.CTkFrame(parent, fg_color="transparent")
        cards_frame.pack(side="left", fill="x", expand=True)
        
        def make_card(master, title, val, sub):
            c = ctk.CTkFrame(master, fg_color=C_SURFACE, corner_radius=12)
            c.pack(side="left", padx=5, fill="both", expand=True)
            ctk.CTkLabel(c, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_SECONDARY).pack(anchor="w", padx=15, pady=(10,0))
            val_frame = ctk.CTkFrame(c, fg_color="transparent")
            val_frame.pack(anchor="w", padx=15, pady=(0,10))
            lbl_val = ctk.CTkLabel(val_frame, text=val, font=ctk.CTkFont(size=20, weight="bold"), text_color=C_TEXT_PRIMARY)
            lbl_val.pack(side="left")
            lbl_sub = ctk.CTkLabel(val_frame, text=" "+sub, font=ctk.CTkFont(size=10), text_color=C_BRAND)
            lbl_sub.pack(side="left", pady=(5,0))
            return lbl_val, lbl_sub
            
        self.stat_cards = {}
        self.stat_cards["TOTAL"], self.stat_cards["TOTAL_SUB"] = make_card(cards_frame, "TOTAL LUT POINTS", "0", "Points")
        self.stat_cards["TIME"], self.stat_cards["TIME_SUB"] = make_card(cards_frame, "ELAPSED TIME", "0:00", "Min:Sec")
        self.job_status_lbl, self.job_status_sub = make_card(cards_frame, "JOB STATUS", "IDLE", "Ready")

    def _build_pdk_tab(self):
        self.tab_pdk.grid_columnconfigure(0, weight=2)
        self.tab_pdk.grid_columnconfigure(1, weight=1)
        self.tab_pdk.grid_rowconfigure(0, weight=1)
        
        left_panel = ctk.CTkFrame(self.tab_pdk, fg_color="transparent")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Row 1: Model File
        ctk.CTkLabel(left_panel, text="MODEL FILE PATH (.SCS)", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_SECONDARY).pack(anchor="w", pady=(0, 5))
        file_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        file_frame.pack(fill="x", pady=(0, 20))
        self.pdk_vars['MODEL_FILE'] = ctk.CTkEntry(file_frame, fg_color=C_BG_MAIN, border_width=0, height=40, placeholder_text="/vols/design/pdk/models/toplevel.scs", placeholder_text_color="#5c6d8a")
        self.pdk_vars['MODEL_FILE'].pack(side="left", fill="x", expand=True, padx=(0,10))
        ctk.CTkButton(file_frame, text="BROWSE...", fg_color=C_SURFACE_HOVER, hover_color=C_BRAND, height=40, command=self._browse_scs).pack(side="right")
        
        # Row 2: Corner & Temp
        row2 = ctk.CTkFrame(left_panel, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 30))
        row2.grid_columnconfigure(0, weight=1)
        row2.grid_columnconfigure(1, weight=1)
        
        c1 = ctk.CTkFrame(row2, fg_color="transparent"); c1.grid(row=0, column=0, sticky="ew", padx=(0,10))
        ctk.CTkLabel(c1, text="CORNER SELECTION", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_SECONDARY).pack(anchor="w", pady=(0,5))
        self.pdk_vars['CORNER'] = ctk.CTkOptionMenu(c1, values=["tt_lib", "ff_lib", "ss_lib"], fg_color=C_BG_MAIN, button_color=C_SURFACE_HOVER, height=40)
        self.pdk_vars['CORNER'].pack(fill="x")
        
        c2 = ctk.CTkFrame(row2, fg_color="transparent"); c2.grid(row=0, column=1, sticky="ew", padx=(10,0))
        ctk.CTkLabel(c2, text="TEMPERATURE (C)", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_SECONDARY).pack(anchor="w", pady=(0,5))
        self.pdk_vars['TEMP'] = ctk.CTkEntry(c2, fg_color=C_BG_MAIN, border_width=0, height=40, placeholder_text="27.0", placeholder_text_color="#5c6d8a")
        self.pdk_vars['TEMP'].pack(fill="x")
        
        # Row 3: Subcircuits
        ctk.CTkLabel(left_panel, text="SUBCIRCUIT DEFINITIONS", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_SUCCESS).pack(anchor="w", pady=(10, 15))
        
        row3 = ctk.CTkFrame(left_panel, fg_color="transparent")
        row3.pack(fill="x")
        row3.grid_columnconfigure(0, weight=1)
        row3.grid_columnconfigure(1, weight=1)
        
        c3 = ctk.CTkFrame(row3, fg_color="transparent"); c3.grid(row=0, column=0, sticky="ew", padx=(0,10))
        ctk.CTkLabel(c3, text="NMOS SUBCKT NAME", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_SECONDARY).pack(anchor="w", pady=(0,5))
        self.pdk_vars['MODEL_N'] = ctk.CTkEntry(c3, fg_color=C_BG_MAIN, border_width=0, height=40, placeholder_text="nch", placeholder_text_color="#5c6d8a")
        self.pdk_vars['MODEL_N'].pack(fill="x")
        
        c4 = ctk.CTkFrame(row3, fg_color="transparent"); c4.grid(row=0, column=1, sticky="ew", padx=(10,0))
        ctk.CTkLabel(c4, text="PMOS SUBCKT NAME", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_SECONDARY).pack(anchor="w", pady=(0,5))
        self.pdk_vars['MODEL_P'] = ctk.CTkEntry(c4, fg_color=C_BG_MAIN, border_width=0, height=40, placeholder_text="pch", placeholder_text_color="#5c6d8a")
        self.pdk_vars['MODEL_P'].pack(fill="x")
        
        # Right panel: PDK Identity & Validation
        right_panel = ctk.CTkFrame(self.tab_pdk, fg_color=C_BG_MAIN, corner_radius=12)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        header = ctk.CTkFrame(right_panel, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(header, text="PDK IDENTITY", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_PRIMARY).pack(side="left")
        
        self.pdk_status_badge = ctk.CTkFrame(header, fg_color="#8B2A2A", corner_radius=10, height=20) # Red default
        self.pdk_status_badge.pack(side="right")
        self.pdk_status_lbl = ctk.CTkLabel(self.pdk_status_badge, text="● WAITING", font=ctk.CTkFont(size=9, weight="bold"), text_color=C_TEXT_PRIMARY)
        self.pdk_status_lbl.pack(padx=8, pady=2)
        
        def add_pdk_input(p, label, default, key):
            f = ctk.CTkFrame(p, fg_color="transparent")
            f.pack(fill="x", padx=15, pady=10)
            ctk.CTkLabel(f, text=label.upper(), font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_SECONDARY).pack(anchor="w", pady=(0, 2))
            entry = ctk.CTkEntry(f, fg_color=C_SURFACE, border_width=0, height=35, placeholder_text=str(default), placeholder_text_color="#5c6d8a")
            entry.pack(fill="x")
            self.pdk_vars[key] = entry
            return entry
            
        add_pdk_input(right_panel, "PDK Name", "CRN65", "PDK_NAME")
        add_pdk_input(right_panel, "Technology Node", "65nm", "PDK_NODE")

        # Premium Status Display
        status_panel = ctk.CTkFrame(right_panel, fg_color=C_SURFACE, corner_radius=8, border_width=1, border_color=C_SURFACE_HOVER)
        status_panel.pack(fill="x", padx=15, pady=(20, 15))
        
        lbl_status_hdr = ctk.CTkLabel(status_panel, text="JOB STATUS & ACTIVE POINT", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_BRAND)
        lbl_status_hdr.pack(anchor="w", padx=15, pady=(10, 0))
        
        self.status_val_lbl = ctk.CTkLabel(status_panel, text="Ready / Awaiting Execution", font=ctk.CTkFont(size=12, family="Courier", weight="bold"), text_color=C_TEXT_PRIMARY)
        self.status_val_lbl.pack(anchor="w", padx=15, pady=(5, 12))

    def _build_sweep_tab(self):
        self.tab_sweep.grid_columnconfigure(0, weight=1)
        self.tab_sweep.grid_columnconfigure(1, weight=1)
        
        def add_param(parent, label, default, row, col):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.grid(row=row, column=col, sticky="ew", padx=20, pady=15)
            ctk.CTkLabel(f, text=label.upper(), font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_SECONDARY).pack(anchor="w", pady=(0,5))
            entry = ctk.CTkEntry(f, fg_color=C_BG_MAIN, border_width=0, height=40, placeholder_text=str(default), placeholder_text_color="#5c6d8a")
            entry.pack(fill="x")
            return entry
            
        self.sweep_vars['W'] = add_param(self.tab_sweep, "W (ref width)", "1u", 0, 0)
        self.sweep_vars['NFING'] = add_param(self.tab_sweep, "Number of Fingers", "1", 0, 1)
        self.sweep_vars['L_VEC'] = add_param(self.tab_sweep, "L Vector (e.g. 90n, 1u)", "90n, 0.5u, 1u", 1, 0)
        self.sweep_vars['VGS_VEC'] = add_param(self.tab_sweep, "VGS Vector (e.g. 0:0.1:1.2)", "0:0.1:1.2", 1, 1)
        self.sweep_vars['VDS_VEC'] = add_param(self.tab_sweep, "VDS Vector (e.g. 0.6)", "0.6", 2, 0)
        self.sweep_vars['VSB_VEC'] = add_param(self.tab_sweep, "VSB Vector (e.g. 0, 0.1)", "0, 0.1", 2, 1)

    def _browse_scs(self):
        path = ctk.filedialog.askopenfilename(title="Select Model File", filetypes=[("Spectre Models", "*.scs"), ("All Files", "*.*")])
        if path:
            self.pdk_vars['MODEL_FILE'].delete(0, 'end')
            self.pdk_vars['MODEL_FILE'].insert(0, path)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                sections = []
                for line in lines:
                    l = line.strip()
                    if l.startswith("section"):
                        s = l.split()
                        if len(s) > 1: sections.append(s[1])
                if sections:
                    unique_sections = sorted(list(set(sections)))
                    self.pdk_vars['CORNER'].configure(values=unique_sections)
                    self.pdk_vars['CORNER'].set(unique_sections[0])
            except Exception as e:
                print("Failed to parse sections:", e)

    def _log(self, msg, color=C_TEXT_PRIMARY):
        self.job_status_sub.configure(text=msg, text_color=color)

    def _update_stats(self):
        try:
            def get_count(s):
                if not s: return 0
                if ":" in s:
                    sub = [parse_eng(x) for x in s.split(":")]
                    if len(sub) == 3:
                        return len(np.arange(sub[0], sub[2] + sub[1]/10, sub[1]))
                return len(s.replace(",", " ").split())

            l_pts = get_count(self.sweep_vars['L_VEC'].get())
            vgs_pts = get_count(self.sweep_vars['VGS_VEC'].get())
            vds_pts = get_count(self.sweep_vars['VDS_VEC'].get())
            vsb_pts = get_count(self.sweep_vars['VSB_VEC'].get())
            
            total = l_pts * vgs_pts * vds_pts * vsb_pts
            
            if total >= 1e6: text = f"{total/1e6:.1f}M"
            elif total >= 1e3: text = f"{total/1e3:.1f}k"
            else: text = str(total)
            
            self.stat_cards["TOTAL"].configure(text=text)
            self.stat_cards["TOTAL_SUB"].configure(text=f"{l_pts}L x {vgs_pts}G x {vds_pts}D x {vsb_pts}S")
        except:
            pass

    def _validate_pdk(self):
        if not self.winfo_exists():
            return
        path = self.pdk_vars['MODEL_FILE'].get()
        if path and os.path.exists(path):
            self.pdk_status_badge.configure(fg_color="#064e3b") # Green
            self.pdk_status_lbl.configure(text="● READY", text_color=C_SUCCESS)
        else:
            self.pdk_status_badge.configure(fg_color="#8B2A2A") # Red
            self.pdk_status_lbl.configure(text="● WAITING", text_color=C_TEXT_PRIMARY)
        self.after(1000, self._validate_pdk)

    def _on_generate(self):
        if self.is_running:
            if self.process:
                self.process.terminate()
                self._log("Stopped by user.", C_DANGER)
                self._finish_generation()
            return
        self._update_stats()
        
        # UI State Shift
        self.is_running = True
        self.start_gen_time = time.time()
        self.btn_generate.configure(text="Stop Generation", fg_color=C_DANGER, hover_color="#8B2A2A")
        self._update_timer()
        
        # Start background thread for the full sequence
        threading.Thread(target=self._run_sequence, daemon=True).start()

    def _run_sequence(self):
        """Full sequence: Probe then Generate, all in background to keep UI fluid."""
        # 1. Probe
        if not self._probe_pdk():
            self.after(0, self._finish_generation)
            return
            
        # 2. Launch Generator
        self._launch_generator()

    def _probe_pdk(self):
        """Auto-detect Spectre suffixes for the current PDK models."""
        self.after(0, lambda: self.job_status_lbl.configure(text="PROBING", text_color=C_WARNING))
        self.after(0, lambda: self.job_status_sub.configure(text="Auto-Detecting Suffixes...", text_color=C_WARNING))
        
        try:
            model_file = self.pdk_vars['MODEL_FILE'].get()
            corner = self.pdk_vars['CORNER'].get()
            model_n = self.pdk_vars['MODEL_N'].get()
            
            netlist = f'// Auto PDK Probe\ninclude "{model_file}" section={corner}\nsave mn:oppoint\n'
            netlist += 'parameters gs=0.6 ds=0.6 length=1.0 sb=0\nvdsn (vdn 0) vsource dc=ds\n'
            netlist += f'vgsn (vgn 0) vsource dc=gs\nvbsn (vbn 0) vsource dc=-sb\nmn (vdn vgn 0 vbn) {model_n} l=length*1u w=1.0*1u m=1\n'
            netlist += 'options1 options rawfmt=psfascii rawfile="./techprobe.raw" redefinedparams=ignore\ndc1 dc\n'
            
            if os.path.exists("techprobe.raw"):
                import shutil
                shutil.rmtree("techprobe.raw", ignore_errors=True)
            with open("techprobe.scs", "w") as f: f.write(netlist)
            subprocess.run("spectre techprobe.scs > techprobe.out 2>&1", shell=True, check=True)
            
            with open("techprobe.raw/dc1.dc", "r", encoding='utf-8', errors='ignore') as pfile: content = pfile.read()
            matches = re.findall(r'"mn:([a-zA-Z0-9_.-]+)"', content)
            available_suffixes = set(matches)
            
            common_suffixes = {
                'ids': ['id', 'ids', 'i'], 'vth': ['vth', 'vto'], 'gm': ['gm'], 'gmbs': ['gmbs', 'gmb'],
                'gds': ['gds', 'rout'], 'cgg': ['cgg', 'cggbo'], 'cgs': ['cgs', 'cgsbo'], 'cgd': ['cgd', 'cgdbo'],
                'cdd': ['cdd', 'cddbo'], 'css': ['css', 'cssbo'], 'vdsat': ['vdsat', 'vdssat']
            }
            found_signals = {}
            for sig_key, candidates in common_suffixes.items():
                found = False
                for cand in candidates:
                    if cand in available_suffixes:
                        found_signals[sig_key] = cand
                        found = True
                        break
                if not found: found_signals[sig_key] = "NOT_FOUND"
            self.found_signals = found_signals
            return True
        except Exception as e:
            msg = f"Probe error: {str(e)[:40]}..."
            self.after(0, lambda m=msg: self._log(m, C_DANGER))
            self.found_signals = {k: k for k in ['ids', 'vth', 'gm', 'gmbs', 'gds', 'cgg', 'cgs', 'cgd', 'cdd', 'css', 'vdsat']}
            return True # Proceed with fallbacks

    def _launch_generator(self):
        """Writes config and launches the process."""
        base_dir = os.path.abspath(os.path.dirname(__file__))
        root_dir = os.path.abspath(os.path.join(base_dir, ".."))
        
        pdk = self.pdk_vars.get('PDK_NAME', 'GENERIC').get()
        node = self.pdk_vars.get('PDK_NODE', 'NODE').get()
        model_n = self.pdk_vars['MODEL_N'].get()
        model_p = self.pdk_vars['MODEL_P'].get()
        
        config = {
            "pdk": {k: v.get() for k, v in self.pdk_vars.items() if hasattr(v, 'get')},
            "sweep": {k: v.get() for k, v in self.sweep_vars.items() if hasattr(v, 'get')},
            "map": { "PREFIX_N": "mn", "PREFIX_P": "mp", "signals": self.found_signals },
            "output": { "nch_file": f"{pdk}_{node}_{model_n}.pkl", "pch_file": f"{pdk}_{node}_{model_p}.pkl" }
        }
        
        if getattr(sys, 'frozen', False):
            config_path = os.path.join(os.getcwd(), "techsweep_config.json")
        else:
            config_path = os.path.join(root_dir, "luts_generation", "techsweep_config.json")
            
        with open(config_path, "w") as f: json.dump(config, f, indent=4)
            
        self.after(0, lambda: self.job_status_lbl.configure(text="RUNNING", text_color=C_BRAND))
        self.after(0, lambda: self._log("Starting engine..."))
        
        script_path = os.path.join(root_dir, "luts_generation", "techsweep_spectre.py")
        try:
            run_cwd = os.path.dirname(script_path)
            
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--techsweep"]
                run_cwd = os.getcwd()
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
            else:
                cmd = [sys.executable, "-u", script_path]
                env = os.environ.copy()
                
            self.process = subprocess.Popen(
                cmd, 
                cwd=run_cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )
            
            # Read logic using local process reference to avoid NoneType race
            threading.Thread(target=self._read_output, args=(self.process,), daemon=True).start()
        except Exception as e:
            self.after(0, lambda: self._log(f"Error: {e}", C_DANGER))
            self.after(0, self._finish_generation)

    def _read_output(self, proc):
        """Reads output from the characterization process and updates status."""
        try:
            for line in iter(proc.stdout.readline, ''):
                if not line: break
                line = line.strip()
                print(f"[LUT GEN] {line}") # Print to terminal for debugging
                
                if "Error:" in line or "Traceback" in line or "Exception" in line:
                    self.after(0, lambda l=line: self._log(l, C_DANGER))
                
                if "Generating single nested sweep netlist" in line:
                    self.after(0, lambda: self.status_val_lbl.configure(text="INIT  >>  Generating Netlist", text_color=C_WARNING))
                elif "Running Spectre" in line:
                    self.after(0, lambda: self.status_val_lbl.configure(text="INIT  >>  Running Spectre Simulator", text_color=C_WARNING))
                elif "Reading Results" in line:
                    self.after(0, lambda: self.status_val_lbl.configure(text="INIT  >>  Reading raw results", text_color=C_WARNING))
                elif "> Processed" in line:
                    val = line.split("Processed")[1].strip().replace("...", "")
                    self.after(0, lambda v=val: self.status_val_lbl.configure(text=f"RUN   >>  Parsed {v}", text_color=C_SUCCESS))
                elif "Saving Data" in line:
                    self.after(0, lambda: self.status_val_lbl.configure(text="RUN   >>  Saving PKL...", text_color=C_SUCCESS))
            
            proc.wait()
        except: pass
        finally:
            self.after(0, self._finish_generation)

    def _update_timer(self):
        if not self.winfo_exists() or not getattr(self, 'is_running', False):
            return
        elapsed = time.time() - self.start_gen_time
        hours = int(elapsed // 3600)
        mins = int((elapsed % 3600) // 60)
        secs = int(elapsed % 60)
        
        if hours > 0:
            self.stat_cards["TIME"].configure(text=f"{hours:02d}:{mins:02d}:{secs:02d}")
        else:
            self.stat_cards["TIME"].configure(text=f"{mins:02d}:{secs:02d}")
            
        self.after(1000, self._update_timer)

    def _finish_generation(self):
        self.is_running = False
        self.btn_generate.configure(text="Generate LUTs  ⚡", fg_color=C_BRAND, hover_color="#8db0ff")
        self.job_status_lbl.configure(text="IDLE", text_color=C_BRAND)
        self.status_val_lbl.configure(text="Finalized / Ready", text_color=C_TEXT_PRIMARY)
        self.process = None
        # self._log("Characterization finalized.")
