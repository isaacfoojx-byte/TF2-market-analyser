# BEFORE YOU GO ON

In order to generate the complete CSV as shown in the folder "data" as an example, one must first create a remote chrome setup.

In Command Prompt:

1) Run cd \

2) Run dir TF2-market-analyser /s /ad

3) Copy the directory name (It appears after "Directory of..."), then run cd &lt;directory name&gt;\TF2-market-analyser

4) Run pip install -r requirements.txt

5) Run "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\ChromeDebug" 

6) In the chrome window that opens after step 3, go to backpack.tf. Pass CLoudflare manually if required.

7) Run python scraper/main.py

8) The chrome tab should start to document each item automatically now.

In VSCode:

1) Open the TF2-market-analyser folder in VS Code.

2) Terminal → New Terminal.

3) Input pip install -r requirements.txt

4) Input "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:TEMP\ChromeDebug"

5) In the chrome window that opens after step 2, go to backpack.tf. Pass Cloudflare manually if required.

6) Input python scraper/main.py

7) The chrome tab should start to document each item automatically now.

You must close all other chrome tabs first. It is done this way because backpack.tf uses cloudfare protection in order to protect itself against bots. This allows the code to manually enter the website using an existing chrome browser.


# Objective

Our project aims to inform TF2 players of which hats to invest in. We will retrieve data on every type of hat with unusual effects&mdash;the total number of hats in existence, the number of hats bought to date, the number of hats that were sold to date. Through analysing these trends, we can predict if a hat is likely to increase in price and hence be profitable.

# Collaborators

Coded by Koh Min Xuan and Isaac Foo for the Build Beyond Hackathon