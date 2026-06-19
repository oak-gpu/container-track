import os

# --- Maersk ---
MAERSK_CLIENT_ID = os.getenv("MAERSK_CLIENT_ID", "")
MAERSK_CLIENT_SECRET = os.getenv("MAERSK_CLIENT_SECRET", "")

# --- Hapag-Lloyd ---
HAPAG_LLOYD_API_KEY = os.getenv("HAPAG_LLOYD_API_KEY", "")

# --- CMA CGM ---
CMA_CGM_API_KEY = os.getenv("CMA_CGM_API_KEY", "")

# --- MyShipTracking (AIS vessel position + ETA) ---
# Register at: https://api.myshiptracking.com
MYSHIPTRACKING_API_KEY = os.getenv("MYSHIPTRACKING_API_KEY", "")

# Excel row/column mapping (1-based)
COL_VESSEL    = 1   # A  — vessel / voyage name
COL_CARRIER   = 2   # B
COL_ETD       = 3   # C  — estimated time of departure
COL_ETA       = 4   # D  — booked ETA at destination
COL_CONTAINER = 5   # E
COL_STATUS    = 6   # F  — container situation
COL_LOCATION        = 8   # H  — container location
COL_ACTUAL_DELIVERY = 20  # T  — actual delivery date (manually filled)
COL_MMSI         = 25  # Y  — cached MMSI (populated on first AIS lookup)
COL_UPDATED_ETA  = 26  # Z  — ETA as broadcast by the vessel (AIS)
COL_ACTUAL_ARR   = 27  # AA — actual arrival date at US port (set once, never overwritten)
HEADER_ROWS   = 1   # rows to skip at the top
