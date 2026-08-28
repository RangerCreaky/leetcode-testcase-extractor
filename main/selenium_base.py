import os
import platform
import re
import subprocess
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

class SeleniumBase:
    # Initialize
    def __init__(self, waitTime):
        driver_kind = os.environ.get("LEETCODE_DRIVER", "undetected").lower()
        if driver_kind == "undetected":
            import undetected_chromedriver as uc
            options = uc.ChromeOptions()
        elif driver_kind == "selenium":
            options = Options()
        else:
            raise ValueError("LEETCODE_DRIVER must be 'undetected' or 'selenium'")

        headless = os.environ.get("LEETCODE_HEADLESS", "0")
        if headless != "0":
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
    
        options.add_argument("--window-size=1920,1080")
        options.add_argument('start-maximized')

        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        if os.environ.get("CHROME_BIN"):
            options.binary_location = os.environ["CHROME_BIN"]

        if driver_kind == "undetected":
            driver_options = {"options": options, "use_subprocess": True}
            if os.environ.get("CHROME_VERSION_MAIN"):
                driver_options["version_main"] = int(os.environ["CHROME_VERSION_MAIN"])
            else:
                chrome_binary = options.binary_location or uc.find_chrome_executable()
                try:
                    version_output = subprocess.check_output(
                        [chrome_binary, "--version"], text=True, timeout=10
                    )
                    version_match = re.search(r"\b(\d+)\.", version_output)
                    if version_match:
                        driver_options["version_main"] = int(version_match.group(1))
                except (OSError, subprocess.SubprocessError):
                    pass
            self.driver = uc.Chrome(**driver_options)
        else:
            self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, waitTime)
        self.modifier_key = Keys.COMMAND if platform.system() == "Darwin" else Keys.CONTROL
        self.screenshotFile = "screenshots/" + time.strftime("%Y%m%d-%H%M%S") + "/"
        os.makedirs(self.screenshotFile, exist_ok=True)
    
    # Debug functions
    def screenshot(self, filename):
        self.driver.save_screenshot(self.screenshotFile + filename)
    
    def save_html(self, filename):
        with open(self.screenshotFile + filename, "w") as file:
            file.write(self.driver.page_source)

    # Getters (with waiting)
    def get_by_text(self, element_type, text):
        xpath = "//" + element_type + "[contains(., '" + text + "')]"
        self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        return self.driver.find_element(By.XPATH, xpath)
    
    def get_by_id(self, id):
        self.wait.until(EC.element_to_be_clickable((By.ID, id)))
        return self.driver.find_element(By.ID, id)
    
    def get_by_href(self, href):
        xpath = "//a[@href='" + href + "']"
        self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        return self.driver.find_element(By.XPATH, xpath)
    
    def get_by_link_text(self, text):
        self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, text)))
        return self.driver.find_element(By.LINK_TEXT, text)
    
    def get_by_xpath(self, xpath):
        self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        return self.driver.find_element(By.XPATH, xpath)
    
    def get_by_class(self, class_name):
        self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, class_name)))
        return self.driver.find_element(By.CLASS_NAME, class_name)
    
    # Operators
    def click(self, element):
        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)
    
    def send_keys(self, element, keys):
        self.click(element)
        self.driver.switch_to.active_element.send_keys(keys)
    
    # Clipboard Operators
    def get_clipboard(self):
        # add input field
        self.driver.execute_script('''
        var tempInput = document.createElement("textarea");
        tempInput.id = "tempInput";
        document.body.appendChild(tempInput);''')

        # paste into it and get contents
        input_field = self.get_by_id("tempInput")
        input_field.send_keys(self.modifier_key, 'v')
        content = input_field.get_attribute('value')

        # remove field
        self.driver.execute_script("arguments[0].remove()", input_field)
        return content
    
    def set_clipboard(self, text):
        self.driver.execute_script('''
            var tempInput = document.createElement("textarea");
            tempInput.id = "tempInput";
            tempInput.value = arguments[0];
            document.body.appendChild(tempInput);
        ''', text)

        input_field = self.get_by_id("tempInput")
        input_field.send_keys(self.modifier_key, 'a')
        input_field.send_keys(self.modifier_key, 'c')

        # remove field
        self.driver.execute_script("arguments[0].remove()", input_field)
    
    def pause(self, seconds):
        print("pausing for " + str(seconds) + " seconds", flush=True)
        time.sleep(seconds)

    def visible_element(self, by, locator, root=None):
        search_root = root or self.driver
        for element in search_root.find_elements(by, locator):
            try:
                if element.is_displayed():
                    return element
            except Exception:
                continue
        return None

    def quit(self):
        self.driver.quit()
