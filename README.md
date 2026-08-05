# BEFORE YOU GO ON

The launcher now creates the remote Chrome setup automatically.

In Command Prompt:

1) Run cd \

2) Run dir TF2-market-analyser /s /ad

3) Copy the directory name (It appears after "Directory of..."), then run cd &lt;directory name&gt;\TF2-market-analyser

4) Run pip install -r requirements.txt

5) Run python -m scraper.main

6) Chrome will open backpack.tf/effects with remote debugging enabled on localhost:9222, and scraping will begin. Please remember to pass Cloudflare manually in that window if required.

In VSCode:

Run the launcher from the project root so its package imports resolve correctly:

1) Open the TF2-market-analyser folder in VS Code.

2) Terminal → New Terminal.

3) Input pip install -r requirements.txt

4) Input python -m scraper.main

5) Chrome will open backpack.tf/effects and scraping will begin. Please remember to pass Cloudflare manually in that window if required.

The launcher uses a separate temporary Chrome profile because backpack.tf may require a manual Cloudflare check before Selenium can use the page.


# Objective

Our project aims to inform TF2 players of which hats to invest in. We will retrieve data on every type of hat with unusual effects&mdash;the total number of hats in existence, the number of hats bought to date, the number of hats that were sold to date. Through analysing these trends, we can predict if a hat is likely to increase in price and hence be profitable.

# Google Sheets Data

- [TF2 Analysis — Sheet 1](https://docs.google.com/spreadsheets/d/1R_gXJRX8stscCKpitq7pSceQWhtFM2ZwoEY-kSZlD_8/edit)
- [TF2 Analysis — Sheet 2](https://docs.google.com/spreadsheets/d/19PjHGJh1Wtb1gjfmQfL1LoL0y6FhggBBC95FbGet8Jg/edit?gid=1061679333#gid=1061679333)

# Collaborators

Coded by Isaac Foo, Koh Min Xuan, and Low Zong Xuan for the Build Beyond Hackathon
