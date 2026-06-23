import requests
import time

while True:
    response = requests.get(
        "http://localhost:8000/status"
    )

    print(response.json())

    time.sleep(5)