import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tron_usdt import (
    export_trc_usdt_to_csv,
    export_trc_usdt_to_sheet,
)
from core.wallets import (
    WALLET_LABELS,
    get_internal_wallets,
    resolve_wallet_identifier,
)


def main():
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
            output_path = f"outputs/trc_usdt/trc_usdt_{suffix}.csv"
            print(f"Exporting USDT transfers for internal wallet {suffix} -> {addr} into {output_path}")
            export_trc_usdt_to_csv(addr, output_path, from_date=args.from_date, to_date=args.to_date)
            if args.sheet_id:
                export_trc_usdt_to_sheet(
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
        output_path = f"outputs/trc_usdt/trc_usdt_{suffix}.csv"

    print(f"Exporting USDT transfers for {args.wallet} -> {address} into {output_path}")
    export_trc_usdt_to_csv(address, output_path, from_date=args.from_date, to_date=args.to_date)
    if args.sheet_id:
        export_trc_usdt_to_sheet(
            address,
            suffix,
            args.sheet_id,
            from_date=args.from_date,
            to_date=args.to_date,
        )


if __name__ == "__main__":
    main()
