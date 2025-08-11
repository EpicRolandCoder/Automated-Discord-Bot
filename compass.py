# Prolly use a raspberry pi to host the server cos this needs a server that can run a web driver (even if its headless)

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
import time
from bs4 import BeautifulSoup

def get_compass_classes(student_code: str, password: str, driver_name: str = "firefox", headless: bool = True, timeout: int = 15):
    """
    Logs into Compass and returns a list of class names (strings).
    - student_code: without domain (e.g. 's12345')
    - password: the student's password
    - driver_name: 'firefox' or 'chrome' (must have corresponding driver in PATH)
    - headless: whether to run the browser headless
    NOTE: This function uses Selenium and is blocking. Call from an executor/thread (e.g. asyncio.to_thread).
    """
    # Configure driver options
    driver = None
    try:
        if driver_name.lower() == "firefox":
            options = FirefoxOptions()
            if headless:
                options.add_argument("--headless")
            driver = webdriver.Firefox(options=options)
        elif driver_name.lower() == "chrome":
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            options = ChromeOptions()
            if headless:
                options.add_argument("--headless")
            driver = webdriver.Chrome(options=options)
        else:
            raise ValueError("Unsupported driver_name. Use 'firefox' or 'chrome'.")

        driver.implicitly_wait(10)
        driver.get("https://mhs-vic.compass.education/login.aspx?sessionstate=disabled")

        # This sequence mirrors your previous flow; element names/IDs may change if Compass updates
        driver.find_element(by=By.NAME, value="ctl10").click()
        driver.implicitly_wait(5)
        driver.find_element(by=By.ID, value="i0116").send_keys(f"{student_code}@mhs.vic.edu.au")
        driver.find_element(by=By.ID, value="idSIButton9").click()
        time.sleep(1)
        driver.find_element(by=By.ID, value="i0118").send_keys(password)
        driver.find_element(by=By.ID, value="i0118").send_keys(Keys.ENTER)
        time.sleep(5)
        # depending on flow, navigate back to the calendar view
        try:
            driver.find_element(by=By.ID, value="idBtn_Back").click()
        except Exception:
            # if not present, just continue
            pass
        time.sleep(3)

        # Extract calendar HTML and parse
        element = driver.find_element(by=By.CLASS_NAME, value="ext-cal-day-col-gutter")
        html = element.get_attribute("outerHTML")
        soup = BeautifulSoup(html, "html.parser")
        classes = []
        for div in soup.find_all("div"):
            if div.find("span"):
                classes.append(div.find("span").text.strip())
        return classes
    finally:
        if driver:
            driver.quit()
