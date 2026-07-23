from selenium import webdriver
import time

driver = webdriver.Chrome()

driver.get("https://backpack.tf/effects")

print(driver.title)

time.sleep(30)

driver.quit()