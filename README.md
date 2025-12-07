# WalletOS_USDT
Small Python tool to fetch and normalize TRON USDT (TRC20) wallet activity into a clean CSV format for finance sheets.

## Features
- Fetch TRC20 USDT transfers from TronScan for a given wallet.
- Normalize raw transfers into columns: DATE, CAT, INFO, SYMB, QTY, RATE, AMOUNT, ACC.
- Use a wallet directory CSV (`data/wallet_directory.csv`) to map addresses to human labels (e.g., BinanceRL, Bluewave-1).
- Export CSV for a single wallet by address or label.
- Export CSVs for all internal wallets in one command (`my_wallets`).
- Optional date filters: `--from-date` and `--to-date` (YYYY-MM-DD).
- Optional Google Sheets export: write normalized data into worksheet tabs (USDT_<label>_RAW) in a target spreadsheet.

## Project structure
- `tronscan_usdt.py` – main script with fetch/normalize/export and CLI.
- `data/wallet_directory.csv` – wallet directory (address,label,owner_type).
- `data/*.csv` – generated exports per wallet (e.g., `usdt_BinanceRL.csv`).
- `pyproject.toml` – Poetry configuration.

## Installation
Prereqs: Python and Poetry installed.
```
cd ~/dev/dev
poetry install
```
Uses the TronScan online API; no private keys required.

## Google Sheets integration (optional)
To push normalized data directly into a Google Sheet, you need to set up a service account and share a spreadsheet with it:
1. In Google Cloud Console, create a project (for example "WalletOS") and enable the **Google Sheets API**.
2. Create a **service account** for that project and generate a JSON key file.
3. Save the JSON key file into this project at `credentials/gsheets_service_account.json`. The `credentials/` folder is ignored by git so the key is not committed.
4. Open the Google Sheet you want to use and **share** it with the service account email (Editor access).
5. Grab the spreadsheet ID from the Sheet URL (the long string between `/d/` and `/edit`) and pass it to the CLI with the `--sheet-id` option.

## Usage
- Single wallet by label:
  ```
  poetry run python tronscan_usdt.py BinanceRL
  ```
- Single wallet by address:
  ```
  poetry run python tronscan_usdt.py TWo82CEE5jjyjF76f9ACQ6tkBMRP26pDWo
  ```
- All internal wallets:
  ```
  poetry run python tronscan_usdt.py my_wallets
  ```
- Date filters:
  ```
  poetry run python tronscan_usdt.py BinanceRL --from-date 2025-10-01
  poetry run python tronscan_usdt.py my_wallets --from-date 2025-10-01 --to-date 2025-12-31
  ```
- Single wallet -> CSV + Google Sheet tab:
  ```bash
  poetry run python tronscan_usdt.py BinanceRL \
    --from-date 2025-10-01 \
    --sheet-id <SPREADSHEET_ID>
  ```
- All internal wallets -> CSVs + Google Sheet tabs:
  ```bash
  poetry run python tronscan_usdt.py my_wallets \
    --from-date 2025-10-01 \
    --sheet-id <SPREADSHEET_ID>
  ```
  For each wallet, the script writes to a worksheet named `USDT_<label>_RAW` (or uses a suffix based on the address if no label exists).

## Editing the wallet directory
- Edit `data/wallet_directory.csv` in any spreadsheet app.
- Columns: `address`, `label`, `owner_type`.
- `owner_type` = "internal" for your own wallets (Bluewave / BinanceRL), "client" for external wallets.
- Adding a row for a new wallet automatically populates the CAT column for that address in future exports.

## Notes / future ideas
- Google Sheets integration (write directly to RAW tabs).
- Incremental sync using last processed date.
- Package a simpler command for non-technical users (secretary).
