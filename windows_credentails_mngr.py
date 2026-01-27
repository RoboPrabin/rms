# import keyring



# def set_password(service_name, username, password):
#     keyring.set_password(
#         service_name=service_name,
#         username=username,
#         password=password
#     )


# def get_password():
#     password = keyring.get_password(service_name="MyApp",username="api_user")
#     return password

# def delete_password():
#     keyring.delete_password(service_name="MyApp",username="api_user")


from db import db
import pandas as pd
df = pd.read_excel('info.xlsx')
df['Occupation'] = df['Occupation'].fillna('')
df['Company'] = df['Company'].fillna('')
db.insert_aml_transactions_bulk(df=df, created_by="ADMIN")