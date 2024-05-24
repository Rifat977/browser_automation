from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import zipfile
import string, time
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import deque


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


def scroll_page_smoothly(browser, direction='down', stay_time=10):
    scroll_script = f"""
    var distance = 50;  // Distance to scroll in each step
    var delay = 100;  // Delay in milliseconds between each scroll step
    var totalTime = {stay_time * 1000};  // Total time to stay on the page in milliseconds
    var elapsedTime = 0;  // Track the elapsed time

    function smoothScroll(currentHeight, maxHeight) {{
        window.scrollTo(0, currentHeight);
        if ((direction === 'down' && currentHeight < maxHeight) || (direction === 'up' && currentHeight > 0)) {{
            setTimeout(function() {{
                elapsedTime += delay;
                var newHeight = window.pageYOffset;
                if (direction === 'down') {{
                    if (newHeight === currentHeight || newHeight >= maxHeight - window.innerHeight) {{
                        smoothScroll(currentHeight + distance, maxHeight);
                    }} else {{
                        smoothScroll(newHeight, maxHeight);
                    }}
                }} else {{
                    if (newHeight === currentHeight || newHeight <= 0) {{
                        smoothScroll(currentHeight - distance, maxHeight);
                    }} else {{
                        smoothScroll(newHeight, maxHeight);
                    }}
                }}
            }}, delay);
        }} else if (elapsedTime < totalTime) {{
            setTimeout(function() {{
                elapsedTime += delay;
                smoothScroll(currentHeight, maxHeight);
            }}, delay);
        }}
    }}

    var direction = '{direction}';
    var maxHeight = document.body.scrollHeight;
    if (direction === 'down') {{
        smoothScroll(0, maxHeight);
    }} else {{
        smoothScroll(maxHeight, maxHeight);
    }}
    """
    browser.execute_script(scroll_script)
    time.sleep(stay_time)

# Example usage:
def scroll_page(browser):
    scroll_page_smoothly(browser, direction='down', stay_time=10)
    scroll_page_smoothly(browser, direction='up', stay_time=10)


def fetch_all_urls(browser):
    urls = set()
    elements = browser.find_elements(By.TAG_NAME, 'a')
    for element in elements:
        href = element.get_attribute('href')
        if href:
            parsed_url = urlparse(href)
            clean_url = parsed_url._replace(fragment='').geturl()
            urls.add(clean_url)
    return urls


def fetch_ip_using_proxy(proxy_host, proxy_port, proxy_user, proxy_pass):
    browser = get_webdriver_with_proxy(proxy_host, proxy_port, proxy_user, proxy_pass)
    
    try:
        site_url = "https://zabreezfirm.com"
        browser.get(site_url)
        time.sleep(3)
        scroll_page(browser)
        
        site_domain = urlparse(site_url).netloc
        visited_paths = set() 
        urls_to_visit = deque()  
        
        initial_urls = fetch_all_urls(browser)
        
        urls_to_visit.extend(url for url in initial_urls if urlparse(url).netloc == site_domain)
        
        while urls_to_visit and len(visited_paths) < 3:
            url = urls_to_visit.popleft()
            path = urlparse(url).path
            
            if path in visited_paths:
                continue 
            
            visited_paths.add(path)  
            
            print(url)
            browser.get(url)
            time.sleep(1)
            scroll_page(browser)
            
            new_urls = fetch_all_urls(browser)
            
            new_paths = {urlparse(url).path for url in new_urls if urlparse(url).netloc == site_domain}
            new_paths -= visited_paths
            
            urls_to_visit.extend(urljoin(site_url, path) for path in new_paths)
        
        all_urls = list(visited_paths)
    finally:
        browser.quit()
    
    return all_urls

def parse_proxy_string(proxy_string):
    proxy_parts = proxy_string.split(':')
    proxy_host = proxy_parts[0]
    proxy_port = proxy_parts[1]
    proxy_user = proxy_parts[2]
    proxy_pass = proxy_parts[3]
    return proxy_host, proxy_port, proxy_user, proxy_pass

proxy_strings = [
    # "na.dcnl7rw1.lunaproxy.net:12233:user-lu9597871-region-us-sessid-usjcupgngywww9mhst-sesstime-90:0502422374bd",
    # "na.dcnl7rw1.lunaproxy.net:12233:user-lu9597871-region-us-sessid-us7h46zg6eaycxplsr-sesstime-90:0502422374bd",
    # "na.dcnl7rw1.lunaproxy.net:12233:user-lu9597871-region-us-sessid-usrhhs6yfot28ulvmz-sesstime-90:0502422374bd",
    # "na.dcnl7rw1.lunaproxy.net:12233:user-lu9597871-region-us-sessid-uslms48eewcqenrasc-sesstime-90:0502422374bd",
    # "na.dcnl7rw1.lunaproxy.net:12233:user-lu9597871-region-us-sessid-uszfkpckiiwrbvkxjm-sesstime-90:0502422374bd",
    # "na.dcnl7rw1.lunaproxy.net:12233:user-lu9597871-region-us-sessid-uske9ar644qhkv0n53-sesstime-90:0502422374bd",
    # "na.dcnl7rw1.lunaproxy.net:12233:user-lu9597871-region-us-sessid-us82paol6f70o4xbi9-sesstime-90:0502422374bd",
    # "na.dcnl7rw1.lunaproxy.net:12233:user-lu9597871-region-us-sessid-usjqvzxbxw44hg4zyp-sesstime-90:0502422374bd",
    # "na.dcnl7rw1.lunaproxy.net:12233:user-lu9597871-region-us-sessid-us5lsnpk8xtzxoo90p-sesstime-90:0502422374bd",
    # "na.dcnl7rw1.lunaproxy.net:12233:user-lu9597871-region-us-sessid-usm7574k3sgb2w6oxs-sesstime-90:0502422374bd",
    "na.dcnl7rw1.lunaproxy.net:12233:user-lu9597871-region-us-sessid-us2x2ju610a7vnpc1t-sesstime-90:0502422374bd",
    # "na.dcnl7rw1.lunaproxy.net:12233:user-lu9597871-region-us-sessid-us2aij87zlyz6vz18h-sesstime-90:0502422374bd"
]

for proxy_string in proxy_strings:
    proxy_host, proxy_port, proxy_user, proxy_pass = parse_proxy_string(proxy_string)
    print(f"Using proxy {proxy_host}:{proxy_port}")
    ip_content = fetch_ip_using_proxy(
        proxy_host=proxy_host,
        proxy_port=proxy_port,
        proxy_user=proxy_user,
        proxy_pass=proxy_pass
    )
    print(ip_content)
