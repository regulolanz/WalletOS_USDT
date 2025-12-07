import argparse
import csv
import json
import os
from datetime import datetime, date
from pathlib import Path

import requests

from gsheets_client import write_usdt_rows_to_sheet


USDT_TRC20_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
ROOT_DIR = Path(__file__).resolve().parent
WALLET_DIR_CSV = ROOT_DIR / "data" / "wallet_directory.csv"


def _load_wallet_directory():
    labels: dict[str, str] = {}
    owner_types: dict[str, str] = {}
    try:
        with WALLET_DIR_CSV.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                addr = (row.get("address") or "").strip()
                if not addr:
                    continue
                labels[addr] = (row.get("label") or "").strip()
                owner_types[addr] = (row.get("owner_type") or "").strip()
    except FileNotFoundError:
        # If the file does not exist, just leave both dicts empty.
        pass
    return labels, owner_types


WALLET_LABELS, WALLET_OWNER_TYPES = _load_wallet_directory()
LABEL_TO_ADDRESS: dict[str, str] = {}
for addr, label in WALLET_LABELS.items():
    if not label:
        continue
    # If a label appears multiple times, keep the first address for now.
    LABEL_TO_ADDRESS.setdefault(label, addr)


def resolve_wallet_identifier(identifier: str) -> str:
    """
    Given either a full address or a label, return the resolved address.

    - If `identifier` matches a key in WALLET_LABELS, treat it as an address.
    - Else if it matches a key in LABEL_TO_ADDRESS, treat it as a label and return the corresponding address.
    - Otherwise, raise a ValueError listing available labels.
    """
    ident = identifier.strip()
    if ident in WALLET_LABELS:
        return ident
    if ident in LABEL_TO_ADDRESS:
        return LABEL_TO_ADDRESS[ident]
    available = ", ".join(sorted(LABEL_TO_ADDRESS.keys()))
    raise ValueError(f"Unknown wallet identifier '{identifier}'. Known labels: {available}")


def get_internal_wallets():
    """
    Return a list of (address, label_suffix) for wallets marked as internal in WALLET_OWNER_TYPES.

    label_suffix is used for naming the CSV file: if the wallet has a label, use that; otherwise use the last 6 characters of the address.
    """
    internal: list[tuple[str, str]] = []
    for addr, owner_type in WALLET_OWNER_TYPES.items():
        if not owner_type:
            continue
        if owner_type.lower() != "internal":
            continue
        label = WALLET_LABELS.get(addr, "")
        suffix = label if label else addr[-6:]
        internal.append((addr, suffix))
    return internal


def _shorten_address(addr: str) -> str:
    """Return a compact representation of an address (first 4 chars, ellipsis, last 4 chars)."""
    return f"{addr[:4]}...{addr[-4:]}"


def fetch_usdt_trc20_transfers(address: str, limit_per_page: int = 200, max_pages: int = 100) -> list[dict]:
    """
    Fetch TRC20 USDT transfer events for the given address from Tronscan.
    Retrieves paginated results up to the configured page and per-page limits.
    Returns a list of raw transfer records as dictionaries in the format provided by the API.
    """
    api_key = os.getenv("TRONSCAN_API_KEY")
    headers: dict | None = {"TRON-PRO-API-KEY": api_key} if api_key else None
    if headers is None:
        # Without an API key, Tronscan rate limits may apply.
        headers = None

    base_url = "https://apilist.tronscanapi.com/api/transfer/trc20"
    transfers: list[dict] = []
    start = 0

    for _ in range(max_pages):
        params = {
            "address": address,
            "trc20Id": USDT_TRC20_CONTRACT,
            "start": start,
            "limit": limit_per_page,
            "direction": 0,
            "reverse": "true",
            "db_version": 1,
        }
        response = requests.get(base_url, params=params, headers=headers, timeout=15)
        if response.status_code != 200:
            raise RuntimeError(f"TronScan API HTTP {response.status_code}: {response.text[:200]}")

        try:
            payload = response.json()
        except json.JSONDecodeError as e:
            body = response.text or ""
            if not body.strip() and response.status_code == 200:
                # Empty body on 200 -> treat as no more data and stop paging.
                break
            raise RuntimeError(
                f"TronScan API returned non-JSON response (status {response.status_code}): "
                f"{body[:200]}"
            ) from e
        page_transfers = payload.get("token_transfers") or payload.get("data") or []
        if not page_transfers:
            break

        transfers.extend(page_transfers)
        start += limit_per_page

    return transfers


