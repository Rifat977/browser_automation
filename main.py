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
import threading
import queue

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

# def get_webdriver_with_proxy(proxy_host, proxy_port, proxy_user, proxy_pass):
#     # Initialize Chrome options
#     chrome_options = webdriver.ChromeOptions()
#     chrome_options.add_argument(f'--proxy-server=http://{proxy_host}:{proxy_port}')
    
#     # Create and add proxy auth extension
#     plugin_path = create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass)
#     if plugin_path:
#         chrome_options.add_extension(plugin_path)

#     # Initialize undetected Chrome with the specified options
#     service = Service(ChromeDriverManager().install())
#     browser = webdriver.Chrome(service=service, options=chrome_options)
    
#     return browser

def get_webdriver_with_proxy(proxy_host, proxy_port, proxy_user, proxy_pass):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f'--proxy-server=https://{proxy_host}:{proxy_port}')
    
    # Headless mode options
    chrome_options.add_argument('--head')
    chrome_options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
    chrome_options.add_argument('--no-sandbox')    # Bypass OS security model
    chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
    chrome_options.add_argument('--remote-debugging-port=9222')  # Debugging port
    chrome_options.add_argument('--window-size=1920x1080')  # Set the window size

    # Enable logging
    chrome_options.add_argument('--enable-logging')
    chrome_options.add_argument('--v=1')  # Set log level to INFO

    # If using a proxy authentication extension
    plugin_path = create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass)
    chrome_options.add_extension(plugin_path)

    # Ensure you provide the correct path to the ChromeDriver executable
    chrome_driver_path = './chromedriver'  # Update this path if necessary
    service = Service(chrome_driver_path)

    try:
        browser = webdriver.Chrome(service=service, options=chrome_options)
        return browser
    except Exception as e:
        print(f"Failed to start Chrome with error: {e}")
        return None


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


def parse_proxy_string(proxy_string):
    proxy_parts = proxy_string.split(':')
    proxy_host = proxy_parts[0]
    proxy_port = proxy_parts[1]
    proxy_user = proxy_parts[2]
    proxy_pass = proxy_parts[3]
    return proxy_host, proxy_port, proxy_user, proxy_pass

def fetch_ip_using_proxy(proxy_host, proxy_port, proxy_user, proxy_pass, browser_id, lock, closed_browsers):
    browser = get_webdriver_with_proxy(proxy_host, proxy_port, proxy_user, proxy_pass)

    with open("data/links.txt", "r") as file:
        site_urls = file.readlines()
    
    completed_count = 0
    
    try:
        first_url = "https://whatismyip.com"
        browser.get(first_url)
        
        for url in site_urls:
            browser.execute_script("window.open('');")
            browser.switch_to.window(browser.window_handles[-1])
            browser.get(url.strip())
            time.sleep(1)
            scroll_page(browser)
            completed_count += 1
            print(f"Browser {browser_id}: Completed {completed_count}/{len(site_urls)} - {url.strip()}")
            
    finally:
        browser.quit()
        with lock:
            closed_browsers.append(browser_id)
            print(f"Browser {browser_id} closed. Total closed: {len(closed_browsers)}")


def run_browsers_with_proxies(proxy_list, num_browsers):
    threads = []
    lock = threading.Lock()
    closed_browsers = []
    
    proxy_batches = [proxy_list[i:i+num_browsers] for i in range(0, len(proxy_list), num_browsers)]
    
    for batch_num, proxy_batch in enumerate(proxy_batches, start=1):
        print(f"Starting batch {batch_num} with {len(proxy_batch)} proxies")

        for i, proxy_string in enumerate(proxy_batch):
            proxy_string = proxy_string.strip()
            proxy_host, proxy_port, proxy_user, proxy_pass = parse_proxy_string(proxy_string)

            thread = threading.Thread(target=fetch_ip_using_proxy, 
                                      args=(proxy_host, proxy_port, proxy_user, proxy_pass, i + 1 + (batch_num - 1) * num_browsers, lock, closed_browsers))
            threads.append(thread)
            thread.start()

        # Wait for all threads in the batch to complete
        for thread in threads:
            thread.join()

        print(f"Batch {batch_num} completed.")

    print(f"All browsers using {len(proxy_list)} proxies completed.")


# Main execution
with open("data/proxy.txt", "r") as file:
    proxy_strings = file.readlines()

num_browsers_to_run = int(input("How many browsers do you want to open at the same time: "))

run_browsers_with_proxies(proxy_strings, num_browsers_to_run)