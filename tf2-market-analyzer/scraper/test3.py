from selenium import webdriver
from selenium.webdriver.common.by import By
import time

driver = webdriver.Chrome()

driver.get("https://backpack.tf/effects")

time.sleep(10)

print(driver.title)

driver.quit()