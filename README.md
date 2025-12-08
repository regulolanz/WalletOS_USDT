# WalletOS

WalletOS is my personal "wallet operating system": a collection of tools to fetch, normalize and sync on-chain activity into clean data for analysis and finance dashboards.

The first module implemented is **USDT on TRON (TRC20)** using TronScan. Next modules will include **USDT on Ethereum (ERC20)** via Etherscan and other reporting apps.

---

## Current features (v1 – TRC USDT)

- **TRON USDT ingestion**
  - Fetch TRC20 USDT transfers for a given TRON address using the TronScan API.
  - Normalize raw transfers into a standard schema:

    `DATE, CAT, INFO, SYMB, QTY, RATE, AMOUNT, ACC`

- **Wallet directory / client master**
  - Use `resources/wallet_directory.csv` as a mini "core banking" file:
    - Columns: `address, label, owner_type`
    - `owner_type = internal` → my own wallets (Bluewave, Binance_RL, etc.).
    - `owner_type = client` → external clients / counterparties.
  - `CAT` is filled from this file using the beneficiary's label.
  - Internal wallets are included automatically in the `my_wallets` flow.

- **CSV exports**
  - Per wallet CSVs written to:

    outputs/trc_usdt/trc_usdt_<LABEL>.csv

  - e.g. `trc_usdt_Binance_RL.csv`, `trc_usdt_Bluewave_8.csv`.

- **Google Sheets integration**
  - Optional Google Sheets export:
    - Write normalized data into worksheet tabs:

      USDT_<LABEL>_RAW

      (for example `USDT_Binance_RL_RAW`, `USDT_Bluewave_1_RAW`).
  - Designed so Google Sheets can use these tabs as RAW sources for higher-level dashboards.

- **Bulk sync for internal wallets**
  - One command to sync **all internal wallets** from a given date:
    - Updates CSVs.
    - Updates Google Sheets RAW tabs (if configured).

---

## Repository layout

WalletOS/
  core/
    __init__.py
    gsheets_client.py        # Google Sheets client using service account
  credentials/               # private files (ignored by git)
    gsheets_service_account.json
    (later) etherscan_api_key.txt
  outputs/
    trc_usdt/                # generated TRC20 USDT CSVs
      trc_usdt_Binance_RL.csv
      trc_usdt_Bluewave_1.csv
      ...
  resources/
    wallet_directory.csv     # wallet directory / client master (NOT tracked in git)
  scripts/
    sync_tron_usdt_my_wallets.sh  # shell helper for bulk sync of internal wallets
  tronscan_usdt.py           # current Tron USDT CLI & glue
  pyproject.toml             # Poetry project configuration
  poetry.lock                # locked dependency versions
  README.md
  .gitignore

Note: credentials/ and resources/wallet_directory.csv are intentionally ignored by git and must be provided manually on each machine.

---

## Requirements

- Python 3.12+ (or compatible 3.x).
- Poetry installed on the system.
- A TronScan-compatible TRON address with USDT TRC20 activity.
- (Optional) A Google Cloud service account for Google Sheets.

---

## Setup

### 1. Clone the repo

cd ~/dev
git clone https://github.com/regulolanz/WalletOS.git
cd WalletOS

### 2. Install Python dependencies

poetry install

This reads pyproject.toml and poetry.lock and installs the exact dependency versions.

### 3. Configure credentials

#### 3.1. Google Sheets service account

1. In Google Cloud Console:
   - Create a project (e.g. "WalletOS").
   - Enable the Google Sheets API.
   - Create a service account and download its JSON key.

2. Place the JSON file in:

credentials/gsheets_service_account.json

3. Open the target Google Sheet (e.g. "WalletOS") and share it with the service account email (Editor access).

4. Copy the spreadsheet ID from the URL (the long string between /d/ and /edit).

#### 3.2. Wallet directory

The wallet directory lives at:

resources/wallet_directory.csv

