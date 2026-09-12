from pathlib import Path
import sqlite3
import importlib
import py_compile

ROOT = Path.cwd()

print()
print("=" * 70)
print("KENYA FINANCIAL ANALYTICS")
print("SYSTEM CHECK")
print("=" * 70)
print()

errors = []
warnings = []

# ============================================================
# FILE CHECK
# ============================================================

files = [
    "app.py",
    "dashboard.py",
    "kenya_market.db",
    "cbk_data.py",
    "cbk_fetcher.py",
    "cbk_pricing.py",
    "cbk_historical_importer.py",
    "pricing_engine.py",
    "cbk_pricing.py",
    "risk_engine.py",
    "portfolio_engine.py",
    "backtest_engine.py",
    "stress_engine.py",
]

print("1. PROJECT FILES")
print("-" * 70)

for name in files:

    path = ROOT / name

    if path.exists():
        print(f"[OK] {name}")
    else:
        print(f"[MISSING] {name}")
        warnings.append(
            f"Missing file: {name}"
        )


# ============================================================
# PRICING DIRECTORY
# ============================================================

print()
print("2. PRICING DIRECTORY")
print("-" * 70)

pricing = ROOT / "pricing"

if pricing.exists():

    print("[OK] pricing directory")

    for path in pricing.glob("*.py"):

        print(
            f"[OK] pricing/{path.name}"
        )

else:

    warnings.append(
        "pricing directory not found."
    )

    print(
        "[WARNING] pricing directory not found"
    )


# ============================================================
# PYTHON SYNTAX
# ============================================================

print()
print("3. PYTHON SYNTAX")
print("-" * 70)

python_files = list(
    ROOT.glob("*.py")
)

if pricing.exists():

    python_files += list(
        pricing.glob("*.py")
    )

for path in python_files:

    try:

        py_compile.compile(
            str(path),
            doraise=True
        )

        print(
            f"[OK] {path.name}"
        )

    except Exception as error:

        print(
            f"[ERROR] {path.name}: {error}"
        )

        errors.append(
            f"Syntax error in {path.name}: {error}"
        )


# ============================================================
# IMPORT CHECK
# ============================================================

print()
print("4. MODULE IMPORTS")
print("-" * 70)

modules = [
    "cbk_data",
    "cbk_fetcher",
    "cbk_pricing",
    "pricing_engine",
    "risk_engine",
    "portfolio_engine",
    "backtest_engine",
    "stress_engine",
]

for name in modules:

    try:

        importlib.import_module(
            name
        )

        print(
            f"[OK] {name}"
        )

    except ModuleNotFoundError as error:

        print(
            f"[WARNING] {name}: {error}"
        )

        warnings.append(
            f"Could not import {name}: {error}"
        )

    except Exception as error:

        print(
            f"[ERROR] {name}: {error}"
        )

        errors.append(
            f"Import error in {name}: {error}"
        )


# ============================================================
# DATABASE CHECK
# ============================================================

print()
print("5. DATABASE")
print("-" * 70)

db = ROOT / "kenya_market.db"

if db.exists():

    try:

        connection = sqlite3.connect(
            str(db)
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        )

        tables = [
            row[0]
            for row in cursor.fetchall()
        ]

        print(
            "Tables found:",
            len(tables)
        )

        for table in tables:

            print(
                f"  [OK] {table}"
            )

        if "treasury_bill_rates" in tables:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM treasury_bill_rates
                """
            )

            count = cursor.fetchone()[0]

            print()
            print(
                f"Treasury Bill records: {count}"
            )

            if count == 0:

                warnings.append(
                    "Treasury Bill table is empty."
                )

        else:

            warnings.append(
                "treasury_bill_rates table was not found."
            )

        connection.close()

    except Exception as error:

        errors.append(
            f"Database check failed: {error}"
        )

        print(
            "[ERROR]",
            error
        )

else:

    errors.append(
        "kenya_market.db was not found."
    )

    print(
        "[ERROR] Database not found"
    )


# ============================================================
# DASHBOARD CHECK
# ============================================================

print()
print("6. DASHBOARD")
print("-" * 70)

dashboard = ROOT / "dashboard.py"

if dashboard.exists():

    try:

        source = dashboard.read_text(
            encoding="utf-8"
        )

        compile(
            source,
            "dashboard.py",
            "exec"
        )

        print(
            "[OK] dashboard.py syntax"
        )

        expected_pages = [
            "Dashboard",
            "Kenyan Market",
            "Yield Curve",
            "Treasury Bills",
            "Bond Pricing",
            "Options & Greeks",
            "Risk Analysis",
            "Portfolio",
            "Backtesting",
            "Stress Testing",
        ]

        for page in expected_pages:

            if page in source:

                print(
                    f"[OK] {page}"
                )

            else:

                warnings.append(
                    f"Dashboard page not detected: {page}"
                )

    except Exception as error:

        print(
            "[ERROR] dashboard.py:",
            error
        )

        errors.append(
            f"Dashboard check failed: {error}"
        )

else:

    errors.append(
        "dashboard.py not found."
    )


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("=" * 70)
print("SYSTEM CHECK RESULT")
print("=" * 70)

print()

if errors:

    print(
        f"STATUS: {len(errors)} ERROR(S)"
    )

    print()

    for error in errors:

        print(
            "[ERROR]",
            error
        )

else:

    print(
        "STATUS: PASS"
    )

    print(
        "No critical errors were detected."
    )

if warnings:

    print()
    print(
        f"WARNINGS: {len(warnings)}"
    )

    for warning in warnings:

        print(
            "[WARNING]",
            warning
        )

print()
print("=" * 70)
print("SYSTEM CHECK COMPLETE")
print("=" * 70)
print()

