import requests
import json

def mowhn():
    username = input("Enter your username: ")
    password = input("Enter your password: ")

    url = "https://puter.com/login"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Origin": "https://puter.com",
        "Referer": "https://puter.com/",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    }

    payload = {
        "username": username,
        "password": password
    }

    try:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            if data.get("proceed"):
                print(f"Login successful! Token: {data['token']}")
            else:
                print("Login failed. Please check your credentials.")
        else:
            print(f"Error: Received status code {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    mowhn()