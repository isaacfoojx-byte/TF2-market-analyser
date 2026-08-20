# Build Beyond Project Write-up

## Project summary

TFAnalytics is a market-intelligence platform for the Team Fortress 2 economy. It
collects and validates daily price-guide data, preserves each update as a historical
snapshot, and turns that history into interactive dashboards, explainable market
signals, item-level trends, and downloadable datasets. The goal is not to promise
profitable trades, but to help players make better-informed decisions from evidence
that would otherwise be difficult and time-consuming to assemble.

## The idea: What inspired us to build it?

Team Fortress 2 has a long-running virtual economy in which cosmetics, weapons,
taunts, and other items are valued in refined metal and Mann Co. Supply Crate Keys.
Unusual items add another layer of complexity because the same hat can have many
different particle effects, each forming a distinct market. Thousands of additional
non-Unusual item variants are differentiated by quality and craftability.

Pricing information is available through community resources such as backpack.tf,
but understanding how the market changes over time still requires players to inspect
many separate pages and compare values manually. Existing tools are useful for
checking an individual price; we wanted to complement them with a broader,
historical view of the economy.

This inspired us to build TFAnalytics: one place where traders, collectors, and
curious players can explore current values, compare past snapshots, and understand
why a market is being highlighted. We deliberately present the product as
decision-support market intelligence rather than a guaranteed investment predictor.

## How it works

TFAnalytics uses scheduled GitHub Actions workflows to request daily pricing data
from the backpack.tf API. One pipeline collects exact Unusual item-effect markets;
the other collects the wider community price guide while excluding Unusual quality
so the two datasets remain clear and complementary. A separate Steam Web API job
maintains the official item-image catalogue used by the website.

After collection, Python and pandas processing code cleans the records and converts
prices into consistent refined-metal and key equivalents. Before a snapshot is
published, automated validators check its required columns, timestamps, price
values, duplicates, and row count. Suspicious or malformed outputs fail the workflow
instead of silently replacing reliable data.

Accepted raw and processed snapshots are versioned as CSV files in GitHub and copied
to date-stamped Google Sheets tabs for secondary analysis and archival. The Streamlit
website automatically discovers the latest files, warns visitors if data becomes
stale, and compares snapshots across time.

The interface uses Plotly for interactive visualisations. It provides headline
market metrics, item and effect leaderboards, historical trend charts, market
sentiment, risk flags, opportunity screening, and confidence labels. Users can also
look up an exact Unusual item-effect combination or community item variant and
download the underlying CSV snapshots for their own analysis.

## Main features

- Automated daily collection of thousands of TF2 price-guide entries.
- Coverage of both exact Unusual markets and wider non-Unusual item variants.
- Historical snapshot comparisons across user-selected periods.
- Searchable trends for individual items, qualities, and Unusual effects.
- Interactive Plotly charts, market summaries, and leaderboards.
- Explainable sentiment, opportunity, risk, and confidence indicators.
- Automatic validation that catches missing fields, invalid prices, duplicates,
  timestamp mismatches, and suspicious data loss.
- Freshness warnings when scheduled updates are missing or delayed.
- Versioned CSV history, Google Sheets archival, and website downloads.
- Fully scheduled cloud workflows that do not require a team member's computer to
  remain online.

What makes TFAnalytics stand out is the combination of product and pipeline. It is
not only a dashboard showing today's values: it continually builds a reproducible
history, protects that history with validation, and explains the evidence behind its
market signals.

## Technology stack

- **Python** for data collection, processing, validation, and analytics.
- **Streamlit** for the multi-page interactive website.
- **pandas and NumPy** for cleaning, aggregation, comparison, and scoring.
- **Plotly** for interactive charts and historical trends.
- **Requests and the backpack.tf API** for scheduled price-guide collection.
- **Steam Web API** for official TF2 item images.
- **Selenium and Beautiful Soup** for supplementary browser-assisted collection and
  HTML parsing utilities.
- **GitHub Actions** for daily scheduling, validation, archival, and continuous
  integration.
- **Google Sheets API** for date-stamped secondary archives.
- **CSV and Git** for reproducible historical storage and version control.

Matplotlib, ReportLab, and their generated static reports were removed because the
current product uses interactive Plotly charts and direct CSV downloads. SQLite was
explored during development, but the deployed application uses versioned CSV
snapshots as its active data source.

## Intended audience

TFAnalytics is designed for TF2 traders, collectors, market researchers, and players
who want to understand the economy before buying or selling an item. It is especially
helpful for people who want to compare items and effects, monitor longer-term price
movement, or investigate unusual market behaviour without manually examining
thousands of price-guide entries.

The platform is also useful as an educational example of how an automated data
pipeline can turn a changing virtual economy into a transparent analytics product.
Its values remain indicative community price-guide data rather than guaranteed sale
prices, and its risk and opportunity signals should be treated as evidence for
further investigation, not financial advice.
