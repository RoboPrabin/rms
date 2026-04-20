# DPM3 Module Documentation

## Overview

**File:** `pages/dpm3.py`
**Type:** Streamlit Web Application
**Purpose:** DPM3 (Depository Participant Module 3) - Stock holding/portfolio management system

---

## What is DPM3?

DPM3 is a stock portfolio management module that:
- Imports client stock holdings from depository files
- Tracks pledged and free share balances
- Calculates portfolio valuations
- Manages on-hold stock transactions

---

## Architecture

### Class: `DPM3(BasePage)`

Inherits from `BasePage` (Streamlit page base class).

### Key Methods

#### 1. `dump_data_to_db(df)`
- **Purpose:** Saves processed dataframe to SQL database
- **Input:** pandas DataFrame
- **Output:** Writes to `dpm3` table

#### 2. `extract_data_from_raw_txt_file(file_obj)`
- **Purpose:** Parses raw DPM3 TXT file format
- **Columns Extracted:** BOID, ISIN, FREE BALANCE, PLEDGE BALANCE, CURRENT BALANCE
- **Returns:** DataFrame with default columns (SCRIPT, CLOSING PRICE, VALUATIONS)

#### 3. `append_thursday_buy_data(df, selected_date)`
- **Purpose:** Adds Thursday floor sheet buy transactions
- **Data Source:** `floorsheet` table
- **Processing:**
  - Aggregates by CLIENT CODE, SCRIPT
  - Maps BOID to client codes
  - Sets STATUS = "THURSDAY BUY"

#### 4. `enrich_with_isin(df)`
- **Purpose:** Maps ISIN numbers to script names
- **Data Source:** `isin_data` table

#### 5. `enrich_with_client_code_and_branch(df)`
- **Purpose:** Links BOID to client details
- **Data Source:** `kyc` table
- **Adds:** CLIENT CODE, CLIENT NAME, BRANCH

#### 6. `enrich_with_close_price(df)`
- **Purpose:** Adds closing prices for valuation
- **Data Source:** `average_price` table
- **Calculates:**
  - FREE SHARE VALUATION = FREE BALANCE × CLOSING PRICE
  - PLEDGE SHARE VALUATION = PLEDGE BALANCE × CLOSING PRICE
  - TOTAL VALUATION = SUM of both

#### 7. `enrich_with_bro(df)`
- **Purpose:** Adds Relationship Manager (BRO) info
- **Data Source:** `rm_child_map` table

---

## Data Processing Pipeline

```
1. Upload TXT File
        ↓
2. extract_data_from_raw_txt_file()
        ↓
3. enrich_with_isin()
        ↓
4. enrich_with_client_code_and_branch()
        ↓
5. append_thursday_buy_data()
        ↓
6. enrich_with_close_price()
        ↓
7. enrich_with_bro()
        ↓
8. dump_data_to_db()
```

---

## User Interface Modes

### Mode 1: Upload Mode
- Triggered when NO file uploaded this week
- User uploads `.txt` file
- Selects Thursday buy floor sheet date
- Processing happens in 6 steps with status indicator

### Mode 2: View Mode
- Triggered when file IS already uploaded
- Two sub-modes:

#### A. Latest Holdings (UAT)
- Shows current stock holdings
- **Filters:** ALL, CLIENT CODE, CLIENT NAME, SCRIPT, BRANCH
- **Metrics:**
  - Total Scripts/Rows
  - Total Valuation
  - Free Valuation
  - Pledge Valuation
- **Interactive:** Click row to see detailed script breakdown

#### B. On Hold
- Shows pending/blocked transactions
- **Filters:** ALL, CLIENT CODE, CLIENT NAME, SCRIPT
- **Metrics:**
  - Total Hold Scripts
  - Total Hold Quantity
  - Total Hold Valuation

---

## Data Flow Diagram

```
┌─────────────────┐
│   TXT File     │
│  (DPM3 Data)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│         Processing Pipeline                     │
│  1. Parse TXT (BOID, ISIN, Balances)           │
│  2. Match ISIN → Script Name                   │
│  3. Link BOID → Client Info                    │
│  4. Add Thursday Buy Data                      │
│  5. Attach Closing Prices                      │
│  6. Tag BRO/RM                                 │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   dpm3 Table   │
│  (Database)    │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌────────┐
│Holdings│ │On Hold │
│  View  │ │  View  │
└────────┘ └────────┘
```

---

## Database Tables Used

| Table | Purpose |
|-------|---------|
| `dpm3` | Main holding data storage |
| `isin_data` | ISIN to script mapping |
| `kyc` | Client information (code, name, branch, BOID) |
| `average_price` | Daily closing prices |
| `rm_child_map` | BRO/RM to client mapping |
| `floorsheet` | Buy/sell transactions |
| `dpm3_onhold` | Blocked transactions |

---

## Key Functions

### Cached Functions (TTL: 3600s)

```python
@st.cache_data(ttl=3600)
def get_latest_holdings()          # Latest stock holdings
def get_dpm3_onhold()              # On-hold transactions
def get_latest_closing_price()     # Current prices
def get_today_due_list()           # Due settlements
def get_client_rm_map()            # BRO assignments
```

---

## UI Components

### Header
- Title: "📦 DPM3"
- Cache clear button (🧹)

### Filters
- Radio button: Mode selection
- Selectbox: Filter by field
- Multiselect: Filter values

### Display
- Badges: Row counts, valuations
- Dataframe: Tabular data
- Dialog: Detailed client view
- Metrics: Summary statistics

---

## Dependencies

```python
from api.ledger_api import dg_ledger_api      # Ledger API
from streamlit_searchbox import st_searchbox # Search
from datetime import date, timedelta          # Dates
import pandas as pd                            # Data processing
import streamlit as st                         # UI
from sqlalchemy import create_engine          # Database
from db import db                              # Database wrapper
import streamlit_bridge.app_state             # State management
from nepali_datetime import date as nepali_date # Nepali dates
from utils import auth_utils, helper          # Utilities
from pages.BasePage import BasePage           # Base class
```

---

## Beginner Summary

**Think of DPM3 as a stock portfolio tracker:**

1. **Import:** Take a raw bank statement (TXT file)
2. **Enrich:** Add client names, stock prices, broker info
3. **Calculate:** Compute total value of holdings
4. **Display:** Show in searchable dashboard

The app tracks:
- Which stocks each client holds
- How much is free vs pledged
- Current market value
- Pending transactions

---

## Error Handling

- Empty file handling
- Missing data fallback (N/F, N/A)
- Numeric conversion with defaults
- Date validation
- Cache management