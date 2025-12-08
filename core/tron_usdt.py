import csv
import json
import os
from datetime import date, datetime
from pathlib import Path

import requests

from core.gsheets_client import write_usdt_rows_to_sheet
from core.wallets import WALLET_LABELS, shorten_address


TRC20_USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


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
            "trc20Id": TRC20_USDT_CONTRACT,
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


def normalize_usdt_trc20_transfers(raw_transfers: list[dict], my_address: str) -> list[dict]:
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
                "INFO": f"Wallet: {shorten_address(beneficiary)}",
                "SYMB": "USDT",
                "QTY": "",
                "RATE": "",
                "AMOUNT": signed_amount,
                "ACC": f"USDT, {my_address[-4:]}",
            }
        )

    return normalized


def get_normalized_trc_usdt_rows(
    address: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[dict]:
    """
    Fetch and normalize TRC20 USDT transfers for the given address, optionally filtering by date range.
    """
    raw_transfers = fetch_usdt_trc20_transfers(address, limit_per_page=50, max_pages=100)
    rows = normalize_usdt_trc20_transfers(raw_transfers, address)

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


def export_trc_usdt_to_csv(
    address: str,
    output_path: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> None:
    """
    Fetch, normalize, optionally filter, and write TRC20 USDT transfers for the given address to a CSV file.
    """
    rows = get_normalized_trc_usdt_rows(address, from_date=from_date, to_date=to_date)

    fieldnames = ["DATE", "CAT", "INFO", "SYMB", "QTY", "RATE", "AMOUNT", "ACC"]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


def export_trc_usdt_to_sheet(
    address: str,
    label_suffix: str,
    spreadsheet_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> None:
    """
    Fetch normalized USDT rows for the given address and write them into a Google Sheet worksheet named 'USDT_<label_suffix>_RAW'.
    """
    rows = get_normalized_trc_usdt_rows(address, from_date=from_date, to_date=to_date)
    worksheet_name = f"USDT_{label_suffix}_RAW"
    write_usdt_rows_to_sheet(spreadsheet_id, worksheet_name, rows)
    print(f"Wrote {len(rows)} rows to Google Sheet tab {worksheet_name}")
