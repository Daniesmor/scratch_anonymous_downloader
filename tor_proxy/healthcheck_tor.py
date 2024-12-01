import time
import requests
import sys

proxies = {
    'http': 'socks5h://tor_proxy:9050',
    'https': 'socks5h://tor_proxy:9050'
}

def check_proxy():
    try:
        print("Checking Tor proxy status...")
        requests.get("https://httpbin.org/ip", proxies=proxies, timeout=5)
        sys.exit(0)
    except Exception as e:
        print(f"Tor proxy health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_proxy()