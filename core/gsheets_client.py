import gspread
from gspread.exceptions import APIError
from google.oauth2 import service_account
from pathlib import Path


def get_sheets_client() -> gspread.Client:
    """
    Return an authenticated gspread Client using the service account
    JSON file located at credentials/gsheets_service_account.json relative to this file.
    """
    root_dir = Path(__file__).resolve().parent.parent
    cred_path = root_dir / "credentials" / "gsheets_service_account.json"
    if not cred_path.exists():
        raise RuntimeError(
            f"Google Sheets credentials not found at {cred_path}. "
            "Make sure you have placed your service account JSON there."
        )
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file(
        str(cred_path),
        scopes=scopes,
    )
    return gspread.authorize(creds)


def write_usdt_rows_to_sheet(
    spreadsheet_id: str,
    worksheet_name: str,
    rows: list[dict],
) -> None:
    """
    Write normalized USDT rows into the given Google Sheet worksheet.

    - If the worksheet does not exist, create it.
    - Clear any existing content in the worksheet.
    - Write a header row using the keys of the first dict in `rows`,
      in the order: ["DATE","CAT","INFO","SYMB","QTY","RATE","AMOUNT","ACC"].
    - Then write one row per dict.
    - If `rows` is empty, still ensure that the worksheet exists and
      contains just the header row.
    """
    client = get_sheets_client()
    sh = client.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=10)

    headers = ["DATE", "CAT", "INFO", "SYMB", "QTY", "RATE", "AMOUNT", "ACC"]
    values = [headers]
    for row in rows:
        values.append([row.get(h, "") for h in headers])

    try:
        ws.clear()
        ws.update("A1", values)
    except APIError as e:
        # Do not crash the whole sync; just log a warning.
        print(f"[WARN] Google Sheets APIError updating {worksheet_name}: {e}")