- This file is not tracked in git.
- It can be edited in any spreadsheet app and exported as CSV.

Expected columns:

address,label,owner_type
TWo82CEE5jjyjF76f9ACQ6tkBMRP26pDWo,Binance_RL,internal
TRrufu5JkXDj6aUnFwFeBrfKj8TVD95dwh,Bluewave_1,internal
...
TQbyABxsTSWYohhF5QDCFG8UTnVS3Nrra4,ChrisBarkovic_1,client
...

Rules:

- address → full chain address.
- label → short name used in CAT and tab names.
- owner_type:
  - "internal" → included in my_wallets bulk sync.
  - "client" → used for CAT but not included in my_wallets.

---

## Usage (TRC20 USDT on TRON)

Assume the repo root is:

cd ~/dev/WalletOS

and your Google Sheet ID is:

1Jad2PoONt--M-_y3RS6T_eqJwBD9uYpI--BWEE3hWfU

### 1. Single wallet by label → CSV only

poetry run python tronscan_usdt.py Binance_RL --from-date 2025-10-01

- Uses label Binance_RL from wallet_directory.csv.
- Writes:

  outputs/trc_usdt/trc_usdt_Binance_RL.csv

### 2. Single wallet by label → CSV + Google Sheet tab

poetry run python tronscan_usdt.py Binance_RL --from-date 2025-10-01 --sheet-id 1Jad2PoONt--M-_y3RS6T_eqJwBD9uYpI--BWEE3hWfU

- Same CSV as above.
- Also writes to Google Sheets tab:

  USDT_Binance_RL_RAW

### 3. All internal wallets (my_wallets) → CSV only

poetry run python tronscan_usdt.py my_wallets --from-date 2025-10-01

- Reads all rows with owner_type = internal from wallet_directory.csv.
- For each internal wallet, writes:

  outputs/trc_usdt/trc_usdt_<LABEL>.csv

### 4. All internal wallets → CSV + Google Sheets tabs

Using the CLI:

poetry run python tronscan_usdt.py my_wallets --from-date 2025-10-01 --sheet-id 1Jad2PoONt--M-_y3RS6T_eqJwBD9uYpI--BWEE3hWfU

Or, using the convenience shell script:

./scripts/sync_tron_usdt_my_wallets.sh 2025-10-01

The script:

- cd's into the repo root.
- Calls the CLI with the proper --sheet-id.
- Syncs all internal wallets from the given date.

Each internal wallet will update:

- outputs/trc_usdt/trc_usdt_<LABEL>.csv
- USDT_<LABEL>_RAW in the Google Sheet.

---

## Future roadmap (v2+)

WalletOS is meant to grow beyond TRON USDT. Planned modules:

- ETH USDT (ERC20 via Etherscan)
  - New core module: core/eth_usdt.py
  - New CLI: apps/eth_usdt_cli.py
  - Outputs to outputs/erc_usdt/erc_usdt_<LABEL>.csv
  - Sheets tabs: USDT_ETH_<LABEL>_RAW (or similar).

- Shared wallet tools
  - core/wallets.py to encapsulate loading and validating wallet_directory.csv.
  - Better validation and tools to manage multiple chains per client.

- Apps layer
  - apps/ directory for dedicated CLIs:
    - apps/tron_usdt_cli.py
    - apps/eth_usdt_cli.py
  - Existing scripts/ will wrap these apps for non-technical operators.

- Reporting / dashboards
  - Higher-level summary scripts (e.g. daily P&L, per-client flows) built on top of the normalized CSVs/Sheets.

---

## Development notes

- This project uses Poetry for dependency management. Typical dev commands:

cd ~/dev/WalletOS
poetry install                  # first time
poetry run python tronscan_usdt.py --help

- core/ is the place for shared Python logic. For now it contains the Google Sheets client; Tron and future ETH modules will be added here as the project evolves.

- scripts/ is the place for small shell scripts that wrap the CLIs for daily operations.

