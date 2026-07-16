from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.debugger_address = "localhost:9222"

driver = webdriver.Chrome(options=options)

print(driver.title)