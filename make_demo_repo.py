r"""Create a small Python demo repository with a realistic commit history for testing PyTwin.

The history tells a story PyTwin should detect commit by commit:
clean start -> features added -> complexity and security problems creep in ->
refactoring -> security fixes -> documentation and tests.

Usage (PowerShell):
    python make_demo_repo.py                 # creates .\pytwin-demo-shop with 12 commits
    python make_demo_repo.py C:\path\to\dir  # or choose the folder

Then push it to GitHub:
    1. On github.com create a new, empty, PUBLIC repository named pytwin-demo-shop
       (no README, no .gitignore).
    2. cd pytwin-demo-shop
       git remote add origin https://github.com/<your-user>/pytwin-demo-shop.git
       git push -u origin main
    3. In PyTwin, paste https://github.com/<your-user>/pytwin-demo-shop and build the twin.

Only the Python standard library and git are needed. The demo code is never run by PyTwin.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ----------------------------------------------------------------------------- file versions

README = """# pytwin-demo-shop

A tiny order-processing library used to demonstrate PyTwin, a software digital twin.
Its history deliberately goes through good and bad phases.
"""

INVENTORY = '''"""Product inventory."""


class Inventory:
    """Keeps stock levels per product."""

    def __init__(self):
        """Start with an empty stock."""
        self.stock = {}

    def add(self, product, qty):
        """Add qty units of product."""
        self.stock[product] = self.stock.get(product, 0) + qty

    def remove(self, product, qty):
        """Remove qty units; raise ValueError if there is not enough stock."""
        if self.stock.get(product, 0) < qty:
            raise ValueError(f"not enough {product}")
        self.stock[product] -= qty

    def available(self, product):
        """Units of product in stock."""
        return self.stock.get(product, 0)
'''

ORDERS_V1 = '''"""Order totals."""


def order_total(items):
    """Sum of price x quantity for each item."""
    return sum(item["price"] * item["qty"] for item in items)
'''

ORDERS_V2_DISCOUNTS = '''"""Order totals."""


def order_total(items):
    """Sum of price x quantity for each item."""
    return sum(item["price"] * item["qty"] for item in items)


def apply_discount(total, customer, coupon, season):
    if customer == "gold":
        if coupon:
            if season == "sale":
                return total * 0.6
            else:
                return total * 0.7
        else:
            return total * 0.8
    elif customer == "silver":
        if coupon:
            return total * 0.85
        else:
            return total * 0.9
    else:
        if coupon and season == "sale":
            return total * 0.9
        return total
'''

ORDERS_V3_MESSY = ORDERS_V2_DISCOUNTS + '''

def process_orders(orders, user, mode, discount, tax, region, flag):
    total = 0
    result = []
    for i in range(len(orders)):
        if orders[i]["qty"] > 0:
            if orders[i]["price"] > 100:
                if region == "EU":
                    if flag:
                        total = total + orders[i]["price"] * orders[i]["qty"] * (1 - discount) * (1 + tax)
                    else:
                        total = total + orders[i]["price"] * orders[i]["qty"] * (1 + tax)
                elif region == "US":
                    if user is not None and user.get("vip"):
                        total = total + orders[i]["price"] * orders[i]["qty"] * 0.95
                    else:
                        total = total + orders[i]["price"] * orders[i]["qty"]
                elif region == "UK":
                    if orders[i]["qty"] > 10 or flag:
                        total = total + orders[i]["price"] * orders[i]["qty"] * 1.05
                    else:
                        total = total + orders[i]["price"] * orders[i]["qty"] * 1.2
                else:
                    total = total + orders[i]["price"] * orders[i]["qty"] * 1.1
            else:
                if mode == "fast":
                    total = total + orders[i]["price"]
                else:
                    total = total + orders[i]["price"] * orders[i]["qty"]
            result.append(orders[i])
    return total, result
'''

ORDERS_V4_REFACTORED = '''"""Order totals, discounts and batch processing."""

DISCOUNTS = {
    ("gold", True, True): 0.6, ("gold", True, False): 0.7, ("gold", False, False): 0.8,
    ("gold", False, True): 0.8, ("silver", True, True): 0.85, ("silver", True, False): 0.85,
    ("silver", False, True): 0.9, ("silver", False, False): 0.9,
}
REGION_FACTORS = {"US": 1.0}
DEFAULT_REGION_FACTOR = 1.1


def order_total(items):
    """Sum of price x quantity for each item."""
    return sum(item["price"] * item["qty"] for item in items)


def apply_discount(total, customer, coupon, season):
    """Apply the customer's discount; regular customers only get the sale coupon."""
    on_sale = season == "sale"
    if customer in ("gold", "silver"):
        return total * DISCOUNTS[(customer, bool(coupon), on_sale)]
    return total * 0.9 if coupon and on_sale else total


def line_total(order, region, tax, discount, apply_eu_discount):
    """Total for one order line, including regional pricing."""
    amount = order["price"] * order["qty"]
    if order["price"] <= 100:
        return amount
    if region == "EU":
        factor = (1 - discount) if apply_eu_discount else 1
        return amount * factor * (1 + tax)
    return amount * REGION_FACTORS.get(region, DEFAULT_REGION_FACTOR)


def process_orders(orders, region, tax=0.2, discount=0.0, apply_eu_discount=False):
    """Total of all orders with a positive quantity, and those orders."""
    valid = [order for order in orders if order["qty"] > 0]
    total = sum(line_total(o, region, tax, discount, apply_eu_discount) for o in valid)
    return total, valid
