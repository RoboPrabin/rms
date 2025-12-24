from datetime import datetime
import nepali_datetime

def convert_ad_to_bs(ad_date: str) -> str:
    ad_dt = datetime.strptime(ad_date, "%Y-%m-%d")
    bs_date = nepali_datetime.date.from_datetime_date(ad_dt.date())
    return bs_date.strftime("%Y-%m-%d")

print(convert_ad_to_bs("2025-12-24"))  # Outputs: 2082-09-09