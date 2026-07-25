# ============================================================
# USA Food Image Dataset Collection using Bing Images
# ------------------------------------------------------------
# This script downloads HIGH-RESOLUTION images for each USA
# dish using Selenium and saves them into separate folders.
#
# Key change vs. the original script:
#   - Instead of reading the small "img.mimg" thumbnail src,
#     it reads the parent "a.iusc" element's "m" attribute,
#     which contains a JSON blob with the ORIGINAL image URL
#     (murl) and its real width/height (ow/oh). This lets us
#     filter for high-resolution images BEFORE downloading.
#   - After downloading, Pillow re-checks the actual image
#     dimensions as a second safety net (some murl links can
#     be stale/redirected/mismatched), and discards anything
#     under the threshold.
# ============================================================

import os
import io
import json
import time
import requests
from urllib.parse import quote

from tqdm import tqdm
from PIL import Image

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    InvalidSessionIdException,
    WebDriverException,
)


# ============================================================
# Dataset Directory
# ============================================================

DATASET_DIR = "USA_Food_Collection"
os.makedirs(DATASET_DIR, exist_ok=True)


# ============================================================
# Dishes to Collect
# ------------------------------------------------------------
# Key   -> dish name (used for search query + folder name)
# Value -> max number of images to download for that dish
#
# Edit this dictionary with whichever dishes / counts you want.
# ============================================================

USA_DISHES = {
    # --- Fast food / burgers / sandwiches ---
    "Cheeseburger": 150,
    "Classic Hamburger":   150,
    "French Fries":   150,
    "Hot Dog":   150,
    "Philly Cheesesteak":   150,
    "Club Sandwich":   150,
    "Grilled Cheese Sandwich":   150,
    "Reuben Sandwich":   150,
    "Turkey Sandwich":   150,
    "Pulled Pork Sandwich":   150,

    # --- Chicken ---
    "Fried Chicken":   150,
    "Buffalo Wings":   150,
    "Chicken Tenders":   150,
    "Chicken Nuggets":   150,
    "BBQ Chicken":   150,

    # --- Pizza ---
    "Pepperoni Pizza":   150,
    "Cheese Pizza":   150,
    "Chicago Deep Dish Pizza":   150,

    # --- BBQ / Southern / comfort food ---
    "BBQ Ribs":   150,
    "Meatloaf":   150,
    "Mac and Cheese":   150,
    "Biscuits and Gravy":   150,
    "Cornbread":   150,
    "Fried Catfish":   150,
    "Jambalaya":   150,

    # --- Seafood ---
    "Clam Chowder":   150,
    "Lobster Roll":   150,
    "Fish and Chips":   150,
    "Fried Shrimp":   150,
    "Shrimp Scampi":   150,

    # --- Mexican-American ---
    "Beef Tacos":   150,
    "Burrito Bowl":   150,
    "Nachos":   150,
    "Chicken Quesadilla":   150,
    "Chili Con Carne":   150,

    # --- Italian-American ---
    "Spaghetti and Meatballs":   150,
    "Fettuccine Alfredo":   150,
    "Lasagna":   150,
    "Chicken Parmesan":   150,

    # --- Salads / bowls ---
    "Caesar Salad":   150,
    "Cobb Salad":   150,
    "Chicken Rice Bowl":   150,

    # --- Breakfast ---
    "Pancakes":   150,
    "Waffles":   150,
    "French Toast":   150,
    "Bacon and Eggs":   150,
    "Omelette":   150,

    # --- Sides / potatoes ---
    "Mashed Potatoes":   150,
    "Baked Potato":   150,

    # --- Desserts ---
    "Apple Pie":   150,
    "Cheesecake":   150,
    "Chocolate Chip Cookies":   150,
    "Ice Cream Sundae":   150,
    "Donuts":   150,
}




# ============================================================
# Resolution Settings (adjust these to taste)
# ============================================================

MIN_WIDTH = 800     # minimum acceptable width in pixels
MIN_HEIGHT = 600    # minimum acceptable height in pixels


# ============================================================
# Chrome Driver Configuration + Crash-Resistant Launcher
# ============================================================
#
# NOTE: We no longer use webdriver_manager. As of Selenium 4.6+,
# Selenium has its own built-in "Selenium Manager" that auto
# detects your installed Chrome version and downloads a MATCHING
# chromedriver automatically. webdriver_manager can sometimes
# fetch a chromedriver version that doesn't match your local
# Chrome build, which silently crashes the browser mid-run and
# causes InvalidSessionIdException. Just leave Service() empty
# and Selenium handles it.

def build_driver():
    """
    Creates a fresh, stability-tuned Chrome WebDriver instance.
    Called at startup, and again automatically if the browser
    session ever dies mid-scrape.
    """

    options = webdriver.ChromeOptions()

    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")

    # Extra stability flags — these reduce the chance of Chrome
    # crashing/hanging during long headless scraping sessions.
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=Translate,BackForwardCache")
    options.add_argument("--disable-crash-reporter")
    options.add_argument("--disable-in-process-stack-traces")
    options.add_argument("--log-level=3")

    # Uncomment ONLY if running in Google Colab
    # options.binary_location = "/usr/bin/google-chrome"

    new_driver = webdriver.Chrome(service=Service(), options=options)
    new_driver.set_page_load_timeout(60)

    return new_driver


