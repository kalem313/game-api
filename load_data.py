import pandas as pd
from sqlalchemy import create_engine

# Load CSV
df = pd.read_csv("games.csv")

# Clean column names
df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

# Drop rows with missing titles
df = df.dropna(subset=["title"])

# Connect to SQLite
engine = create_engine("sqlite:///games.db")

# Save to SQLite
df.to_sql("games", con=engine, if_exists="replace", index=False)

print("Game data loaded into SQLite successfully!")
