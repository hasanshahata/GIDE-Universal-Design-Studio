import sys
import os

if __name__ == "__main__":
    if "--techsweep" in sys.argv:
        import runpy
        runpy.run_module('luts_generation.techsweep_spectre', run_name='__main__')
    else:
        from gui.app import App
        app = App()
        app.mainloop()
