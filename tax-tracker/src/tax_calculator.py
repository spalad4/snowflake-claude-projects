#!/usr/bin/env python3
"""
Tax Tracker -- Federal Tax Estimator (Single Filer)

Usage:
    python tax_calculator.py [year]

Environment:
    FINANCE_DATA_DIR  path to the root of your tax data folder
    e.g.  export FINANCE_DATA_DIR=~/finance-data/taxes

Supported input files (place in FINANCE_DATA_DIR/<year>/):
    w2.csv                        -- W2 wages and withholding
    fidelity_transactions.csv     -- (coming soon)
    robinhood_transactions.csv    -- (coming soon)
    frec_transactions.csv         -- (coming soon)
    retirement.csv                -- (coming soon)
    hsa.csv                       -- (coming soon)
"""

import os
import csv
import sys
from pathlib import Path

TAX_YEAR = 2025

# ---------------------------------------------------------------------------
# 2025 Federal Tax Constants (Single Filer)
# ---------------------------------------------------------------------------

STANDARD_DEDUCTION = 15_000

ORDINARY_BRACKETS = [
    (11_925,        0.10),
    (48_475,        0.12),
    (103_350,       0.22),
    (197_300,       0.24),
    (250_525,       0.32),
    (626_350,       0.35),
    (float("inf"),  0.37),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_data_dir(year):
    base = os.environ.get("FINANCE_DATA_DIR")
    if not base:
        raise EnvironmentError(
            "FINANCE_DATA_DIR is not set.\n"
            "Add to ~/.zshrc:  export FINANCE_DATA_DIR=~/finance-data/taxes"
        )
    path = Path(base).expanduser() / str(year)
    if not path.exists():
        raise FileNotFoundError(
            f"Data directory not found: {path}\n"
            f"Create it with:  mkdir -p {path}"
        )
    return path


def read_csv(path):
    if not path.exists():
        return None  # None = not supplied, distinct from empty file
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def to_float(value):
    return float(str(value).replace(",", "").replace("$", "").strip() or 0)


# ---------------------------------------------------------------------------
# Loaders
# Each loader returns (data, found) -- found=False means file not present
# ---------------------------------------------------------------------------

def load_w2(data_dir):
    rows = read_csv(data_dir / "w2.csv")
    if rows is None:
        return {}, False
    if not rows:
        return {}, False
    r = rows[0]
    return {
        "employer":              r.get("employer", ""),
        "wages":                 to_float(r.get("wages", 0)),
        "federal_withheld":      to_float(r.get("federal_tax_withheld", 0)),
        "social_security_wages": to_float(r.get("social_security_wages", 0)),
        "medicare_wages":        to_float(r.get("medicare_wages", 0)),
        "hsa_employer":          to_float(r.get("hsa_employer_contribution", 0)),
        "roth_401k":             to_float(r.get("roth_401k_contribution", 0)),
        "traditional_401k":      to_float(r.get("traditional_401k_contribution", 0)),
    }, True


# ---------------------------------------------------------------------------
# Tax Calculation
# ---------------------------------------------------------------------------

def calc_ordinary_tax(taxable):
    tax, prev = 0.0, 0.0
    for bracket, rate in ORDINARY_BRACKETS:
        if taxable <= prev:
            break
        tax += (min(taxable, bracket) - prev) * rate
        prev = bracket
    return tax


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

W = 52

def section(title):
    print(f"\n  {title}")
    print(f"  {'-' * (W - 2)}")

def line(label, amount, negative=False):
    if negative or amount < 0:
        print(f"  {label:<36}  (${abs(amount):>10,.2f})")
    else:
        print(f"  {label:<36}   ${amount:>10,.2f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def calculate(year=TAX_YEAR):
    print(f"\n{'=' * W}")
    print(f"  TAX TRACKER  |  {year}  |  Single Filer")
    print(f"{'=' * W}")

    data_dir = get_data_dir(year)

    # Load available sources
    w2, has_w2 = load_w2(data_dir)
    # Future: investments, retirement, hsa loaded here as they are added

    # Track which sources are included in this estimate
    sources = []
    if has_w2:
        sources.append("W2")

    if not sources:
        print("\n  No input files found in", data_dir)
        print("  Add at least w2.csv to get started.\n")
        return

    print(f"\n  Sources included in this estimate: {', '.join(sources)}")

    # Build income
    wages = w2.get("wages", 0.0) if has_w2 else 0.0
    gross = wages

    # Adjustments (more will be added as sources are introduced)
    agi = gross

    # Taxable income
    taxable = max(0.0, agi - STANDARD_DEDUCTION)

    # Tax
    total_tax    = calc_ordinary_tax(taxable)
    withheld     = w2.get("federal_withheld", 0.0) if has_w2 else 0.0
    balance      = total_tax - withheld

    # Report
    section("INCOME")
    if has_w2:
        line("W2 Wages", wages)
    line("Gross Income", gross)

    section("DEDUCTIONS")
    line("Standard Deduction (Single)", STANDARD_DEDUCTION, negative=True)
    line("Taxable Income", taxable)

    section("TAX CALCULATION")
    line("Ordinary Income Tax", total_tax)

    section("WITHHOLDING & BALANCE")
    line("Federal Tax Withheld (W2)", withheld)
    balance_label = "TAX OWED" if balance >= 0 else "EXPECTED REFUND"
    line(balance_label, abs(balance))

    section("RATES")
    marginal  = next(r for b, r in ORDINARY_BRACKETS if taxable <= b)
    effective = (total_tax / gross * 100) if gross else 0.0
    print(f"  {'Marginal Rate':<36}  {marginal * 100:.0f}%")
    print(f"  {'Effective Rate':<36}  {effective:.1f}%")

    print(f"\n{'=' * W}")
    if balance >= 0:
        print(f"  >> You owe ${balance:,.2f} in additional federal taxes")
    else:
        print(f"  >> You are due a refund of ${abs(balance):,.2f}")
    print()


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else TAX_YEAR
    calculate(year)
