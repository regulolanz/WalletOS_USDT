#!/usr/bin/env bash
# Usage:
#   ./scripts/sync_tron_usdt_my_wallets.sh 2025-12-01
#
# This will:
#   - sync all internal wallets (my_wallets)
#   - from the given FROM_DATE (YYYY-MM-DD)
#   - update local CSVs (outputs/tron_usdt/)
#   - update Google Sheets RAW tabs (USDT_<label>_RAW)

set -euo pipefail

FROM_DATE="${1:-}"

if [ -z "$FROM_DATE" ]; then
  echo "Usage: $0 FROM_DATE (YYYY-MM-DD)"
  exit 1
fi

# Base directory of this repo = parent of the scripts folder
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# WalletOS Google Sheet ID
SHEET_ID="1Jad2PoONt--M-_y3RS6T_eqJwBD9uYpI--BWEE3hWfU"

cd "$BASE_DIR"

echo "Syncing internal wallets from ${FROM_DATE} to Google Sheet ${SHEET_ID}..."
poetry run python apps/tron_usdt_cli.py my_wallets \
  --from-date "${FROM_DATE}" \
  --sheet-id "${SHEET_ID}"
