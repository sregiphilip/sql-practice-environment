"""Generate the synthetic dataset for the SQL practice environment, then build index.html.

Produces data/applications.csv, data/merchants.csv, data/transactions.csv with the
row counts and schemas from the take-home, seeded so results are reproducible.
The data is clean: no NULLs, duplicates or inconsistent values beyond what the
schema implies (verified_at is NULL unless status = 'Verified').
"""
import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(20260317)
OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

FMT = "%Y-%m-%d %H:%M:%S"
START = datetime(2025, 10, 1)
END = datetime(2026, 6, 30, 23, 59, 59)


def rand_ts(start=START, end=END):
    secs = random.randint(0, int((end - start).total_seconds()))
    return (start + timedelta(seconds=secs)).replace(second=0)


# ---------------------------------------------------------------- merchants (600)
PREFIX = ["Fast", "Secure", "Neo", "Global", "Blue", "Peak", "Swift", "Prime", "Nova", "Iron",
          "Harbor", "Summit", "Bright", "Atlas", "Cedar", "Zen", "Apex", "Lumen", "Orbit", "Vector",
          "Pacific", "North", "Coral", "Silver", "Rapid", "Clear", "Urban", "Golden", "Echo", "Pioneer"]
CORE = ["Pay", "Trust", "Fin", "Remit", "Ledger", "Wallet", "Cash", "Coin", "Trade", "Bridge",
        "Flow", "Mint", "Capital", "Exchange", "Commerce", "Cargo", "Supply", "Retail", "Logistics", "Labs"]
SUFFIX = ["Solutions", "Bank", "Tech", "Ltd", "Group", "Co", "Partners", "Holdings", "Inc", "Pty Ltd"]

MANAGERS = ["Sarah", "James", "Matt", "Priya", "Daniel", "Chen"]
MGR_W = [18, 17, 17, 16, 16, 16]

fixed_merchants = [
    (890, "FastPay Solutions", "High", "Sarah"),
    (456, "SecureTrust Bank", "Low", "Matt"),
    (123, "NeoFin Tech", "High", "James"),
    (745, "Global Remit", "Medium", "Sarah"),
]
ids = set(m[0] for m in fixed_merchants)
pool = [i for i in range(100, 1000) if i not in ids]
random.shuffle(pool)
merchant_ids = [m[0] for m in fixed_merchants] + pool[: 600 - len(fixed_merchants)]

names = set(m[1] for m in fixed_merchants)
merchants = list(fixed_merchants)
for mid in merchant_ids[len(fixed_merchants):]:
    while True:
        n = f"{random.choice(PREFIX)}{random.choice(CORE)} {random.choice(SUFFIX)}"
        if n not in names:
            names.add(n)
            break
    risk = random.choices(["High", "Medium", "Low"], [25, 40, 35])[0]
    mgr = random.choices(MANAGERS, MGR_W)[0]
    merchants.append((mid, n, risk, mgr))

risk_of = {m[0]: m[2] for m in merchants}

# ---------------------------------------------------------------- applications (10,000)
# business_id space is wider than merchants: many applicants never became merchants.
non_merchant_biz = [i for i in range(1000, 12000)]
biz_pool = merchant_ids + non_merchant_biz

apps = []
fixed_apps = [
    (1001, 890, datetime(2026, 3, 1, 9, 0), "Verified", datetime(2026, 3, 2, 11, 30)),
    (1002, 456, datetime(2026, 3, 15, 14, 20), "Pending", None),
    (1003, 123, datetime(2026, 3, 20, 10, 0), "Verified", datetime(2026, 3, 20, 18, 45)),
    (1004, 745, datetime(2026, 4, 1, 8, 0), "Verified", datetime(2026, 4, 2, 9, 0)),
]
apps.extend(fixed_apps)
SNAPSHOT = datetime(2026, 7, 1)


