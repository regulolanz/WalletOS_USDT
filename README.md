# WalletOS_USDT
Small Python tool to fetch and normalize TRON USDT (TRC20) wallet activity into a clean CSV format for finance sheets.

## Features
- Fetch TRC20 USDT transfers from TronScan for a given wallet.
- Normalize raw transfers into columns: DATE, CAT, INFO, SYMB, QTY, RATE, AMOUNT, ACC.
- Use a wallet directory CSV (`data/wallet_directory.csv`) to map addresses to human labels (e.g., BinanceRL, Bluewave-1).
- Export CSV for a single wallet by address or label.
- Export CSVs for all internal wallets in one command (`my_wallets`).
- Optional date filters: `--from-date` and `--to-date` (YYYY-MM-DD).

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

## Editing the wallet directory
- Edit `data/wallet_directory.csv` in any spreadsheet app.
- Columns: `address`, `label`, `owner_type`.
- `owner_type` = "internal" for your own wallets (Bluewave / BinanceRL), "client" for external wallets.
- Adding a row for a new wallet automatically populates the CAT column for that address in future exports.

## Notes / future ideas
- Google Sheets integration (write directly to RAW tabs).
- Incremental sync using last processed date.
- Package a simpler command for non-technical users (secretary).
