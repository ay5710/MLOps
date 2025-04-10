import argparse
import pandas as pd
import time
import tqdm

from datetime import datetime
from src.analysis import GPT
from src.scrapping import IMDb
from src.utils.db import PostgreSQLDatabase
from src.utils.logger import setup_logging, get_backend_logger


setup_logging()
logger = get_backend_logger()

parser = argparse.ArgumentParser()
parser.add_argument("--movie_id", required=True, type=str)
args = parser.parse_args()
movie_id = args.movie_id

start_time = time.time()


##################################
###          SCRAPPING         ###
##################################

logger.info(f"{movie_id} - Beginning scraping")

###   Scrap movie metadata   ###

movie_scrap_time = datetime.now().strftime("%Y%m%d_%H%M%S")
with IMDb() as scrapper:
    movie_title, release_date = scrapper.get_movie(movie_id)
    total_reviews = scrapper.get_number_of_reviews(movie_id)

# Update table (data must be passed as a list of tuples)
with PostgreSQLDatabase() as db:
    last_scrapping = db.query_data("movies", condition=f"movie_id = '{(movie_id)}'", movie_id=movie_id)[0][4]
movie_data = [(movie_id, movie_title, release_date, total_reviews, movie_scrap_time)]

if last_scrapping is None:
    new_movie = 1
    with PostgreSQLDatabase() as db:
        db.remove_data("movies", "movie_id", movie_id, movie_id)
        db.insert_data("movies", movie_data, movie_id)
    prompt = "without" if total_reviews == 0 else "with"
    logger.info(f"{movie_id} - New movie {prompt} reviews to scrap!")
else:
    new_movie = 0
    with PostgreSQLDatabase() as db:
        db.upsert_movie_data(movie_data, movie_id)
    
    # Check if new reviews have been published or if the last scrapping is >24h old
    with PostgreSQLDatabase() as db:
        movie_row = db.query_data("movies", condition=f"movie_id = '{movie_id}'", movie_id=movie_id)[0]
    declared_reviews = int(movie_row[3]) if movie_row[3] is not None else 0
    new_reviews = total_reviews - declared_reviews

    last_scrapping = movie_row[4]
    time_since_scrapping = (datetime.now() - last_scrapping).seconds

    prompt = "No review" if new_reviews == 0 else f"{new_reviews} new reviews"
    logger.info(f"{movie_id} - {prompt} published in the last {(time_since_scrapping / 3600):.2F} hours")

    # Check if already published reviews have not been scrapped during the previous runs
    with PostgreSQLDatabase() as db:
        old_total_reviews = len(db.query_data("reviews_raw", condition=f"movie_id = '{(movie_id)}'", movie_id=movie_id))
    old_total_reviews = int(old_total_reviews) if old_total_reviews is not None else 0
    logger.info(f"{movie_id} - {old_total_reviews} reviews already scrapped")

    reviews_to_scrap = total_reviews - old_total_reviews
    if reviews_to_scrap == 0:
        logger.info(f"{movie_id} - No additional review to scrap")
    else:
        logger.info(f"{movie_id} - {reviews_to_scrap} reviews to scrap")

###   Scrap reviews   ###

if new_movie == 1 or reviews_to_scrap > 0 or time_since_scrapping > 86400:
    with IMDb() as scrapper:
        reviews_df = scrapper.get_reviews(movie_id, total_reviews)

        # Get the text hidden behind spoiler markup
        empty_reviews = reviews_df[pd.isnull(reviews_df["text"]) | (reviews_df["text"].str.strip() == "")]

        if len(empty_reviews) > 0:
            logger.warning(f"{movie_id} - Missing text for {len(empty_reviews)} reviews")
            logger.info(f"{movie_id} - Getting text behind spoiler markups")

            for index, row in tqdm.tqdm(empty_reviews.iterrows(), total=len(empty_reviews), desc=f"{movie_id} - Processing empty reviews", miniters=10):
                review_id = row["review_id"]
                spoiler_text = scrapper.get_spoiler(review_id, movie_id)  # Call the function to get the spoiler
                reviews_df.at[index, "text"] = spoiler_text  # Replace 'text' with the spoiler

        # Check again for empty reviews
        empty_reviews = reviews_df[reviews_df["text"].isna() | reviews_df["text"].str.strip().eq("") |
                                   reviews_df["title"].isna() | reviews_df["title"].str.strip().eq("")].shape[0]

        if empty_reviews > 0:
            logger.warning(f"{movie_id} - Still missing text or title for {empty_reviews} reviews")
        else:
            logger.info(f"{movie_id} - No reviews with missing text or title")

        # Get exact vote counts for values >999
        logger.info(f"{movie_id} - Updating votes")
        mask = reviews_df['upvotes'].astype(str).str.endswith('K') | reviews_df['downvotes'].astype(str).str.endswith('K')
        logger.info(f"{movie_id} - Found {len(reviews_df[mask])} reviews with rounded votes")

        for index, row in reviews_df[mask].iterrows():
            review_id = row['review_id']
            exact_upvotes, exact_downvotes = scrapper.get_votes(review_id, movie_id)
            reviews_df.loc[index, 'upvotes'] = exact_upvotes
            reviews_df.loc[index, 'downvotes'] = exact_downvotes

        reviews_df['upvotes'] = reviews_df['upvotes'].astype(int)
        reviews_df['downvotes'] = reviews_df['downvotes'].astype(int)

    # Update table
    # Create a variable to identify reviews needing sentiment analysis
    reviews_df['to_process'] = 1

    # Convert data to a list of tuples
    reviews_list = reviews_df.apply(lambda row: (
        str(row['movie_id']), str(row['review_id']),
        str(row['author']), str(row['title']),
        str(row['text']), row['rating'],
        str(row['date']), row['upvotes'],
        row['downvotes'], row['last_update'], row['to_process']
    ), axis=1).tolist()

    # Replace NaN with None to avoid errors with postgreSQL
    reviews_list = [tuple(None if pd.isna(x) else x for x in row) for row in reviews_list]

    # Upserting
    with PostgreSQLDatabase() as db:
        db.upsert_review_data(reviews_list, movie_id)

logger.info(f"{movie_id} - Finished scrapping")


##################################
###     SENTIMENT ANALYSIS     ###
##################################

with PostgreSQLDatabase() as db:
    reviews_to_process = db.query_data('reviews_raw', condition=f"to_process = 1", movie_id=movie_id)

if len(reviews_to_process) == 0:
    logger.info(f"{movie_id} - No new reviews to analyze")

else:
    unirev = len(reviews_to_process)
    prompt = "1 review" if unirev == 1 else f"{unirev} reviews"
    logger.info(f"{movie_id} - {prompt} to analyze, starting API calls...")

    analyzer = GPT()
    for review in tqdm.tqdm(reviews_to_process, desc=f"{movie_id} - Analyzing reviews sentiment", unit="review", miniters=10):
        review_id = review[1]
        GPT_results = analyzer.sentiment(review, movie_id)
        if GPT_results is not None:
            data = [(review_id, *GPT_results)]
            with PostgreSQLDatabase() as db:
                db.update_sentiment_data(data, movie_id)
                db.reset_indicator(review_id, movie_id)


logger.info(f"{movie_id} - Total execution time: {(time.time() - start_time)/60:.2f} minutes")
