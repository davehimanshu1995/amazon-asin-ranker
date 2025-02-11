import pandas as pd
import os
import threading
import random
import time
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 🔹 CONFIGURATION
INPUT_FILE = 'asin.xlsx'  # Path to your input file in GitHub repo
OUTPUT_FILE = 'output_asin.xlsx'  # Output file saved in GitHub repo
NUM_THREADS = 3  # Adjust threads based on ASIN count (3 for safer bulk fetching)
MAX_RETRIES = 3  # Retries if ASIN ranking is not found
DELAY_SECONDS = [2, 3, 4]  # Randomized delay between requests (prevents blocking)

# 🔹 Rotate User-Agents (Amazon blocking prevention)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
]

# Thread Lock for Writing to Excel
lock = threading.Lock()

def create_driver():
    """Create a new WebDriver instance with a random User-Agent."""
    service = ChromeService(executable_path='/usr/bin/chromedriver')  # Path to chromedriver
    options = ChromeOptions()
    options.add_argument("--headless")  # Enable headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_argument("--blink-settings=imagesEnabled=false")  # Disable images
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-infobars")
    
    # 🔹 Randomize User-Agent
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    
    return webdriver.Chrome(service=service, options=options)

def get_amazon_ranking(asin):
    """Fetch rankings from both <ul> and <table> formats while avoiding detection."""
    driver = create_driver()
    url = f"https://www.amazon.in/dp/{asin}"
    print(f"🔍 Fetching ranking for ASIN: {asin}")

    try:
        for attempt in range(MAX_RETRIES):
            try:
                driver.get(url)

                ranking = "Not Found"

                # 🔹 Try extracting rankings from <ul> format
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//ul[contains(@class, 'zg_hrsr')]"))
                    )
                    rank_elements = driver.find_elements(By.XPATH, "//ul[contains(@class, 'zg_hrsr')]//li//span[@class='a-list-item']")
                    rankings = [rank.text.strip() for rank in rank_elements]

                    if rankings:
                        ranking = ", ".join(rankings)
                except:
                    pass  # If not found, try next method

                # 🔹 Try extracting rankings from <table> format
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//table[@id='productDetails_detailBullets_sections1']"))
                    )
                    rank_elements = driver.find_elements(By.XPATH, "//table[@id='productDetails_detailBullets_sections1']//tr[th[contains(text(), 'Best Sellers Rank')]]/td/span")
                    rankings = [rank.text.strip() for rank in rank_elements]

                    if rankings:
                        ranking = ", ".join(rankings)
                except:
                    pass  # If not found, ranking remains "Not Found"

                if ranking != "Not Found":
                    print(f"✅ ASIN: {asin} - Ranking: {ranking}")
                    return ranking
                
                # 🔹 If ranking not found, retry
                print(f"⚠️ ASIN {asin}: Ranking not found, retrying... ({attempt+1}/{MAX_RETRIES})")

            except Exception as e:
                print(f"⚠️ ASIN {asin} failed on attempt {attempt+1}: {e}")
            
            # 🔹 Randomized delay between attempts to prevent blocking
            time.sleep(random.choice(DELAY_SECONDS))

        print(f"❌ ASIN: {asin} - Ranking not found after {MAX_RETRIES} attempts")
        return "Not Found"

    finally:
        driver.quit()  # Close WebDriver

def process_asin(asin, df):
    """Process each ASIN in a separate thread."""
    ranking = get_amazon_ranking(asin)
    
    with lock:  # Prevents multiple threads from writing at the same time
        df.loc[df['ASIN'] == asin, 'Ranking'] = ranking

def main():
    """Main function to process ASINs using multi-threading."""
    print(f"📂 Checking file path: {INPUT_FILE}")

    if not os.path.exists(INPUT_FILE):
        print(f"❌ ERROR: File '{INPUT_FILE}' not found!")
        return

    try:
        df = pd.read_excel(INPUT_FILE)

        if "ASIN" not in df.columns:
            print("❌ ERROR: Column 'ASIN' not found in the input file!")
            return

        asins = df["ASIN"].dropna().tolist()

        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            executor.map(lambda asin: process_asin(asin, df), asins)

        df.to_excel(OUTPUT_FILE, index=False)
        print(f"✅ Rankings saved to {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    main()
