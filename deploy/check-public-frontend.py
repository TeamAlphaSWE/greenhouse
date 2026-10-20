"""Check the HTTP bridge transport after deployment, through the public proxy.

Only checks the bridge mechanics (session established, no native WebSocket
fallback) -- never the deployed app's layout or content. What a page
contains is that app's own concern, not this deploy gate's."""
import sys
import os
from playwright.sync_api import sync_playwright

url = sys.argv[1].rstrip('/')
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=os.environ.get('CHROME_PATH'))
    page = browser.new_page()
    sockets = []
    sessions = []
    page.on('websocket', lambda socket: sockets.append(socket.url))
    page.on('response', lambda response: sessions.append(response.status)
            if response.url == url + '/_greenhouse_transport/session' else None)
    try:
        page.goto(url, timeout=60000)
        assert 200 in sessions, 'Streamlit did not connect through the HTTP bridge'
        assert not sockets, 'Browser attempted a native WebSocket'
        print('HTTP bridge transport verified:', url)
    finally:
        browser.close()
