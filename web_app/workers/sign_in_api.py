import requests

def sign_in_api(username, password):
    payload = {"username": username, "password": password}
    try:
        response = requests.post(
            url='https://icls.sosit-wh.net/login',
            json=payload
        )
        # Check if the response is successful
        if response.status_code == 200:
            try:
                data = response.json()  # Parse JSON if available
                return data
            except ValueError:
                print("Response is not valid JSON. Response content:", response.text)
                return None
        else:
            print(f"Request failed with status code {response.status_code}: {response.text}")
            return response.json()['type']
    except requests.exceptions.RequestException as e:
        print("An error occurred while making the request:", e)
        return None
