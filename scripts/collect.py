#!/usr/bin/env python3
"""
Collect USDT/USDC/ETH balances from TRC20 and ERC20 blockchains.
Runs daily at 00:00 UTC via GitHub Actions.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# Contract addresses
USDT_ERC20 = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
USDC_ERC20 = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDT_TRC20 = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

ETHERSCAN_API_KEY = os.environ.get("ETHERSCAN_API_KEY", "")
TRONGRID_API_KEY = os.environ.get("TRONGRID_API_KEY", "")

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "crypto-balance-tracker/1.0"


# ── TRC20 ──────────────────────────────────────────────────────────────────────

def get_trc_usdt(address: str) -> float | None:
    """Return USDT TRC20 balance via TronGrid (3 retries), fallback to TronScan."""
    headers = {"Accept": "application/json"}
    if TRONGRID_API_KEY:
        headers["TRON-PRO-API-KEY"] = TRONGRID_API_KEY

    # --- TronGrid with retries ---
    for attempt in range(3):
        try:
            url = f"https://api.trongrid.io/v1/accounts/{address}"
            r = SESSION.get(url, headers=headers, timeout=15)
            if r.status_code == 429:
                time.sleep(3 * (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
            accounts = data.get("data", [])
            if accounts:
                for item in accounts[0].get("trc20", []):
                    if USDT_TRC20 in item:
                        return int(item[USDT_TRC20]) / 1_000_000
                return 0.0
            break
        except Exception as e:
            print(f"  TronGrid attempt {attempt+1} error: {e}", file=sys.stderr)
            time.sleep(2)

    # --- TronScan fallback ---
    try:
        url = "https://apilist.tronscanapi.com/api/account"
        r = SESSION.get(url, params={"address": address}, timeout=15)
        r.raise_for_status()
        data = r.json()
        for token in data.get("trc20token_balances", []):
            if token.get("tokenId") == USDT_TRC20:
                return int(token.get("balance", 0)) / 1_000_000
        return 0.0
    except Exception as e:
        print(f"  TRC USDT error for {address}: {e}", file=sys.stderr)
        return None


# ── ERC20 ─────────────────────────────────────────────────────────────────────

def etherscan_get(params: dict) -> dict | None:
    """Call Etherscan API with retry."""
    base = "https://api.etherscan.io/api"
    params["apikey"] = ETHERSCAN_API_KEY
    for attempt in range(3):
        try:
            r = SESSION.get(base, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            if data.get("status") == "1":
                return data
            # Rate limit
            if data.get("result") == "Max rate limit reached":
                time.sleep(2 ** attempt)
                continue
            return data
        except Exception as e:
            print(f"  Etherscan error: {e}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return None


def get_eth_balance(address: str) -> float | None:
    data = etherscan_get({
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest",
    })
    try:
        if data and data.get("status") == "1":
            return int(data["result"]) / 1e18
        if data:
            print(f"  Etherscan ETH error: {data.get('message')} — {data.get('result')}", file=sys.stderr)
    except (ValueError, TypeError) as e:
        print(f"  Etherscan ETH parse error: {e}", file=sys.stderr)
    return None


def get_erc20_balance(address: str, contract: str, decimals: int) -> float | None:
    data = etherscan_get({
        "module": "account",
        "action": "tokenbalance",
        "contractaddress": contract,
        "address": address,
        "tag": "latest",
    })
    try:
        if data and data.get("status") == "1":
            return int(data["result"]) / (10 ** decimals)
        if data:
            print(f"  Etherscan token error: {data.get('message')} — {data.get('result')}", file=sys.stderr)
    except (ValueError, TypeError) as e:
        print(f"  Etherscan token parse error: {e}", file=sys.stderr)
    return None


# ── Main ───────────────────────────────────────────────────────────────────────

def collect():
    root = Path(__file__).parent.parent
    wallets_path = root / "wallets.json"
    history_dir = root / "data" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    with open(wallets_path) as f:
        config = json.load(f)

    wallets = config.get("wallets", [])
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    timestamp = now.isoformat()

    results = {
        "date": date_str,
        "timestamp": timestamp,
        "wallets": []
    }

    for w in wallets:
        label = w.get("label", w.get("id", "unknown"))
        print(f"\nCollecting: {label}")
        entry = {
            "id": w.get("id"),
            "label": label,
            "trc": {},
            "erc": {},
        }

        # TRC20
        trc_addr = w.get("trc", "").strip()
        if trc_addr and len(trc_addr) >= 34 and trc_addr.startswith("T"):
            print(f"  TRC address: {trc_addr}")
            bal = get_trc_usdt(trc_addr)
            entry["trc"]["address"] = trc_addr
            entry["trc"]["USDT"] = bal
            print(f"  USDT(TRC20): {bal}")
            time.sleep(1.5)

        # ERC20
        erc_addr = w.get("erc", "").strip()
        if erc_addr and len(erc_addr) == 42 and erc_addr.startswith("0x"):
            print(f"  ERC address: {erc_addr}")
            entry["erc"]["address"] = erc_addr

            eth = get_eth_balance(erc_addr)
            entry["erc"]["ETH"] = eth
            print(f"  ETH: {eth}")
            time.sleep(0.3)

            usdt = get_erc20_balance(erc_addr, USDT_ERC20, 6)
            entry["erc"]["USDT"] = usdt
            print(f"  USDT(ERC20): {usdt}")
            time.sleep(0.3)

            usdc = get_erc20_balance(erc_addr, USDC_ERC20, 6)
            entry["erc"]["USDC"] = usdc
            print(f"  USDC(ERC20): {usdc}")
            time.sleep(0.3)

        results["wallets"].append(entry)

    out_path = history_dir / f"{date_str}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved → {out_path}")

    # Update index.json (list of available dates)
    index_path = root / "data" / "index.json"
    dates = []
    if index_path.exists():
        with open(index_path) as f:
            dates = json.load(f).get("dates", [])
    if date_str not in dates:
        dates.append(date_str)
        dates.sort(reverse=True)
    with open(index_path, "w") as f:
        json.dump({"dates": dates}, f, indent=2)
    print(f"Updated → {index_path}")


if __name__ == "__main__":
    collect()
