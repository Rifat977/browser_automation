from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import zipfile
import string

def create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass, scheme='http', plugin_path='proxy_auth_plugin.zip'):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = string.Template(
        """
        var config = {
            mode: "fixed_servers",
            rules: {
                singleProxy: {
                    scheme: "${scheme}",
                    host: "${proxy_host}",
                    port: parseInt(${proxy_port})
                },
                bypassList: ["localhost"]
            }
        };

        chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

        function callbackFn(details) {
            return {
                authCredentials: {
                    username: "${proxy_user}",
                    password: "${proxy_pass}"
                }
            };
        }

        chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {urls: ["<all_urls>"]},
            ["blocking"]
        );
        """
    ).substitute(
        proxy_host=proxy_host,
        proxy_port=proxy_port,
        proxy_user=proxy_user,
        proxy_pass=proxy_pass,
        scheme=scheme,
    )

    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return plugin_path

def get_webdriver_with_proxy(proxy_host, proxy_port, proxy_user, proxy_pass):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f'--proxy-server=http://{proxy_host}:{proxy_port}')

    plugin_path = create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass)
    chrome_options.add_extension(plugin_path)

    service = Service(ChromeDriverManager().install())
    browser = webdriver.Chrome(service=service, options=chrome_options)
    
    return browser

def fetch_ip_using_proxy(proxy_host, proxy_port, proxy_user, proxy_pass):
    browser = get_webdriver_with_proxy(proxy_host, proxy_port, proxy_user, proxy_pass)
    
    try:
        browser.get('https://api.ipify.org/')
        time.sleep(10)  # Wait for 10 seconds to allow the page to load
        content = browser.page_source
    finally:
        browser.quit()
    
    return content

proxy_details = [
    {
        "proxy_host": "na.dcnl7rw1.lunaproxy.net",
        "proxy_port": 12233,
        "proxy_user": "user-lu9597871-region-us-sessid-usm7574k3sgb2w6oxs-sesstime-90",
        "proxy_pass": "0502422374bd"
    },
]

for proxy in proxy_details:
    print(f"Using proxy {proxy['proxy_host']}:{proxy['proxy_port']}")
    ip_content = fetch_ip_using_proxy(
        proxy_host=proxy['proxy_host'],
        proxy_port=proxy['proxy_port'],
        proxy_user=proxy['proxy_user'],
        proxy_pass=proxy['proxy_pass']
    )
    print(ip_content)
