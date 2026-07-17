# BEFORE YOU GO ON

In order to generate the complete CSV as shown in the folder "data" as an example, one must first create a remote chrome setup using these commands in VSCode's Powershell:

"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

pip install -r requirements.txt

python scraper/main.py

You must close all other chrome tabs first. It is done this way because backpack.tf uses cloudfare protection in order to protect itself against bots. This allows the code to manually enter the website using an existing chrome browser.



# Objective

Our project aims to inform TF2 players of which hats to invest in. We will retrieve data on every type of hat with unusual effects&mdash;the total number of hats in existence, the number of hats bought to date, the number of hats that were sold to date. Through analysing these trends, we can predict if a hat is likely to increase in price and hence be profitable.

# Collaborators

Coded by Koh Min Xuan and Isaac Foo for the Build Beyond Hackathon