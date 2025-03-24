from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, MetaData, Table, func
from sqlalchemy.sql import select
import databases
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles

# SQLite database URL
DATABASE_URL = "sqlite:///./games.db"

# Setup async database connection
database = databases.Database(DATABASE_URL)
engine = create_engine(DATABASE_URL)
metadata = MetaData()
metadata.reflect(bind=engine)

# Reflect the 'games' table
games = Table("games", metadata, autoload_with=engine)

# Lifespan context to manage DB connection
@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()

# Create FastAPI app
app = FastAPI(lifespan=lifespan)

# 1. All games (with optional limit)
@app.get("/games/")
async def get_games(limit: int = 100):
    query = select(games).limit(limit)
    results = await database.fetch_all(query)
    return results


# 2. General stats
@app.get("/games/stats")
async def get_game_stats():
    total_games = await database.fetch_val(select(func.count()).select_from(games))
    avg_score = await database.fetch_val(
        select(func.avg(games.c.critic_score)).where(games.c.critic_score != None)
    )
    total_sales = await database.fetch_val(
        select(func.sum(games.c.total_sales)).where(games.c.total_sales != None)
    )

    top_consoles_query = (
        select(games.c.console, func.sum(games.c.total_sales).label("sales"))
        .where(games.c.total_sales != None)
        .group_by(games.c.console)
        .order_by(func.sum(games.c.total_sales).desc())
        .limit(5)
    )
    top_consoles = await database.fetch_all(top_consoles_query)

    top_genres_query = (
        select(games.c.genre, func.sum(games.c.total_sales).label("sales"))
        .where(games.c.total_sales != None)
        .group_by(games.c.genre)
        .order_by(func.sum(games.c.total_sales).desc())
        .limit(5)
    )
    top_genres = await database.fetch_all(top_genres_query)

    return JSONResponse({
        "total_games": total_games,
        "average_critic_score": round(avg_score, 2) if avg_score else None,
        "total_global_sales": round(total_sales, 2) if total_sales else None,
        "top_consoles": [dict(row) for row in top_consoles],
        "top_genres": [dict(row) for row in top_genres],
    })


# 3. Top sellers
@app.get("/games/top-sellers")
async def get_top_sellers(limit: int = 10):
    query = (
        select(games)
        .where(games.c.total_sales != None)
        .order_by(games.c.total_sales.desc())
        .limit(limit)
    )
    results = await database.fetch_all(query)
    return results


# 4. Filter by console
@app.get("/games/console/{console_name}")
async def get_games_by_console(console_name: str, limit: int = 50):
    query = (
        select(games)
        .where(games.c.console == console_name)
        .limit(limit)
    )
    results = await database.fetch_all(query)
    return results


# 5. Stats by year
@app.get("/games/stats/by-year")
async def get_stats_by_year(
    console: str = Query(None),
    genre: str = Query(None)
):
    filters = [
        games.c.release_date != None,
        func.substr(games.c.release_date, 1, 4) >= "2000"
    ]

    if console:
        filters.append(func.lower(games.c.console) == console.lower())

    if genre:
        filters.append(func.lower(games.c.genre) == genre.lower())

    query = (
        select(
            func.substr(games.c.release_date, 1, 4).label("year"),
            func.count().label("game_count"),
            func.avg(games.c.critic_score).label("avg_score"),
            func.sum(games.c.total_sales).label("total_sales")
        )
        .where(*filters)
        .group_by("year")
        .order_by("year")
    )

    results = await database.fetch_all(query)

    return [
        dict(row) for row in results
        if row["avg_score"] is not None or row["total_sales"] is not None
    ]

@app.get("/games/consoles")
async def get_unique_consoles():
    query = select(games.c.console).distinct().order_by(games.c.console)
    results = await database.fetch_all(query)
    return [row["console"] for row in results if row["console"]]

@app.get("/games/genres")
async def get_unique_genres():
    query = select(games.c.genre).distinct().order_by(games.c.genre)
    results = await database.fetch_all(query)
    return [row["genre"] for row in results if row["genre"]]

app.mount("/", StaticFiles(directory="static", html=True), name="static")