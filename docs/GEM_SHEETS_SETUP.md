# GeM Tender Tracker — Automated Daily Sheet Updater

Automatically discovers new GeM bids matching Nikom's business categories and
appends them to your Google Sheets tracker every day at 9:00 AM IST.

## How It Works

1. **GeM Scraper** (`src/adapters/gem.py`) searches `bidplus.gem.gov.in` across 31
   keyword categories (UPS, chiller, HVAC, DG set, fire detection, etc.)
2. **Classifier** (`src/classifier/gem_classifier.py`) auto-assigns each bid to one of
   your 8 groups (Best fit, Quick win, HPC, HVAC O&M, etc.)
3. **Sheets Service** (`src/services/sheets_service.py`) deduplicates against your
   existing rows and appends only new bids
4. **GitHub Actions** (`.github/workflows/daily-gem-update.yml`) triggers this at
   9:00 AM IST every day — zero manual intervention

---

## Setup (One-Time, ~10 Minutes)

### Step 1: Create a Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Nikom Tender Bot") or use an existing one
3. Enable the **Google Sheets API**:
   - Navigate to **APIs & Services → Library**
   - Search "Google Sheets API" → click **Enable**
4. Create a Service Account:
   - Go to **APIs & Services → Credentials**
   - Click **Create Credentials → Service Account**
   - Name it `tender-bot` → click **Create and Continue**
   - Skip the optional roles → click **Done**
5. Create a JSON key:
   - Click the service account you just created
   - Go to **Keys** tab → **Add Key → Create New Key → JSON**
   - A `.json` file downloads — **keep this safe, you'll need its contents**

### Step 2: Share Your Spreadsheet with the Bot

1. Open the downloaded JSON file and copy the `client_email` value
   (looks like `tender-bot@your-project.iam.gserviceaccount.com`)
2. Open your Google Sheet
3. Click **Share** → paste the service account email → give **Editor** access
4. Click **Send** (ignore the "not a Google account" warning)

### Step 3: Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these two secrets:

| Secret Name | Value |
|---|---|
| `GOOGLE_SHEETS_CREDENTIALS` | The **entire contents** of the downloaded JSON key file (paste the full JSON) |
| `PROXY_URL` | Your Indian HTTP proxy, e.g. `http://34.100.244.79:80` |

### Step 4: Push and Enable

```bash
git push origin claude/upbeat-turing-kzea44
```

The workflow runs automatically at 9:00 AM IST every day. You can also
trigger it manually: **Actions → Daily GeM Tender Sheet Update → Run workflow**

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set credentials (option A: env var with JSON content)
export GOOGLE_SHEETS_CREDENTIALS='{"type":"service_account",...}'
export PROXY_URL=http://34.100.244.79:80

# Or (option B: path to the JSON key file)
export GOOGLE_SHEETS_CREDENTIALS_PATH=/path/to/key.json

# Full sync — discover, classify, deduplicate, append, update "Days left"
python gem_sheets_sync.py

# Dry run — see what would be added without writing
python gem_sheets_sync.py --dry-run

# Only recalculate "Days left" column
python gem_sheets_sync.py --days-only

# Also remove bids past their closing date
python gem_sheets_sync.py --remove-expired
```

---

## What Gets Added to the Sheet

Each new row auto-fills these columns:

| Column | Source |
|---|---|
| # | Auto-incremented |
| GeM bid number | From GeM API (e.g. GEM/2026/B/8197254) |
| Scope of work | Bid title/category from GeM |
| Closing date & time | From GeM API |
| Bid document (link) | `bidplus.gem.gov.in/showbidDocument/{id}` |
| Days left | Calculated daily |
| Buyer (Ministry / Dept) | Ministry/department from GeM |
| Group | Auto-classified (1–8) |
| Nikom role | Auto-assigned (Direct bidder / Partner) |
| Eligibility | Defaults to "Not started" |
| Est. value / EMD | Filled if available in GeM listing |
| Remarks | "Auto-discovered DD-Mon-YYYY" |

**You still review** Eligibility, Past experience, Min. turnover, and Remarks manually.

---

## Proxy Notes

Indian government portals (`eprocure.gov.in`, `gem.gov.in`) block non-Indian IPs.
The HTTP proxy at `34.100.244.79:80` routes traffic through Google Cloud Mumbai.

If you need a more reliable proxy, consider:
- A VPS in India (Google Cloud Mumbai, AWS ap-south-1)
- A residential proxy service with Indian IPs
- Running the script directly on an Indian server (skip the proxy)