def normalize_usdt_transfers(raw_transfers: list[dict], my_address: str) -> list[dict]:
    """
    Normalize raw TRC20 USDT transfer records.
    Converts API-shaped transfers into a consistent structure with direction, amount, counterparty, and timestamps.
    Uses my_address to determine whether each transfer is inbound or outbound.
    """
    normalized: list[dict] = []

    for transfer in raw_transfers:
        amount_raw = int(transfer["amount"])
        decimals = int(transfer["decimals"])
        amount_usdt = amount_raw / (10**decimals)

        from_addr = transfer["from"]
        to_addr = transfer["to"]

        if to_addr == my_address:
            beneficiary = from_addr
            signed_amount = amount_usdt
        elif from_addr == my_address:
            beneficiary = to_addr
            signed_amount = -amount_usdt
        else:
            # Not involving this wallet; skip.
            continue

        ts_ms = int(transfer["block_timestamp"])
        dt_str = datetime.utcfromtimestamp(ts_ms / 1000).strftime("%m-%d-%Y")
        label = WALLET_LABELS.get(beneficiary, "")

        normalized.append(
            {
                "DATE": dt_str,
                "CAT": label,
                "INFO": f"Wallet: {_shorten_address(beneficiary)}",
                "SYMB": "USDT",
                "QTY": "",
                "RATE": "",
                "AMOUNT": signed_amount,
                "ACC": f"USDT, {my_address[-4:]}",
            }
        )

    return normalized


def get_normalized_usdt_rows(
    address: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[dict]:
    """
    Fetch and normalize TRC20 USDT transfers for the given address, optionally filtering by date range.
    """
    raw_transfers = fetch_usdt_trc20_transfers(address, limit_per_page=50, max_pages=100)
    rows = normalize_usdt_transfers(raw_transfers, address)

    def _parse_cli_date(s: str) -> date:
        return datetime.strptime(s, "%Y-%m-%d").date()

    def _parse_row_date(s: str) -> date:
        return datetime.strptime(s, "%m-%d-%Y").date()

    from_d = _parse_cli_date(from_date) if from_date else None
    to_d = _parse_cli_date(to_date) if to_date else None

    if from_d or to_d:
        filtered = []
        for row in rows:
            row_d = _parse_row_date(row["DATE"])
            if from_d and row_d < from_d:
                continue
            if to_d and row_d > to_d:
                continue
            filtered.append(row)
        rows = filtered

    return rows


def export_usdt_transfers_to_csv(
    address: str,
    output_path: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> None:
    """
    Fetch, normalize, optionally filter, and write TRC20 USDT transfers for the given address to a CSV file.
    """
    rows = get_normalized_usdt_rows(address, from_date=from_date, to_date=to_date)

    fieldnames = ["DATE", "CAT", "INFO", "SYMB", "QTY", "RATE", "AMOUNT", "ACC"]

    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


def export_usdt_transfers_to_sheet(
    address: str,
    label_suffix: str,
    spreadsheet_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> None:
    """
    Fetch normalized USDT rows for the given address and write them into a Google Sheet worksheet named 'USDT_<label_suffix>_RAW'.
    """
    rows = get_normalized_usdt_rows(address, from_date=from_date, to_date=to_date)
    worksheet_name = f"USDT_{label_suffix}_RAW"
    write_usdt_rows_to_sheet(spreadsheet_id, worksheet_name, rows)
    print(f"Wrote {len(rows)} rows to Google Sheet tab {worksheet_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export TRON USDT transfers for a wallet.")
    parser.add_argument(
        "wallet",
        help="Wallet identifier: either a full TRON address or a known label from wallet_directory.csv (e.g. 'BinanceRL').",
    )
    parser.add_argument(
        "output",
        nargs="?",
        help="Optional output CSV path. If not provided, use data/usdt_<label_or_suffix>.csv",
    )
    parser.add_argument(
        "--from-date",
        help="Only include transfers on or after this date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--to-date",
        help="Only include transfers on or before this date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--sheet-id",
        help="Optional Google Sheets spreadsheet ID. If provided, normalized rows will also be written into worksheet tabs (USDT_<label>_RAW).",
    )
    args = parser.parse_args()

    ident = args.wallet.strip()
    if ident.lower() == "my_wallets":
        # Ignore args.output in this mode.
        wallets = get_internal_wallets()
        if not wallets:
            print("No internal wallets found in wallet_directory.csv.")
            raise SystemExit(1)

        for addr, suffix in wallets:
            output_path = f"data/usdt_{suffix}.csv"
            print(f"Exporting USDT transfers for internal wallet {suffix} -> {addr} into {output_path}")
            export_usdt_transfers_to_csv(addr, output_path, from_date=args.from_date, to_date=args.to_date)
            if args.sheet_id:
                export_usdt_transfers_to_sheet(
                    addr,
                    suffix,
                    args.sheet_id,
                    from_date=args.from_date,
                    to_date=args.to_date,
                )
        raise SystemExit(0)

    try:
        address = resolve_wallet_identifier(ident)
    except ValueError as e:
        print(e)
        raise SystemExit(1)

    # Decide default output path if not provided:
    if args.output:
        output_path = args.output
    else:
        # Prefer label if we have one, otherwise use last 6 chars of the address.
        label = WALLET_LABELS.get(address, "")
        if label:
            suffix = label
        else:
            suffix = address[-6:]
        output_path = f"data/usdt_{suffix}.csv"

    print(f"Exporting USDT transfers for {args.wallet} -> {address} into {output_path}")
    export_usdt_transfers_to_csv(address, output_path, from_date=args.from_date, to_date=args.to_date)
    if args.sheet_id:
        export_usdt_transfers_to_sheet(
            address,
            suffix,
            args.sheet_id,
            from_date=args.from_date,
            to_date=args.to_date,
        )