def make_app(app_id, biz, created, force_status=None):
    age_h = (SNAPSHOT - created).total_seconds() / 3600
    # Older applications are mostly resolved; recent ones are still in the queue.
    age_d = age_h / 24
    weights = [70, 26, 2, 2] if age_d > 30 else [64, 20, 8, 8] if age_d > 7 else [35, 10, 30, 25]
    status = force_status or random.choices(["Verified", "Rejected", "Pending", "In Review"], weights)[0]
    verified_at = None
    if status == "Verified":
        hrs = random.lognormvariate(math.log(22), 0.85)
        while not 0.5 <= hrs <= 336:  # redraw outliers rather than clipping (no pile-up at a cap)
            hrs = random.lognormvariate(math.log(22), 0.85)
        if hrs > age_h:  # cannot be verified in the future
            hrs = random.uniform(0.5, max(age_h, 1))
        verified_at = (created + timedelta(hours=hrs)).replace(second=0)
    return (app_id, biz, created, status, verified_at)


# Each business goes through onboarding once. Some rejected businesses re-apply a few days
# later, always within the same calendar month, so "unique businesses" matters but a
# business never spans two monthly cohorts.
biz_queue = [b for b in biz_pool if b not in {a[1] for a in fixed_apps}]
random.shuffle(biz_queue)
app_id = 1005
while len(apps) < 10000:
    biz = biz_queue.pop()
    created = rand_ts()
    # Every merchant is a business that passed KYB
    first = make_app(app_id, biz, created, "Verified" if biz in risk_of else None)
    apps.append(first)
    app_id += 1
    if first[3] == "Rejected" and random.random() < 0.35 and len(apps) < 10000:
        created2 = (created + timedelta(hours=random.uniform(24, 24 * 10))).replace(second=0)
        if created2.month == created.month and created2 < END:
            apps.append(make_app(app_id, biz, created2))
            app_id += 1

apps.sort(key=lambda a: a[0])
with open(OUT / "applications.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["app_id", "business_id", "created_at", "status", "verified_at"])
    for a in apps:
        w.writerow([a[0], a[1], a[2].strftime(FMT), a[3], a[4].strftime(FMT) if a[4] else ""])

# ---------------------------------------------------------------- transactions (50,000)
# Merchant activity weights: heavy-tailed (a few big merchants, many small ones)
weights = {m: random.paretovariate(1.3) for m in merchant_ids}

txn_fixed = [
    (890, 5500.00, datetime(2026, 3, 28, 12, 0), True),
    (123, 120.50, datetime(2026, 3, 29, 15, 30), False),
    (890, 3000.00, datetime(2026, 3, 30, 9, 15), True),
    (456, 45.00, datetime(2026, 4, 1, 10, 0), False),
]
w_ids = list(weights)
w_vals = [weights[m] for m in w_ids]

rows = []
for mid, amt, ts, rev in txn_fixed:
    rows.append([mid, amt, ts, rev])

while len(rows) < 50000:
    mid = random.choices(w_ids, w_vals)[0]
    risk = risk_of[mid]
    mu = {"High": math.log(900), "Medium": math.log(450), "Low": math.log(200)}[risk]
    amt = round(min(random.lognormvariate(mu, 1.1), 250000), 2)
    base_p = {"High": 0.18, "Medium": 0.06, "Low": 0.02}[risk]
    p = min(base_p + (0.35 if amt > 5000 else 0.0), 0.95)
    rows.append([mid, amt, rand_ts(), random.random() < p])

rows.sort(key=lambda r: r[2])
txns = [[f"TXN_{i:05d}"] + r for i, r in enumerate(rows, start=1)]

txns.sort(key=lambda t: (t[3], t[0]))
with open(OUT / "transactions.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["txn_id", "merchant_id", "amount", "processed_at", "requires_review"])
    for t in txns:
        w.writerow([t[0], t[1], f"{t[2]:.2f}", t[3].strftime(FMT),
                    "TRUE" if t[4] else "FALSE"])

with open(OUT / "merchants.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["merchant_id", "business_name", "risk_level", "account_manager"])
    for m in merchants:
        w.writerow([m[0], m[1], m[2], m[3]])

print(f"applications={len(apps)} merchants={len(merchants)} transactions={len(txns)}")

# ---------------------------------------------------------------- build the workbook page
html = (Path(__file__).parent / "workbook_template.html").read_text()
for name in ["applications", "merchants", "transactions"]:
    html = html.replace(f"/*__{name}__*/", (OUT / f"{name}.csv").read_text())
# expected results, as salted fingerprints only
html = html.replace("/*__checkdata__*/", (Path(__file__).parent / "check_data.json").read_text())
(Path(__file__).parent / "index.html").write_text(html)
print("wrote index.html")
