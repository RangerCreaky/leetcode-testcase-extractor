import time
import os
import undetected_chromedriver as uc
from csv import DictReader
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def dump_leetcode_dom():
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument("--window-size=1920,1080")
    options.add_argument('start-maximized')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')

    driver = uc.Chrome(options=options, version_main=151)
    wait = WebDriverWait(driver, 15)

    print("Navigating to login page...")
    driver.get("https://leetcode.com/accounts/login/")
    time.sleep(3)

    print("Loading cookies...")
    filename = "main/leetcode_cookies.csv"
    if os.path.isfile(filename):
        with open(filename, 'r') as file:
            csv_reader = DictReader(file)
            for row in csv_reader:
                clean_row = {key.strip(): value.strip() for key, value in row.items() if key!=""}
                driver.add_cookie(clean_row)
    else:
        print("No cookies file found!")
        driver.quit()
        return

    print("Navigating to problem page...")
    driver.get("https://leetcode.com/problems/two-sum/")
    time.sleep(10) # wait for page to fully load

    print("Dumping problem page HTML...")
    with open("problem_page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    print("Attempting to find and click Submit button...")
    try:
        # Try to find a button containing 'Submit'
        submit_btn = driver.find_element(By.XPATH, "//button[contains(., 'Submit')]")
        submit_btn.click()
        print("Clicked submit. Waiting for result...")
        time.sleep(10)
        
        print("Dumping result page HTML...")
        with open("result_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    except Exception as e:
        print("Could not submit:", e)

    driver.quit()
    print("Done.")

if __name__ == "__main__":
    dump_leetcode_dom()
