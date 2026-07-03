"""One-time script to seed demo TMS records with real users across branches."""
from db import db

demo_records = [
    # (client_code, client_name, boid, created_at_bs, opened_by)
    ("TMS001", "RAM SHRESTHA",    "1301140000000001", "2081-01-15", "ADMIN"),
    ("TMS002", "SITA POUDEL",     "1301140000000002", "2081-01-15", "ANJIT"),
    ("TMS003", "HARI ADHIKARI",   "1301140000000003", "2081-02-10", "SIRJANA"),
    ("TMS004", "GEETA SHARMA",    "1301140000000004", "2081-02-10", "GOKUL"),
    ("TMS005", "KRISHNA THAPA",   "1301140000000005", "2081-03-05", "BIMAL"),
    ("TMS006", "NITA KUMARI",     "1301140000000006", "2081-03-05", "SAJANP"),
    ("TMS007", "BISHNU ACHARYA",  "1301140000000007", "2081-03-20", "MOHANB"),
    ("TMS008", "ANITA GURUNG",    "1301140000000008", "2081-04-12", "ADMIN"),
    ("TMS009", "RAJENDRA BASNET", "1301140000000009", "2081-04-12", "USHA"),
    ("TMS010", "SUNITA KHADKA",   "1301140000000010", "2081-05-01", "MANOJ"),
    ("TMS011", "PRAKASH NEUPANE", "1301140000000011", "2081-05-15", "TANK"),
    ("TMS012", "DEEPAK BOHARA",   "1301140000000012", "2081-06-08", "MANI"),
    ("TMS013", "SARITA LAMA",     "1301140000000013", "2081-06-08", "PRABIN"),
    ("TMS014", "AMRIT RAI",       "1301140000000014", "2081-07-01", "TULSA"),
    ("TMS015", "KABITA SHRESTHA", "1301140000000015", "2081-07-20", "DAYA"),
]

count = 0
for code, name, boid, date_bs, opened_by in demo_records:
    try:
        db.insert_tms_record(
            client_code=code,
            client_name=name,
            boid=boid,
            created_at_bs=date_bs,
            opened_by=opened_by
        )
        count += 1
        print(f"  OK {code} - {name} ({opened_by})")
    except Exception as e:
        if "duplicate key" in str(e).lower():
            print(f"  -- {code} already exists, skipped")
        else:
            print(f"  FAIL {code} - {e}")

print(f"\nInserted {count} demo TMS records.")
