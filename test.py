import requests

# Proxy information
proxy_host = "na.dcnl7rw1.lunaproxy.net"
proxy_port = 12233
proxy_user = "user-lu9597871-region-us-sessid-usm7574k3sgb2w6oxs-sesstime-90"
proxy_pass = "0502422374bd"

# Construct the proxy URL
proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"

# Define the target URL to test the proxy
target_url = "https://api.ipify.org/"

# Set up the proxy for the request
proxies = {
    "http": proxy_url,
    "https": proxy_url
}

try:
    # Make a request through the proxy
    response = requests.get(target_url, proxies=proxies)
    
    # Check the response
    if response.status_code == 200:
        print(f"Proxy is working. Your IP address is: {response.text}")
    else:
        print("Proxy is not working. Please check your proxy settings.")
        
except requests.exceptions.RequestException as e:
    print("Error occurred:", e)