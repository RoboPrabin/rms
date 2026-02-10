import pandas as pd

filepath = r"C:\Users\Prabin\Desktop\order book for the period from Kartik 1, 2082 to Poush 30, 2082.xlsx"
df = pd.read_excel(filepath)

# Count rows for each unique Order Status
status_counts = df['Order Status'].value_counts()

# Convert to DataFrame with explicit columns
status_df = status_counts.reset_index()
status_df.columns = ['Order Status', 'Count']

# Add Date Range column
status_df['Date Range'] = '2025-07-17 to 2025-10-17'

print(status_df)
status_df.to_excel("report.xlsx", index=False)