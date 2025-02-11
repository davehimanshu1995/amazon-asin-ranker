from flask import Flask, request, render_template, send_file
import pandas as pd
import os
import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor
import threading

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloads"
NUM_THREADS = 3
MAX_RETRIES = 3
DELAY_SECONDS = [2, 3, 4]

# Use a cloud-based Chrome WebDriver
def create_driver():
    """Create a Selenium WebDriver instance (Runs on Cloud, No Installation Needed)."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-popup-blocking")

    driver = webdriver.Chrome(options=options)
    return driver

def get_amazon_ranking(asin):
    """Fetch Amazon ranking."""
    driver = create_driver()
    url = f"https://www.amazon.in/dp/{asin}"
    print(f"🔍 Fetching ranking for ASIN: {asin}")

    try:
        for attempt in range(MAX_RETRIES):
            try:
                driver.get(url)
                ranking = "Not Found"

                # Try extracting ranking from <ul>
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//ul[contains(@class, 'zg_hrsr')]"))
                    )
                    rank_elements = driver.find_elements(By.XPATH, "//ul[contains(@class, 'zg_hrsr')]//li//span[@class='a-list-item']")
                    rankings = [rank.text.strip() for rank in rank_elements]
                    if rankings:
                        ranking = ", ".join(rankings)
                except:
                    pass

                # Try extracting ranking from <table>
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//table[@id='productDetails_detailBullets_sections1']"))
                    )
                    rank_elements = driver.find_elements(By.XPATH, "//table[@id='productDetails_detailBullets_sections1']//tr[th[contains(text(), 'Best Sellers Rank')]]/td/span")
                    rankings = [rank.text.strip() for rank in rank_elements]
                    if rankings:
                        ranking = ", ".join(rankings)
                except:
                    pass

                if ranking != "Not Found":
                    print(f"✅ ASIN: {asin} - Ranking: {ranking}")
                    return ranking
                
                print(f"⚠️ ASIN {asin}: Ranking not found, retrying... ({attempt+1}/{MAX_RETRIES})")

            except Exception as e:
                print(f"⚠️ ASIN {asin} failed on attempt {attempt+1}: {e}")

            time.sleep(random.choice(DELAY_SECONDS))

        return "Not Found"

    finally:
        driver.quit()

def process_asin(asin, df):
    """Fetch ASIN ranking and update DataFrame."""
    ranking = get_amazon_ranking(asin)
    df.loc[df['ASIN'] == asin, 'Ranking'] = ranking

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file = request.files["file"]
        if file:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            
            df = pd.read_excel(file_path)
            asins = df["ASIN"].dropna().tolist()

            with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
                executor.map(lambda asin: process_asin(asin, df), asins)

            output_file = os.path.join(DOWNLOAD_FOLDER, "asin_ranking.xlsx")
            df.to_excel(output_file, index=False)
            
            return send_file(output_file, as_attachment=True)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
