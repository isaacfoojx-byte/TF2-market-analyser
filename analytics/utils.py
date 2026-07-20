import pandas as pd

def load_data():

    df = pd.read_csv("data/processed/cleaned_unusuals.csv")

    priced = df[df["has_price"]].copy()

    return df, priced