from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

options = Options()
options.debugger_address = "localhost:9222"
driver = webdriver.Chrome(options=options)

print("Current title:", driver.title)
print("Current URL:", driver.current_url)