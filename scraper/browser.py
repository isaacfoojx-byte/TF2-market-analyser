from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def get_driver():
    chrome_options = Options()
    chrome_options.debugger_address = "localhost:9222"

    return webdriver.Chrome(options=chrome_options)


