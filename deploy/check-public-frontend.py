"""Check actual Streamlit rendering after deployment, through the public proxy."""
import sys
import os
from playwright.sync_api import sync_playwright, expect

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
        expect(page.locator('[data-testid="stMain"] h1')).to_be_visible(timeout=60000)
        assert 200 in sessions, 'Streamlit did not connect through the HTTP bridge'
        assert not sockets, 'Browser attempted a native WebSocket'
        print('Public Streamlit page rendered through HTTP transport:', url)
    finally:
        browser.close()
