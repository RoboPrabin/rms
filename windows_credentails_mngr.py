
import requests

headers = {
    'Pn': 'DMBA+xwcc/6lVvqFzYNwSA==',
    'sec-ch-ua-platform': '"macOS"',
    'Authorization': 'Bearer eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiIxMjQyNDk4MjIiLCJBIjoiMTcyLjE3LjI2LjQiLCJCIjoiU1VBIiwiQyI6IlBSQUJJTiIsIkQiOiIxIiwiRSI6IktUTSIsIkYiOiIxMDIwNTAxMDEiLCJHIjoiMTAyMDUwMjAxIiwiSCI6IjEwMjAxMDQiLCJJIjoiNDgiLCJKIjoiOTkiLCJLIjoiTiIsIkwiOiJOIiwiTSI6Ik4iLCJOIjoiTiIsIk8iOiIvYm9tIiwiUCI6Ijc5ODAiLCJRIjoiZmFsc2UiLCJSIjoiVHJpc2hha3RpIFNlY3VyaXRpZXMgTGltaXRlZCIsIlQiOlsxLDIsMyw0LDUsNiw3LDFdLCJpYXQiOjE3ODA5MDE4NjksImV4cCI6MTc4MDk0MjQ5OX0.TaGJ2ZLZ9UyJpyMvYc1Kjm2tIiyMTcO_Q1-8CfEVZnN5XkumaUHD4pufc17v0yCIanIZiS7yjhWDAMYj3EhBYA',
    'Referer': 'https://dgtrade.trishakti.com.np:8080/bom/index.html',
    'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'Em': '+/5+AoUSQTRtDcJndB+Cm4mxPvaPj06gSYWw2ItcnRTFfhGn1sCITXN/JrG6UG5RG5vliC7u+t5TbMcaehBhsJfZL1PjQKp3QZ97bNEkFgdBfiRWpRpKfX08qwXGk7Kvb8RFfZzkXJeHMmFKOOSzzfgs4k3TxDToT7+RhUG9oZowcPBwEe2OFURM3bwGuND5GwokKX2JIzqKazffi9Nsj2E0+tTRbcYF6Tun4tluHlFltd1Wm7xpkffzVN2IhblR5bUlNryylO7ZJeVclnSuJOP4GmC7ayeHDrK1+XiE7yHJO5oRr0B1hqoTQb4Tyw2JodWZZrlB/VB5rUCEaEYo2pTnx8kBRTkjA0Qx8VYVC3G3TM0ayqIaxgPB6iMuPJ5LlYXq5Hx5Ej5YXRV714LcvVLL781BrbOJtuUuMtECO3KkuYxL5ahVlEtyWPPTQ4paMY2NLAUA5ZB7fk316zC+X+zchPhgluKfolfRqjtRh0UjsH1jQ688JhZuV07tWucbAas76R82w7xy0Z4bx1f1x8hFtKSy57/zW2WlB0gh8KJh1oWzcShxThQTJzLo27vshC1nVIlRD0mJ8pjW4OcDXMZmTE9r5pf+7zn1B9tm6oMqEMWkGACbtjmv0oYRTSL9gfGnpFnj3xXMPOe+YQe5sM8D+x8UWD6y9RtDRkA2gAmzdYC7KK8+lMx0AI2XuXkrydAJpn88g9KUCncrMgFXCtSRIHTmynNw2QrzyAdNVWeIXy9YRd6FeSDPAROTnD+DxYkISGf6dbO3q9wHthtD7jL+p8sif7LvNfkIUyr+c+hH0W3ElLBsy0JN9DowY4ZXvVE8uP/KIv6PnzkmcCIHmUF6KtHMdVsNS4V3wqa8t+/hyR/+BhszKrFRsChKuyEUJUU0ixJU+G+/XuUdNvoW0UXtTzv+zwTRnlSmcvSweSI2mVPZddas5Bh7H6+8LqC0PD1MnnjVDLXc8lJU8z+Bvw==',
    'Access-Control-Allow-Origin': '*',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'X-Session-Id': 'MfyurC7muw0zrfU7DwmYN',
}

params = {
    'pageNumber': '0',
    'date': '2026-06-10',
    'dueType': 'DR',
    'calcBy': 'settlementDate',
    'agentDues': 'false',
    'otherDp': 'false',
    'ownDp': 'false',
}

response = requests.get('https://dgtrade.trishakti.com.np:8080/bom/api/account/report/due', params=params, headers=headers)

print(response.status_code)