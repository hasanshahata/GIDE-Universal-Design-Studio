# GIDE - Universal Design Studio: Modernized Sizing & Characterization

<!DOCTYPE html><html class="dark" lang="en"><head>
<meta charset="utf-8">
<meta content="width=device-width, initial-scale=1.0" name="viewport">
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=Manrope:wght@700;800&amp;display=swap" rel="stylesheet">
<script id="tailwind-config">
      tailwind.config = {
        darkMode: "class",
        theme: {
          extend: {
            colors: {
              "background": "#070e1a",
              "surface-container-low": "#0c1321",
              "primary": "#89acff",
              "on-surface": "#e5ebfd",
              "on-surface-variant": "#a4abbc",
            },
            fontFamily: {
              "headline": ["Manrope"],
              "body": ["Inter"],
            },
          },
        },
      }
    </script>
<style>
    body { background-color: #070e1a !important; margin: 0; padding: 20px; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
    #logo-target { display: inline-flex; align-items: center; gap: 1.5rem; padding: 1rem; background-color: #070e1a; border-radius: 1rem; }
    .g-shadow { filter: drop-shadow(0 0 8px rgba(137, 172, 255, 0.4)); }
</style>
</head>
<body class="font-body">
<div id="logo-target" class="select-none">
    <!-- Stylized 'G' Icon with Shadow -->
    <div class="relative flex items-center justify-center w-16 h-16 g-shadow">
        <div class="absolute inset-0 rounded-2xl border-2 border-primary/30 bg-surface-container-low shadow-[inset_0_0_15px_rgba(137,172,255,0.1)]"></div>
        <div class="relative w-10 h-10 flex items-center justify-center">
            <!-- Circular Base -->
            <div class="absolute inset-0 rounded-full border-[6px] border-primary/50"></div>
            <!-- Crossbar -->
            <div class="absolute top-1/2 left-1/2 -translate-y-1/2 w-6 h-[6px] bg-primary rounded-full ml-1.5"></div>
            <!-- Inner Polish SVG -->
            <svg class="absolute inset-0 w-full h-full text-primary fill-none stroke-current" style="stroke-width: 6; stroke-linecap: round; stroke-linejoin: round;" viewBox="0 0 40 40">
                <path d="M32 20C32 26.6274 26.6274 32 20 32C13.3726 32 8 26.6274 8 20C8 13.3726 13.3726 8 20 8C24.4183 8 28.2433 10.3869 30.3431 13.9119"></path>
                <path d="M20 20H32"></path>
            </svg>
        </div>
        <!-- Lens Glint -->
        <div class="absolute top-2 right-2 w-3 h-3 bg-primary/20 rounded-full blur-[1px]"></div>
    </div>

    <!-- Typography Container -->
    <div class="flex flex-col">
        <h1 class="font-headline text-5xl font-extrabold tracking-tighter text-on-surface leading-none">
            G<span class="text-primary">I</span>DE
        </h1>
        <span class="font-body text-[10px] uppercase tracking-[0.4em] font-bold text-on-surface-variant mt-1.5 pl-1">gm/id hacking</span>
        
        <!-- Premium Line Separator -->
        <div class="w-full h-[3px] bg-gradient-to-r from-primary/80 via-primary/30 to-transparent mt-3 relative">
            <div class="absolute right-0 top-1/2 -translate-y-1/2 w-2 h-2 bg-primary rounded shadow-[0_0_10px_rgba(137,172,255,0.8)]"></div>
        </div>
        
        <!-- Updated Attribution -->
        <span class="text-[9px] text-primary/80 font-bold tracking-[0.2em] mt-2 italic text-left w-full opacity-90">By: Hassan Shehata</span>
    </div>
</div>
</body></html>


**GIDE* is a comprehensive, cross-platform standalone application built for modern Analog IC Designers. It streamlines the $g_m/I_D$ design methodology by automating the characterization of semiconductor devices (using Cadence Spectre) and providing a Universal Sizing Engine to instantly translate circuit specifications into precise transistor dimensions.

## Features

*   **Universal Sizing Engine:** Input design targets like Transit Frequency ($f_T$), Intrinsic Gain ($g_m/g_{ds}$), and Target $g_m$, and instantly receive the optimal channel Length ($L$) and Width ($W$).
*   **Automated LUT Generation:** A built-in wrapper for Cadence Spectre that automatically sweeps bias voltages and geometries to generate high-precision Look-Up Tables (LUTs).
*   **High-Precision Interpolation:** Uses advanced spline interpolation to guarantee precision even between simulated grid points.
*   **Integrated Plotter:** Visualize key trade-offs (e.g., $g_m/I_D$ vs. $f_T$, $I_D/W$ vs. $g_m/I_D$) to make informed design decisions.
*   **Standalone Portability:** Shipped as standalone binaries for both Windows and Linux—no complex Python environment setup required.

## 🧠 Under the Hood (Advanced Engineering)
*   **Mathematical Supremacy (PCHIP):** Employs Scipy's Piecewise Cubic Hermite Interpolating Polynomials alongside multi-dimensional tensor interpolation (`RegularGridInterpolator`). This prevents Runge's Phenomenon (ringing) in subthreshold exponential regions to guarantee monotonicity.
*   **Zero-Crossing Multi-dimensional Solvers:** The universal engine utilizes discrete grid root-bracketing combined with robust Brent solvers (`scipy.optimize.brentq`). This safely navigates highly complex multi-constraint sizing routing without mathematical divergence.
*   **Device Agnostic Backend:** The mathematical engine normalizes and absolute-maps PMOS physical data to perfectly emulate NMOS dimensions under the hood, effectively shrinking the codebase in half while preventing sign-inversion bugs during gradient plotting.

## 🛠️ Verified PDKs
The built-in LUT extraction has been successfully tested on industry-standard device models:
*   **65nm** (`nch` / `pch`, models loaded from `toplevel.scs`, `tt_lib` corner)
*   **90nm** (`n_10_sp` / `p_10_sp`, `tt` corner)
*   **Cadence gpdk045** (`g45n1svt` / `g45p1svt`, `tt` corner)

---

## 🚀 Getting Started (Using the Standalone Apps)

> **Important Note:** Due to GitHub's file size limits, the pre-compiled standalone executables (`.exe` and Linux binaries) and the heavy technology LUT files (`*.pkl`) are hosted in the **[GitHub Releases](../../releases)** section of this repository. Please download the latest release `.zip` from there!

### Windows
1. Download the release `.zip` and extract the files to a folder.
2. Double-click the `GIDE_Sizing_Dashboard.exe` (or similarly named Windows executable).
3. The application will launch immediately.

### Linux (Important Note for Cadence Users)
If you intend to generate *new* LUTs on Linux, the application needs access to the `spectre` simulator. 
**Do not double-click the app from the Desktop** unless you have created a launcher script, because the graphical desktop does not load your terminal's `.bashrc` or `.bash_profile`.

**Best way to launch on Linux:**
1. Open your terminal.
2. Ensure your Cadence environment variables are loaded (e.g., you can type `spectre -version` and get a valid response).
3. Navigate to the folder: `cd path/to/GIDE\ Apps`
4. Run the application: `./GIDE_Sizing_Dashboard_Linux`

---

## 📖 Beginner's Step-by-Step Manual

If you are new to the $g_m/I_D$ methodology, follow this procedure to size your first transistor:

### Step 1: Generate or Load a Look-Up Table (LUT)
Before sizing, the tool needs to understand the behavior of your specific technology node (e.g., TSMC 65nm).
*   **To use existing data:** Open the app, stay on the **Sizing Dashboard**, and click **Load NMOS Data** or **Load PMOS Data**. Select one of the `.pkl` files provided in the extracted release folder.
*   **To generate new data:** 
    1. Navigate to the **LUTs Generation** tab.
    2. Input your desired parameter sweeps. For a fast yet highly accurate "Golden Config", use:
       *   **W:** `5 µm`, **NFING:** `1`
       *   **L:** `60nm` to `1.0µm` (Step: `20nm` or `25nm`)
       *   **VGS & VDS:** `0.0V` to `1.2V` (Step: `25mV` each)
       *   **VSB:** `0.0V` to `1.2V` (Step: `300mV`, just 5 points)
    3. Click Generate. The tool will drive Spectre in the background and show a live Job Status. Once finished, a `.pkl` file will be created.

### Step 2: Set Global Biases
Once your LUT is loaded, look at the left panel on the **Sizing Dashboard**.
1.  **Drain-Source ($V_{DS}$):** Set the expected voltage drop across the transistor (e.g., `0.6V`).
2.  **Source-Bulk ($V_{SB}$):** Set the body bias (usually `0V` for source-tied devices).

### Step 3: Configure Your Design Targets
Move to the **Universal Sizing Engine** section in the center. You have 3 Degrees of Freedom to constrain your transistor:
1.  **Inversion Level:** Choose $f_T$ (Speed) or $g_m/I_D$ (Efficiency).
2.  **Geometry & Performance:** Set a target Intrinsic Gain ($v/v$) or force a specific Channel Length ($L$).
3.  **Target Scaling:** Define the total current ($I_D$) or the necessary transconductance ($g_m$).

*Example: Set $g_m/I_D$ to `15`, Intrinsic Gain to `30`, and Target $g_m$ to `1mS`.*

### Step 4: Run Universal Solver
1. Click the large **RUN UNIVERSAL SOLVER** button at the bottom.
2. The engine will instantly interpolate the LUT database and return:
   *   The required **Width ($W$)** and **Length ($L$)**.
   *   All Biasing Metrics (Required $V_{GS}$, $V_{DSAT}$, etc.).
   *   Small signal parameters ($g_{ds}$, $c_{gg}$, etc.).

### Step 5: Explore Trade-offs (Plotter)
To gain deeper intuition:
1. Navigate to the **Plotter** tab on the left.
2. Select your X and Y axes (e.g., plot $f_T$ versus $g_m/I_D$).
3. Use the generated plots to visually verify why the solver chose the specific optimal sizing point.

---

## 🛠️ Built With
*   **Python 3**
*   **CustomTkinter** - For the modernized UI.
*   **SciPy / NumPy** - For multi-dimensional spline interpolation and matrix handling.
*   **PyInstaller** - For cross-platform standalone executable packaging.

## 📝 License
This project is for educational and engineering design purposes. Ensure you have the appropriate Cadence standard licensing to generate technology data.

---

## 👨‍💻 Author

**Hassan Shehata Ali BadrEL-den**  
*Master Student and Teaching Assistant*  
Faculty of Engineering, Department of Electronics and Communications  
Mansoura University

* 📧 **Email:** [hassanbader80@gmail.com](mailto:hassanbader80@gmail.com)
* 💼 **LinkedIn:** [linkedin.com/in/hshehata](https://www.linkedin.com/in/hshehata)
* 🐙 **GitHub:** [@hasanshahata](https://github.com/hasanshahata)
