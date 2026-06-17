"""Thin shim — delegates to live_rail.setup.pzdc.

Use `live-rail setup pzdc` instead.
"""

from live_rail.setup.pzdc import PzdcSetup

if __name__ == "__main__":
    PzdcSetup().run()