driver = build_driver()


# ============================================================
# Request Headers
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0 Safari/537.36"
    )
}


# ============================================================
# Download + Resolution Verification Function
# ============================================================

def download_image(url, save_path, min_width=MIN_WIDTH, min_height=MIN_HEIGHT):
    """
    Downloads an image from the given URL, and only keeps it
    if its actual dimensions meet the minimum resolution
    requirement. Returns True if saved, False otherwise.
    """

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        if (
            response.status_code == 200
            and "image" in response.headers.get("Content-Type", "")
        ):

            content = response.content

            # ---- Verify real dimensions before saving ----
            try:
                with Image.open(io.BytesIO(content)) as img:
                    width, height = img.size

                    if width < min_width or height < min_height:
                        return False

                    # Convert to RGB so we can always save as .jpg
                    # (handles PNG/WEBP/CMYK/palette images safely)
                    if img.mode != "RGB":
                        img = img.convert("RGB")

                    img.save(save_path, "JPEG", quality=95)
                    return True

            except Exception:
                # Not a valid/openable image
                return False

    except Exception:
        pass

    return False


# ============================================================
# Extract Original-Resolution Image Candidates from a Page
# ============================================================

def get_high_res_candidates(driver, min_width=MIN_WIDTH, min_height=MIN_HEIGHT):
    """
    Parses Bing's "iusc" containers to pull the original image
    URL (murl) plus its real width/height (ow/oh) from the
    embedded JSON, so we can filter by resolution before ever
    downloading anything.
    """

    candidates = []

    containers = driver.find_elements(By.CSS_SELECTOR, "a.iusc")

    for container in containers:

        meta = container.get_attribute("m")

        if not meta:
            continue

        try:
            data = json.loads(meta)
        except (ValueError, TypeError):
            continue

        murl = data.get("murl")
        width = data.get("ow")
        height = data.get("oh")

        if not murl or not murl.startswith("http"):
            continue

        # Filter by resolution reported by Bing BEFORE downloading
        if width and height:
            if int(width) < min_width or int(height) < min_height:
                continue

        candidates.append((murl, width, height))

    return candidates


# ============================================================
# Scrape Images for Each Dish
# ============================================================

MAX_RETRIES_PER_DISH = 2  # how many times to retry a dish if the browser crashes

for dish, max_images in USA_DISHES.items():

    print(f"\n{'='*60}")
    print(f"Collecting Images : {dish}")
    print(f"{'='*60}")

    dish_folder = os.path.join(DATASET_DIR, dish)
    os.makedirs(dish_folder, exist_ok=True)

    attempt = 0

    while attempt <= MAX_RETRIES_PER_DISH:

        try:
            # "qft=+filterui:imagesize-large" tells Bing itself to bias
            # results toward large images, which reduces wasted scrolls.
            search_query = quote(f"{dish} USA food")

            url = (
                f"https://www.bing.com/images/search?q={search_query}"
                f"&qft=+filterui:imagesize-large"
            )

            driver.get(url)

            time.sleep(3)

            # ------------------------------------------------
            # Scroll to load more images
            # ------------------------------------------------

            last_height = driver.execute_script(
                "return document.body.scrollHeight"
            )

            for _ in range(20):

                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )

                time.sleep(2)

                new_height = driver.execute_script(
                    "return document.body.scrollHeight"
                )

                if new_height == last_height:
                    break

                last_height = new_height

            # ------------------------------------------------
            # Collect high-resolution image candidates
            # ------------------------------------------------

            candidates = get_high_res_candidates(driver)

            print(f"Found {len(candidates)} candidates >= {MIN_WIDTH}x{MIN_HEIGHT}")

            downloaded = 0
            urls_seen = set()

            # ------------------------------------------------
            # Download Images
            # ------------------------------------------------

            for murl, width, height in tqdm(candidates):

                if downloaded >= max_images:
                    break

                if murl in urls_seen:
                    continue

                urls_seen.add(murl)

                filename = os.path.join(
                    dish_folder,
                    f"{dish.replace(' ', '_')}_{downloaded+1}.jpg"
                )

                success = download_image(murl, filename)

                if success:
                    downloaded += 1

            print(f"Downloaded {downloaded} high-resolution images")

            # Success — move on to the next dish
            break

        except (InvalidSessionIdException, WebDriverException) as e:

            attempt += 1

            print(f"⚠️  Browser session error on '{dish}': {e}")
            print(f"   Restarting Chrome (attempt {attempt}/{MAX_RETRIES_PER_DISH})...")

            try:
                driver.quit()
            except Exception:
                pass  # session is already dead, nothing to clean up

            driver = build_driver()

            if attempt > MAX_RETRIES_PER_DISH:
                print(f"❌ Giving up on '{dish}' after repeated crashes. Skipping.")


# ============================================================
# Cleanup
# ============================================================

try:
    driver.quit()
except Exception:
    pass

print("\n✅ Dataset Collection Completed Successfully!")

