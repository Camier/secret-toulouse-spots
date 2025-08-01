#!/usr/bin/env python3
"""Validate the Secret Toulouse Spots map using Playwright"""

import asyncio
import os


async def validate_map():
    print("🎭 Starting Playwright validation...")

    # First, let's check if the server is running
    import subprocess

    # Kill any existing servers on our ports
    subprocess.run(["pkill", "-f", "python.*8890"], capture_output=True)

    # Start the server
    server_process = subprocess.Popen(
        ["python3", "-m", "http.server", "8890", "--bind", "127.0.0.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Give server time to start
    await asyncio.sleep(2)

    try:
        # Import playwright
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()

            print("\n📍 Testing Enhanced Map...")

            # Navigate to enhanced map
            await page.goto("http://localhost:8890/enhanced-map.html")

            # Wait for map to load
            await page.wait_for_selector("#map", timeout=10000)
            print("✅ Map container loaded")

            # Wait for loading overlay to disappear
            await page.wait_for_selector("#loading", state="hidden", timeout=30000)
            print("✅ Data loaded successfully")

            # Check stats are populated
            total_spots = await page.text_content("#totalSpots")
            hidden_spots = await page.text_content("#hiddenSpots")
            exact_spots = await page.text_content("#exactSpots")

            print(f"\n📊 Statistics:")
            print(f"  - Total spots: {total_spots}")
            print(f"  - Hidden spots: {hidden_spots}")
            print(f"  - Exact coordinates: {exact_spots}")

            # Take screenshot of initial view
            await page.screenshot(path="validation_1_initial.png")
            print("\n📸 Screenshot 1: Initial map view saved")

            # Test search functionality
            await page.fill("#searchInput", "grotte")
            await page.wait_for_timeout(1000)
            await page.screenshot(path="validation_2_search.png")
            print("📸 Screenshot 2: Search for 'grotte' saved")

            # Clear search
            await page.click("#clearSearch")

            # Test type filters
            type_filters = await page.query_selector_all('[data-filter="type"]')
            if type_filters:
                # Click on cave filter
                for filter_chip in type_filters:
                    text = await filter_chip.text_content()
                    if "Grotte" in text:
                        await filter_chip.click()
                        await page.wait_for_timeout(1000)
                        await page.screenshot(path="validation_3_cave_filter.png")
                        print("📸 Screenshot 3: Cave filter applied")
                        break

            # Test visibility filter
            await page.click('[data-filter="visibility"][data-value="hidden"]')
            await page.wait_for_timeout(1000)
            await page.screenshot(path="validation_4_hidden_spots.png")
            print("📸 Screenshot 4: Hidden spots filter applied")

            # Reset to all
            await page.click('[data-filter="visibility"][data-value="all"]')

            # Test distance filter
            await page.fill("#distanceFilter", "50")
            await page.wait_for_timeout(1000)
            distance_value = await page.text_content("#distanceValue")
            print(f"\n🎯 Distance filter set to: {distance_value}")
            await page.screenshot(path="validation_5_distance_filter.png")
            print("📸 Screenshot 5: 50km distance filter applied")

            # Click on a marker (if visible)
            markers = await page.query_selector_all(".leaflet-marker-icon")
            if markers and len(markers) > 0:
                await markers[0].click()
                await page.wait_for_selector(".leaflet-popup", timeout=5000)
                await page.wait_for_timeout(500)
                await page.screenshot(path="validation_6_popup.png")
                print("📸 Screenshot 6: Marker popup displayed")

            # Test perimeter toggle
            perimeter_checkbox = await page.query_selector("#showPerimeters")
            if perimeter_checkbox:
                is_checked = await perimeter_checkbox.is_checked()
                if is_checked:
                    await perimeter_checkbox.click()
                    await page.wait_for_timeout(1000)
                    await page.screenshot(path="validation_7_no_perimeters.png")
                    print("📸 Screenshot 7: Perimeters hidden")

            # Final full view
            await page.click("#refreshBtn")
            await page.wait_for_selector("#loading", state="hidden", timeout=30000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path="validation_8_final_view.png", full_page=True)
            print("📸 Screenshot 8: Final full page view")

            print("\n✅ All validation tests passed!")
            print(f"\n📁 Screenshots saved in: {os.getcwd()}")

            # Keep browser open for manual inspection
            print("\n👀 Browser will stay open for 30 seconds for manual inspection...")
            await page.wait_for_timeout(30000)

            await browser.close()

    finally:
        # Stop the server
        server_process.terminate()
        print("\n🛑 Server stopped")


if __name__ == "__main__":
    asyncio.run(validate_map())
