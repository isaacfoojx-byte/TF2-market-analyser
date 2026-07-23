from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def get_driver(port):
    chrome_options = Options()
    chrome_options.debugger_address = f"localhost:{port}"
    

    service = Service(log_output="chromedriver.log")

    return webdriver.Chrome(
        service=service,
        options=chrome_options
    )


