import requests

def get_targets():
    url = "http://localhost/nette/greenhouse/www/api/getdata/"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print("Error:", response.status_code, response.text)