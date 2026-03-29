# GIDE - Universal Design Studio: Modernized Sizing & Characterization



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
