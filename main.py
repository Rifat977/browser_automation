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
import undetected_chromedriver as uc


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

# def get_webdriver_with_proxy(proxy_host, proxy_port, proxy_user, proxy_pass):
#     chrome_options = webdriver.ChromeOptions()
#     chrome_options.add_argument(f'--proxy-server=http://{proxy_host}:{proxy_port}')

#     plugin_path = create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass)
#     chrome_options.add_extension(plugin_path)

#     service = Service(ChromeDriverManager().install())
#     browser = webdriver.Chrome(service=service, options=chrome_options)
    
#     return browser

def get_webdriver_with_proxy(proxy_host, proxy_port, proxy_user, proxy_pass):
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument(f'--proxy-server=http://{proxy_host}:{proxy_port}')

    plugin_path = create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass)
    chrome_options.add_extension(plugin_path)

    # Set the custom path to ChromeDriver
    chrome_driver_path = '/home/rifat/.wdm/drivers/chromedriver/linux64/127.0.6533.119/chromedriver-linux64/chromedriver'
    service = Service(chrome_driver_path)
    
    # Create the browser instance using the custom ChromeDriver path
    browser = webdriver.Chrome(service=service, options=chrome_options)
    
    return browser


def scroll_page_smoothly(browser, direction='down', pause_time=2):
    scroll_script = f"""
    var distance = window.innerHeight / 4;  // Distance to scroll in each step (half the viewport height)
    var delay = 50;  // Delay in milliseconds between each scroll step
    var pauseTime = {pause_time * 550};  // Pause time in milliseconds after each section scroll
    var totalHeight = document.body.scrollHeight;
    var sections = Math.ceil(totalHeight / distance);  // Number of sections to scroll
    var totalTime = sections * pauseTime;  // Total time to stay on the page

    function smoothScroll(currentHeight, section) {{
        if (section < sections) {{
            window.scrollTo(0, currentHeight);
            setTimeout(function() {{
                if (direction === 'down') {{
                    currentHeight += distance;
                }} else {{
                    currentHeight -= distance;
                }}
                setTimeout(function() {{
                    smoothScroll(currentHeight, section + 1);
                }}, delay);
            }}, pauseTime);
        }}
    }}

    var direction = '{direction}';
    if (direction === 'down') {{
        smoothScroll(0, 0);
    }} else {{
        smoothScroll(totalHeight, 0);
    }}
    """
    browser.execute_script(scroll_script)
    sections = browser.execute_script("return Math.ceil(document.body.scrollHeight / (window.innerHeight / 2));")
    total_stay_time = sections * pause_time
    time.sleep(total_stay_time)

def scroll_page(browser):
    scroll_page_smoothly(browser, direction='down', pause_time=1)
    scroll_page_smoothly(browser, direction='up', pause_time=1)



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
        site_url = "https://dailycombotoday.com"
        browser.get(site_url)
        time.sleep(1)
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
            
            # Open the URL in a new tab
            browser.execute_script("window.open('');")
            browser.switch_to.window(browser.window_handles[-1])
            browser.get(url)
            time.sleep(1)
            scroll_page(browser)
            
            new_urls = fetch_all_urls(browser)
            new_paths = {urlparse(url).path for url in new_urls if urlparse(url).netloc == site_domain}
            new_paths -= visited_paths
            
            urls_to_visit.extend(urljoin(site_url, path) for path in new_paths)
            
            # Close the tab and switch back to the original tab
            # browser.close()
            # browser.switch_to.window(browser.window_handles[0])
        
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
"gw.dataimpulse.com:10000:ee9f710b8d0307f3ce1a__cr.us:6509bead40a27cc8",
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
