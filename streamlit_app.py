import io
import re
from datetime import datetime

import openpyxl
import streamlit as st

import config
from trackers import ais as tracker_ais

# Load API key from Streamlit secrets (set via Streamlit Cloud dashboard)
try:
    config.MYSHIPTRACKING_API_KEY = st.secrets["MYSHIPTRACKING_API_KEY"]
except Exception:
    pass

# ── Port name lookup ──────────────────────────────────────────────────────────

_PORT_NAMES = {
    "USSAV": "Savannah, GA",     "USLAX": "Los Angeles, CA",
    "USLGB": "Long Beach, CA",   "USNYC": "New York, NY",
    "USHOU": "Houston, TX",      "USORF": "Norfolk, VA",
    "USCHA": "Charleston, SC",   "USJAX": "Jacksonville, FL",
    "USMOB": "Mobile, AL",       "USBAL": "Baltimore, MD",
    "USSEA": "Seattle, WA",      "USOAK": "Oakland, CA",
    "USTAC": "Tacoma, WA",       "USBOS": "Boston, MA",
    "USNOL": "New Orleans, LA",
    "MTMLA": "Valletta, Malta",  "MAPTM": "Tanger Med, Morocco",
    "ITSAL": "Salerno, Italy",   "ITGOA": "Genoa, Italy",
    "ITCAG": "Cagliari, Italy",  "ITTRS": "Trieste, Italy",
    "ESBCN": "Barcelona, Spain", "ESVLC": "Valencia, Spain",
    "ESLPA": "Las Palmas",       "GRSKG": "Thessaloniki, Greece",
    "GRPIR": "Piraeus, Greece",  "TRIZM": "Izmir, Turkey",
    "TRGEM": "Gemlik, Turkey",   "TRMER": "Mersin, Turkey",
    "TRAMS": "Ambarli, Turkey",  "TRIST": "Istanbul, Turkey",
    "AEJEA": "Jebel Ali, UAE",   "EGPSD": "Port Said, Egypt",
    "EGALS": "Alexandria, Egypt","SAJED": "Jeddah, Saudi Arabia",
    "SGSIN": "Singapore",        "CNSHA": "Shanghai, China",
    "CNNGB": "Ningbo, China",    "HKHKG": "Hong Kong",
    "PKKAR": "Karachi, Pakistan","INBOM": "Mumbai, India",
}


def _locode_to_name(code: str) -> str:
    if not code:
        return ""
    return _PORT_NAMES.get(code.strip().upper(), code.strip())


def _eta_date(eta: str) -> str:
    if not eta:
        return ""
    return eta.replace("T", " ").split(" ")[0].split(".")[0]


def _fmt_date(iso_date: str) -> str:
    if not iso_date:
        return ""
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%b %Y')}"
    except Exception:
        return iso_date


def _build_situation(ais: dict) -> tuple[str, str]:
    from trackers.ais import is_us_port, _port_name, _port_locode

    nav          = ais.get("nav_status", "")
    dest         = ais.get("destination", "")
    eta          = ais.get("eta", "")
    current_port = ais.get("current_port", "")
    next_port    = ais.get("next_port", "")
    next_eta     = ais.get("next_port_eta", "")
    arrived_at   = _eta_date(ais.get("arrived_at", ""))

    cur_locode  = _port_locode(current_port)
    cur_name    = _locode_to_name(_port_name(current_port) or cur_locode)
    next_locode = _port_locode(next_port)
    dest_name   = _locode_to_name(dest)

    if is_us_port(cur_locode) or (nav in ("Moored", "At anchor", "At Anchor") and is_us_port(dest)):
        port = cur_name if is_us_port(cur_locode) else dest_name
        actual = arrived_at or _eta_date(eta)
        return f"ARRIVED — {port}", actual

    if is_us_port(dest):
        eta_date = _eta_date(eta)
        status = f"IN TRANSIT → {dest_name}"
        if eta_date:
            status += f" | ETA {_fmt_date(eta_date)}"
        return status, eta_date

    if is_us_port(next_locode):
        eta_date = _eta_date(next_eta)
        next_name = _locode_to_name(_port_name(next_port) or next_locode)
        stop = cur_name or dest_name
        status = f"AT PORT: {stop} → Next: {next_name}"
        if eta_date:
            status += f" | US ETA {_fmt_date(eta_date)}"
        return status, eta_date

    if nav in ("Moored", "At anchor", "At Anchor"):
        port_info = cur_name or dest_name or "intermediate port"
        return f"AT PORT: {port_info} (en route to US)", ""

    if dest:
        eta_date = _eta_date(eta)
        status = f"AT SEA → {dest_name}"
        if eta_date:
            status += f" | Arrives {_fmt_date(eta_date)}"
        return status, ""

    return "AT SEA (destination unknown)", ""


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Container Tracker", page_icon="🚢", layout="centered")
st.title("🚢 Container Tracker")
st.caption("Upload your Excel file to track shipments via AIS. Original columns are never modified.")

