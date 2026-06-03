from playwright.sync_api import sync_playwright
import time
import os
import requests

# Trigger paradox to move to exploration phase immediately
requests.post("http://127.0.0.1:8765/api/state/trigger_paradox")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://127.0.0.1:8765/')

    print("Page loaded")
    time.sleep(1)

    # Move mouse around to trigger _renderCursor
    canvas_rect = page.locator("#konva-mount").bounding_box()
    if canvas_rect:
        center_x = canvas_rect["x"] + canvas_rect["width"] / 2
        center_y = canvas_rect["y"] + canvas_rect["height"] / 2
        page.mouse.move(center_x, center_y)
        time.sleep(0.5)
        page.mouse.move(center_x + 50, center_y + 50)
        time.sleep(0.5)
        page.mouse.move(center_x - 50, center_y - 50)
        time.sleep(0.5)

    os.makedirs('verification', exist_ok=True)
    screenshot_path = 'verification/frontend_test.png'
    page.screenshot(path=screenshot_path)
    browser.close()

    print(f"Screenshot saved to {screenshot_path}")
