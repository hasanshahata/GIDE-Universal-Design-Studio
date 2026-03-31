import os
import subprocess
import json
import numpy as np
import pickle
from psf_utils import PSF

# Check if spectre is available in the path
try:
    subprocess.run("spectre -version", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
except (subprocess.CalledProcessError, OSError):
    print("Error: 'spectre' command not found. Please ensure it is in your PATH.", flush=True)
    # Don't exit yet, let it continue or wait for gui 
    # (Actually we will just warn since spectre might be an alias not caught by subprocess without bash)

# =========================================================================
# 1. Technology Configuration (Loaded from GUI JSON)
# =========================================================================
base_dir = os.path.abspath(os.path.dirname(__file__))
config_path = os.path.join(base_dir, "techsweep_config.json")
if not os.path.exists(config_path):
    config_path = os.path.join(os.getcwd(), "techsweep_config.json")

try:
    with open(config_path, "r") as f:
        config = json.load(f)
except FileNotFoundError:
    print(f"Error: techsweep_config.json not found at {config_path}. Please run the GUI first.", flush=True)
    exit(1)

MODEL_FILE = config['pdk']['MODEL_FILE']
CORNER = config['pdk']['CORNER']
TEMP = float(config['pdk']['TEMP'])

MODEL_N = config['pdk']['MODEL_N']
MODEL_P = config['pdk']['MODEL_P']

# Move W and NFING after parse_eng definition
# (Will be placed at line 85 after function definitions)

# =========================================================================
# 0. Utilities
# =========================================================================
def parse_eng(val: str) -> float:
    """Parse engineering notation (e.g. 180n, 1.2u, 600m)."""
    if not val: return 0.0
    val = val.lower().strip()
    suffix_map = {
        'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3,
        'k': 1e3, 'meg': 1e6, 'g': 1e9, 't': 1e12
    }
    # Check for 'meg' first since it's 3 chars
    if val.endswith('meg'):
        return float(val[:-3]) * 1e6
    for s, multiplier in suffix_map.items():
        if val.endswith(s):
            try:
                return float(val[:-len(s)]) * multiplier
            except ValueError:
                pass
    return float(val)

def parse_vector_string(s: str):
    """Parses 'start:step:stop' or 'val1, val2, ...' with engineering units."""
    if not s: return []
    parts = s.replace(',', ' ').split()
    results = []
    for p in parts:
        if ':' in p:
            sub = [parse_eng(x) for x in p.split(':')]
            if len(sub) == 3:
                results.extend(np.arange(sub[0], sub[2] + sub[1]/10, sub[1]))
            elif len(sub) == 2:
                results.extend(np.arange(sub[0], sub[1] + 1e-15, 1.0)) # unlikely
        else:
            results.append(parse_eng(p))
    return np.array(results)

W = parse_eng(config['sweep']['W'])
NFING = int(config['sweep']['NFING'])

VGS_vec = parse_vector_string(config['sweep']['VGS_VEC'])
VDS_vec = parse_vector_string(config['sweep']['VDS_VEC'])
VSB_vec = parse_vector_string(config['sweep']['VSB_VEC'])
L_vec = parse_vector_string(config['sweep']['L_VEC'])
PREFIX_N = config['map']['PREFIX_N']
PREFIX_P = config['map']['PREFIX_P']
SIGNALS = config['map']['signals']

# Phase 3 feature: Allow PDKs to specify their multiplicity parameter mapping. Default to 'm'.
M_PARAM = config['map'].get('M_PARAM', 'm')

OUT_VARS = list(SIGNALS.keys())

# =========================================================================
# 2. Netlist Generator Function (Fast Nested Sweeps)
# =========================================================================
def create_netlist():
    l_vals = " ".join([f"{v:.12g}" for v in L_vec])
    vsb_vals = " ".join([f"{v:.12g}" for v in VSB_vec])
    vds_vals = " ".join([f"{v:.12g}" for v in VDS_vec])
    vgs_vals = " ".join([f"{v:.12g}" for v in VGS_vec])

    save_n = " ".join([f"{PREFIX_N}:{s}" for s in SIGNALS.values()])
    save_p = " ".join([f"{PREFIX_P}:{s}" for s in SIGNALS.values()])

    netlist = f"""// Automatically generated Fast Python-Spectre techsweep netlist
include "{MODEL_FILE}" section={CORNER}

save {save_n} {save_p}
parameters gs=0 ds=0.1 length=65n sb=0

// --- NMOS Instantiation ---
vdsn (vdn 0) vsource dc=ds
vgsn (vgn 0) vsource dc=gs
vbsn (vbn 0) vsource dc=-sb
{PREFIX_N} (vdn vgn 0 vbn) {MODEL_N} l=length w={W:.12g} {M_PARAM}={NFING}

// --- PMOS Instantiation ---
vdsp (vdp 0) vsource dc=-ds
vgsp (vgp 0) vsource dc=-gs
vbsp (vbp 0) vsource dc=sb
{PREFIX_P} (vdp vgp 0 vbp) {MODEL_P} l=length w={W:.12g} {M_PARAM}={NFING}

options1 options rawfmt=psfascii rawfile="./techsweep.raw" redefinedparams=ignore

// NESTED SWEEPS: Spectre loops these internally in a single run
sweepL sweep param=length values=[{l_vals}] {{
    sweepVSB sweep param=sb values=[{vsb_vals}] {{
        sweepVDS sweep param=ds values=[{vds_vals}] {{
            sweepVGS dc param=gs values=[{vgs_vals}]
        }}
    }}
}}
"""
    with open("techsweep.scs", "w") as f:
        f.write(netlist)

# =========================================================================
# 3. Main Extraction Loop
# =========================================================================
def run_characterization():
    nch_data = {'L': L_vec, 'VGS': VGS_vec, 'VDS': VDS_vec, 'VSB': VSB_vec, 'W': W, 'NFING': NFING}
    pch_data = {'L': L_vec, 'VGS': VGS_vec, 'VDS': VDS_vec, 'VSB': VSB_vec, 'W': W, 'NFING': NFING}

    shape = (len(L_vec), len(VGS_vec), len(VDS_vec), len(VSB_vec))
    for var in OUT_VARS:
        nch_data[var] = np.zeros(shape)
        pch_data[var] = np.zeros(shape)

    print("Generating single nested sweep netlist...", flush=True)
    create_netlist()

    print("Running Spectre (Single Execution in Fast Mode)...", flush=True)
    if os.path.exists("techsweep.raw"):
        import shutil
        shutil.rmtree("techsweep.raw", ignore_errors=True)

    try:
        subprocess.run("spectre techsweep.scs > techsweep.out 2>&1", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Spectre simulation failed: {e}", flush=True)
        print("Please check techsweep.out for simulation details.", flush=True)
        return

    print("Reading Results using psf_utils...", flush=True)
    try:
        raw_dir = os.path.join(os.getcwd(), "techsweep.raw")
        if not os.path.exists(raw_dir):
            print(f"Error: {raw_dir} does not exist.")
            return

        cgg_name = config['map']['signals'].get('cgg', 'cgg')
        cgs_name = config['map']['signals'].get('cgs', 'cgs')
        cgd_name = config['map']['signals'].get('cgd', 'cgd')

        total_points = len(L_vec) * len(VSB_vec) * len(VDS_vec)
        processed = 0

        # Iterate through the expected shape indices to read all individual .dc files
        for i_L, L in enumerate(L_vec):
            for i_VSB, VSB in enumerate(VSB_vec):
                for i_VDS, VDS in enumerate(VDS_vec):
                    
                    filename = f"sweepL-{i_L:03d}_sweepVSB-{i_VSB:03d}_sweepVDS-{i_VDS:03d}_sweepVGS.dc"
                    psf_path = os.path.join(raw_dir, filename)
                    
                    if not os.path.exists(psf_path):
                        print(f"Warning: Expected file {filename} not found.")
                        continue
                        
                    psf = PSF(psf_path)
                    
                    for var in OUT_VARS:
                        if var == 'cgg':
                            # Dynamic capacitance proxy fallback if cgg isn't explicitly output
                            try:
                                nch_data['cgg'][i_L, :, i_VDS, i_VSB] = psf.get_signal(f"{PREFIX_N}:{cgg_name}").ordinate
                            except KeyError:
                                cgs_n = psf.get_signal(f"{PREFIX_N}:{cgs_name}").ordinate
                                cgd_n = psf.get_signal(f"{PREFIX_N}:{cgd_name}").ordinate
                                nch_data['cgg'][i_L, :, i_VDS, i_VSB] = np.abs(cgs_n) + np.abs(cgd_n)

                            try:
                                pch_data['cgg'][i_L, :, i_VDS, i_VSB] = psf.get_signal(f"{PREFIX_P}:{cgg_name}").ordinate
                            except KeyError:
                                cgs_p = psf.get_signal(f"{PREFIX_P}:{cgs_name}").ordinate
                                cgd_p = psf.get_signal(f"{PREFIX_P}:{cgd_name}").ordinate
                                pch_data['cgg'][i_L, :, i_VDS, i_VSB] = np.abs(cgs_p) + np.abs(cgd_p)
                            continue

                        suf = config['map']['signals'][var]
                        sig_n = psf.get_signal(f"{PREFIX_N}:{suf}").ordinate
                        sig_p = psf.get_signal(f"{PREFIX_P}:{suf}").ordinate
                        
                        nch_data[var][i_L, :, i_VDS, i_VSB] = sig_n
                        pch_data[var][i_L, :, i_VDS, i_VSB] = sig_p
                    
                    processed += 1
                    if processed % (max(1, total_points // 10)) == 0:
                        print(f"  > Processed {processed}/{total_points} bias points...", flush=True)

    except Exception as e:
        print(f"Error compiling split PSF files: {e}", flush=True)
        return

    print("Saving Data...", flush=True)
    nch_out = config.get('output', {}).get('nch_file', 'tech_nch.pkl')
    pch_out = config.get('output', {}).get('pch_file', 'tech_pch.pkl')

    # Construct metadata for self-documenting Look-Up Tables
    # This info is used by the Sizing Dashboard's 'Tech Summary' sidebar
    info_str = (
        f"GIDE V3 Fast LUT; PDK: {os.path.basename(MODEL_FILE)}; Corner: {CORNER}; Temp: {TEMP}C; "
        f"L_Range: [{L_vec.min():.3g}, {L_vec.max():.3g}]; "
        f"VGS_Range: [{VGS_vec.min():.3g}, {VGS_vec.max():.3g}]; "
        f"VDS_Range: [{VDS_vec.min():.3g}, {VDS_vec.max():.3g}]; "
        f"VSB_Range: [{VSB_vec.min():.3g}, {VSB_vec.max():.3g}]; "
        f"Ref_W: {W:.3g}; NFING: {NFING}"
    )
    nch_data['INFO'] = info_str
    pch_data['INFO'] = info_str
    
    with open(nch_out, 'wb') as f:
        pickle.dump(nch_data, f)
    with open(pch_out, 'wb') as f:
        pickle.dump(pch_data, f)
        
    print(f"Done! Fast LUTs generated successfully as {nch_out} and {pch_out}", flush=True)

if __name__ == "__main__":
    run_characterization()
