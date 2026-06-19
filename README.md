# Container Tracker

A web tool that reads your shipment Excel files and automatically looks up each vessel's current position using AIS (ship tracking satellites). It writes the result back into your file so you always know where your containers are.

**Live app:** https://container-track-t4tfct6x2d8hx4fwlxbyft.streamlit.app/

---

## What it does

- Reads vessel names from your Excel file
- Looks up each vessel on the AIS network in real time
- Writes the current status into the **Container Location** column
- Caches the vessel's MMSI number so future lookups are faster
- Saves the result as a new file — your original is never modified
- Works across all sheets in the workbook

---

## Excel file requirements

The tool finds columns by reading the **header row** (row 1), so the exact column order does not matter. The following column headers must exist somewhere in row 1:

| Header (exact text) | Purpose |
|---|---|
| `VESSEL / VOYAGE NAME` | Vessel name used for AIS lookup |
| `CONTAINER` or `CONTAINER ID` | Container number (used for display only) |
| `CONTAINER LOCATION` | **Where the tool writes the status** |
| `Actual Delivery Date` | If this cell has a value the row is skipped |

These headers are optional but improve the output:

| Header | Purpose |
|---|---|
| `ETD` | Shown in arrived log (departure date) |
| `ETA` | Shown in arrived log (expected arrival) |
| `CARRIER` or `FORWARDER / LINE` | Shown next to container ID in the log |

The tool also adds three new columns on the first run (if they do not already exist):

| Column added | Content |
|---|---|
| `MMSI` | Vessel identifier — cached so future runs are faster |
| `UPDATED ETA` | Estimated arrival date at a US port |
| `ACTUAL ARRIVAL` | Date the vessel arrived (filled once ARRIVED status is detected) |

---

## Status values written to Container Location

| Status | Meaning |
|---|---|
| `ARRIVED — Port Name` | Vessel is at a US port |
| `IN TRANSIT → Port Name \| ETA DD Mon YYYY` | Heading directly to the US |
| `AT PORT: Stop → Next: US Port \| US ETA DD Mon YYYY` | Currently at a stopover, next stop is the US |
| `AT PORT: Port Name (en route to US)` | Stopped somewhere, US arrival date unknown |
| `AT SEA → Port Name \| Arrives DD Mon YYYY` | Underway to a non-US port |
| `AT SEA (destination unknown)` | No destination broadcast |

Rows already showing `ARRIVED` are skipped in future runs. Rows with a value in **Actual Delivery Date** are also skipped.

---

## How to use

1. Go to the live app link above
2. Click **TR** in the top-right corner to switch to Turkish if needed
3. Upload your `.xlsx` file
4. Click **Track Containers**
5. Wait for the tool to check each vessel (this takes a moment per row)
6. Click **Download processed file** to save the result

The downloaded file is named `[original name] - Processed YYYY-MM-DD HH-MM.xlsx`.

---

## Running locally (Mac)

```bash
git clone https://github.com/oak-gpu/container-track.git
cd container-track
pip install -r requirements.txt
streamlit run streamlit_app.py
```

You will need a MyShipTracking API key. Create a file at `.streamlit/secrets.toml`:

```toml
MYSHIPTRACKING_API_KEY = "your_key_here"
```

API keys can be obtained at [myshiptracking.com](https://www.myshiptracking.com).

---

## Hosting your own copy on Streamlit Cloud

1. Fork this repository to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. In **App settings → Secrets**, add:
   ```toml
   MYSHIPTRACKING_API_KEY = "your_key_here"
   ```
4. Deploy — the app will be available at a public URL

---

## Notes

- Only `.xlsx` files are supported (not `.xls` or `.csv`)
- Sheets that do not have the required headers are silently skipped
- The AIS network does not cover all vessels at all times — some ships may show "vessel not found in AIS coverage"
- MSC carrier is not supported via API; AIS tracking still works as long as the vessel name is in the file