'''

REPORTS_INSECURE = '''import subprocess
import pickle


def run_report(name):
    return subprocess.call("generate_report " + name, shell=True)


def load_session(data):
    return pickle.loads(data)


def export(rows, path):
    f = open(path, "w")
    for r in rows:
        f.write(str(r) + "\\n")
'''

REPORTS_SECURE = '''"""Reports and session storage."""
import json
import subprocess


def run_report(name):
    """Run the report generator without a shell, so name cannot inject commands."""
    return subprocess.call(["generate_report", name])


def load_session(data):
    """Load a session saved as JSON (never pickle untrusted data)."""
    return json.loads(data)


def export(rows, path):
    """Write one row per line."""
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(f"{row}\\n")
'''

UTILS_BAD = '''import os
import hashlib
import random


def password_hash(pw):
    return hashlib.md5(pw.encode()).hexdigest()


def make_token():
    return str(random.random())


def cleanup(path):
    try:
        os.remove(path)
    except:
        pass


def l(x):
    return [i for i in x if i]
'''

UTILS_FIXED = '''"""Small helpers."""
import hashlib
import os
import secrets


def password_hash(password, salt):
    """PBKDF2-SHA256 hash of a password."""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000).hex()


def make_token():
    """Cryptographically secure random token."""
    return secrets.token_urlsafe(32)


def cleanup(path):
    """Delete path if it exists."""
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def non_empty(values):
    """Values that are truthy."""
    return [value for value in values if value]
'''

TESTS = '''"""Tests for the demo shop."""
from shop.inventory import Inventory
from shop.orders import apply_discount, order_total, process_orders


def test_inventory_add_remove():
    inv = Inventory()
    inv.add("apple", 5)
    inv.remove("apple", 2)
    assert inv.available("apple") == 3


def test_order_total():
    assert order_total([{"price": 2, "qty": 3}]) == 6


def test_gold_sale_coupon():
    assert apply_discount(100, "gold", True, "sale") == 60


def test_process_orders_skips_empty():
    total, valid = process_orders([{"price": 10, "qty": 0}, {"price": 10, "qty": 2}], "US")
    assert total == 20 and len(valid) == 1
'''

# ----------------------------------------------------------------------------- the history
# Each step: (commit message, {path: content or None to delete})

HISTORY = [
    ("Initial project: inventory module", {
        "README.md": README, "shop/__init__.py": '"""Demo shop package."""\n',
        "shop/inventory.py": INVENTORY}),
    ("Add order totals", {"shop/orders.py": ORDERS_V1}),
    ("Add customer discounts", {"shop/orders.py": ORDERS_V2_DISCOUNTS}),
    ("Add report generation and session loading", {"shop/reports.py": REPORTS_INSECURE}),
    ("Add utility helpers", {"shop/utils.py": UTILS_BAD}),
    ("Add batch order processing (rushed for release)", {"shop/orders.py": ORDERS_V3_MESSY}),
    ("Tweak inventory error message", {
        "shop/inventory.py": INVENTORY.replace('f"not enough {product}"',
                                               'f"not enough {product} in stock"')}),
    ("Refactor order processing into small functions", {"shop/orders.py": ORDERS_V4_REFACTORED}),
    ("Security: remove shell=True and pickle from reports", {"shop/reports.py": REPORTS_SECURE}),
    ("Security: strong password hashing and secure tokens", {"shop/utils.py": UTILS_FIXED}),
    ("Add unit tests", {"tests/__init__.py": "", "tests/test_shop.py": TESTS}),
    ("Update README", {"README.md": README + "\nRun the tests with `pytest`.\n"}),
]


def git(repo: Path, *args: str, date: str | None = None) -> None:
    env = dict(os.environ)
    env.update({"GIT_AUTHOR_NAME": env.get("GIT_AUTHOR_NAME", "PyTwin Demo"),
                "GIT_AUTHOR_EMAIL": env.get("GIT_AUTHOR_EMAIL", "demo@example.com"),
                "GIT_COMMITTER_NAME": env.get("GIT_COMMITTER_NAME", "PyTwin Demo"),
                "GIT_COMMITTER_EMAIL": env.get("GIT_COMMITTER_EMAIL", "demo@example.com")})
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True)


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "pytwin-demo-shop").resolve()
    if target.exists() and any(target.iterdir()):
        print(f"{target} already exists and is not empty. Choose another folder.")
        return 1
    target.mkdir(parents=True, exist_ok=True)
    git(target, "init", "-q", "-b", "main")
    start = datetime.now(timezone.utc) - timedelta(days=len(HISTORY))
    for day, (message, files) in enumerate(HISTORY):
        for rel, content in files.items():
            path = target / rel
            if content is None:
                path.unlink(missing_ok=True)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        git(target, "add", "-A")
        git(target, "commit", "-q", "-m", message,
            date=(start + timedelta(days=day)).isoformat(timespec="seconds"))
        print(f"  commit {day + 1:2d}: {message}")
    print(f"\nCreated {target} with {len(HISTORY)} commits.")
    print("Next: create an empty public repo on GitHub named pytwin-demo-shop, then run:")
    print(f"  cd {target}")
    print("  git remote add origin https://github.com/<your-user>/pytwin-demo-shop.git")
    print("  git push -u origin main")
    return 0


if __name__ == "__main__":
    sys.exit(main())
