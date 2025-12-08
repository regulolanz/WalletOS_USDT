import csv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
WALLET_DIR_CSV = ROOT_DIR / "resources" / "wallet_directory.csv"


def _load_wallet_directory():
    """
    Load wallet_directory.csv and return:
    - labels: dict[address, label]
    - owner_types: dict[address, owner_type]
    """
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


def shorten_address(addr: str) -> str:
    """
    Return a shortened address like 'Txxx...yyyy' for display.
    """
    if not addr:
        return ""
    if len(addr) <= 8:
        return addr
    return f"{addr[:4]}...{addr[-4:]}"


def resolve_wallet_identifier(identifier: str) -> str:
    """
    Given either a full address or a label, return the resolved address.

    - If identifier matches a known address (key in WALLET_LABELS), return it.
    - Else if it matches a known label (key in LABEL_TO_ADDRESS), return the address.
    - Otherwise, raise ValueError listing available labels.
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
    Return a list of (address, label_suffix) for wallets marked as internal.

    label_suffix is used to build filenames / sheet tab names:
    - prefer label if it exists; otherwise use last 6 chars of the address.
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
