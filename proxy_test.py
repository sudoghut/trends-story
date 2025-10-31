import os
import urllib.request

print("--- Checking Environment Variables from Python's perspective ---")
# os.environ is how Python sees all environment variables
print(f"HTTP_PROXY: {os.environ.get('HTTP_PROXY')}")
print(f"HTTPS_PROXY: {os.environ.get('HTTPS_PROXY')}")

print("\n--- Checking what proxies urllib automatically detects ---")
# getproxies() shows what urllib will use by default
print(urllib.request.getproxies())