# ── File upload ───────────────────────────────────────────────────────────────

uploaded = st.file_uploader("Select your Excel file (.xlsx)", type=["xlsx"])

if not uploaded:
    st.stop()

if not st.button("Track Containers", type="primary", use_container_width=True):
    st.stop()

# ── Processing ────────────────────────────────────────────────────────────────

wb = openpyxl.load_workbook(uploaded)
ws = wb.active
total = skipped = 0

for col, label in [
    (config.COL_MMSI,        "MMSI"),
    (config.COL_UPDATED_ETA, "UPDATED ETA"),
    (config.COL_ACTUAL_ARR,  "ACTUAL ARRIVAL"),
]:
    if not ws.cell(row=1, column=col).value:
        ws.cell(row=1, column=col).value = label

tracker_ais.clear_run_cache()

with st.status("Tracking containers…", expanded=True) as status_box:
    for row_idx in range(config.HEADER_ROWS + 1, ws.max_row + 1):
        carrier      = ws.cell(row=row_idx, column=config.COL_CARRIER).value
        container_id = ws.cell(row=row_idx, column=config.COL_CONTAINER).value

        if not carrier and not container_id:
            break
        if not carrier or not container_id:
            continue

        carrier      = str(carrier).strip()
        container_id = str(container_id).strip().upper()
        total += 1

        # skip if manually delivered
        delivered = ws.cell(row=row_idx, column=config.COL_ACTUAL_DELIVERY).value
        if delivered:
            st.write(f"**{container_id}** — manually delivered, skipped")
            skipped += 1
            continue

        # skip if already marked arrived
        current_loc = str(ws.cell(row=row_idx, column=config.COL_LOCATION).value or "")
        if current_loc.startswith("ARRIVED"):
            st.write(f"**{container_id}** — already arrived, skipped")
            skipped += 1
            continue

        st.write(f"**{container_id}** ({carrier})")

        vessel_raw   = ws.cell(row=row_idx, column=config.COL_VESSEL).value
        mmsi_cell    = ws.cell(row=row_idx, column=config.COL_MMSI)
        eta_cell     = ws.cell(row=row_idx, column=config.COL_UPDATED_ETA)
        actual_cell  = ws.cell(row=row_idx, column=config.COL_ACTUAL_ARR)
        loc_cell     = ws.cell(row=row_idx, column=config.COL_LOCATION)
        etd_cell     = ws.cell(row=row_idx, column=config.COL_ETD)
        booked_eta   = ws.cell(row=row_idx, column=config.COL_ETA)

        if not vessel_raw:
            st.write("  ↳ no vessel name")
            continue

        mmsi, err = tracker_ais.resolve_mmsi(str(vessel_raw), mmsi_cell.value)
        if not mmsi:
            st.write(f"  ↳ AIS: {err}")
            continue

        mmsi_cell.value = mmsi
        ais_data = tracker_ais.get_vessel_status(mmsi)

        if ais_data.get("error"):
            st.write(f"  ↳ AIS error: {ais_data['error']}")
            continue

        situation, us_eta = _build_situation(ais_data)
        loc_cell.value  = situation
        eta_cell.value  = us_eta

        if situation.startswith("ARRIVED") and us_eta:
            actual_cell.value = us_eta
            etd  = _fmt_date(_eta_date(str(etd_cell.value or "")))
            exp  = _fmt_date(_eta_date(str(booked_eta.value or "")))
            act  = _fmt_date(us_eta)
            st.write(f"  ↳ {situation} | ETD {etd} | Expected {exp} | Actual {act}")
        else:
            st.write(f"  ↳ {situation}")

    status_box.update(
        label=f"Done — {total} containers processed, {skipped} skipped",
        state="complete",
    )

# ── Download ──────────────────────────────────────────────────────────────────

output = io.BytesIO()
wb.save(output)
output.seek(0)

timestamp = datetime.now().strftime("%Y-%m-%d %H-%M")
orig_name = uploaded.name.replace(".xlsx", "")
out_name  = f"{orig_name} - Processed {timestamp}.xlsx"

st.success(f"✓ {total} containers processed, {skipped} skipped")
st.download_button(
    label="⬇️ Download processed file",
    data=output,
    file_name=out_name,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
