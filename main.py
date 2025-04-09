import pandas as pd
import time
import tqdm

from datetime import datetime
from src.analysis import GPT
from src.scrapping import IMDb
from src.utils.db import PostgreSQLDatabase
from src.utils.logger import setup_logging, get_backend_logger
from src.utils.s3 import s3


setup_logging()
logger = get_backend_logger()
logger.info("Launching main script")

db = PostgreSQLDatabase()
db.connect()

begin_time = time.time()


##################################
###          SCRAPPING         ###
##################################


for movie_id in set(movie[0] for movie in db.query_data('movies')):
    logger.info(f"Beginning scraping for movie #{movie_id}")

    ###   Scrap movie metadata   ###

    scrapper = IMDb()
    movie_scrap_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    movie_title, release_date = scrapper.get_movie(movie_id)
    total_reviews = scrapper.get_number_of_reviews(movie_id)

    # Update table (data must be passed as a list of tuples)
    last_scrapping = db.query_data("movies", condition=f"movie_id = '{(movie_id)}'")[0][4]
    movie_data = [(movie_id, movie_title, release_date, total_reviews, movie_scrap_time)]

    if last_scrapping is None:
        new_movie = 1
        db.remove_data("movies", "movie_id", movie_id)
        db.insert_data("movies", movie_data)
        prompt = "without" if total_reviews == 0 else "with"
        logger.info(f"New movie {prompt} reviews to scrap!")
    else:
        new_movie = 0
        db.upsert_movie_data(movie_data)

        # Check if new reviews have been published or if the last scrapping is >24h old
        movie_row = db.query_data("movies", condition=f"movie_id = '{movie_id}'")[0]
        declared_reviews = int(movie_row[3]) if movie_row[3] is not None else 0
        new_reviews = total_reviews - declared_reviews

        last_scrapping = movie_row[4]
        time_since_scrapping = (datetime.now() - last_scrapping).seconds

        prompt = "No review" if new_reviews == 0 else f"{new_reviews} new reviews"
        logger.info(f"{prompt} published in the last {(time_since_scrapping / 3600):.2F} hours")

        # Check if already published reviews have not been scrapped during the previous runs
        old_total_reviews = len(db.query_data("reviews_raw", condition=f"movie_id = '{(movie_id)}'"))
        old_total_reviews = int(old_total_reviews) if old_total_reviews is not None else 0
        logger.info(f"{old_total_reviews} reviews already scrapped")

        reviews_to_scrap = total_reviews - old_total_reviews
        if reviews_to_scrap == 0:
            logger.info("No additional review to scrap")
        else:
            logger.info(f"{reviews_to_scrap} to scrap")

    ###   Scrap reviews   ###

    if new_movie == 1 or reviews_to_scrap > 0 or time_since_scrapping > 86400:
        reviews_df = scrapper.get_reviews(movie_id, total_reviews)

        # Get the text hidden behind spoiler markup
        empty_reviews = reviews_df[pd.isnull(reviews_df["text"]) | (reviews_df["text"].str.strip() == "")]

        if len(empty_reviews) > 0:
            logger.warning(f"Missing text for {len(empty_reviews)} reviews")
            logger.info("Getting text behind spoiler markups")

            for index, row in tqdm.tqdm(empty_reviews.iterrows(), total=len(empty_reviews), desc="Processing empty reviews"):
                review_id = row["review_id"]
                spoiler_text = scrapper.get_spoiler(review_id)  # Call the function to get the spoiler
                reviews_df.at[index, "text"] = spoiler_text  # Replace 'text' with the spoiler
                db.ping()  # Ping the db to avoid being disconnected

        # Check again for empty reviews
        empty_reviews = reviews_df[reviews_df["text"].isna() | reviews_df["text"].str.strip().eq("") |
                                   reviews_df["title"].isna() | reviews_df["title"].str.strip().eq("")].shape[0]

        if empty_reviews > 0:
            logger.warning(f"Still missing text or title for {empty_reviews} reviews")
        else:
            logger.info("No reviews with missing text or title")

        # Get exact vote counts for values >999
        logger.info("Updating votes")
        mask = reviews_df['upvotes'].astype(str).str.endswith('K') | reviews_df['downvotes'].astype(str).str.endswith('K')
        logger.info(f"Found {len(reviews_df[mask])} reviews with rounded votes")

        for index, row in reviews_df[mask].iterrows():
            review_id = row['review_id']
            exact_upvotes, exact_downvotes = scrapper.get_votes(review_id)
            reviews_df.loc[index, 'upvotes'] = exact_upvotes
            reviews_df.loc[index, 'downvotes'] = exact_downvotes
            db.ping()

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
        db.upsert_review_data(reviews_list)

    # Closing browser
    scrapper.close()
    logger.info(f"Finished scrapping for movie #{movie_id}")


##################################
###     SENTIMENT ANALYSIS     ###
##################################


reviews_to_process = db.query_data('reviews_raw', condition=f"to_process = 1")

if len(reviews_to_process) == 0:
    logger.info("No new reviews to analyze")

else:
    unirev = len(reviews_to_process)
    unimov = len(pd.DataFrame(reviews_to_process)[0].unique())
    prompt1 = "1 review" if unirev == 1 else f"{unirev} reviews"
    prompt2 = "1 movie" if unimov == 1 else f"{unimov} movies"
    logger.info(f"{prompt1} to analyze for {prompt2}")
    logger.info("Starting API calls...")

    analyzer = GPT()
    for review in tqdm.tqdm(reviews_to_process, desc="Analyzing reviews sentiment", unit="review"):
        review_id = review[1]
        GPT_results = analyzer.sentiment(review)
        if GPT_results is not None:
            data = [(review_id, *GPT_results)]
            db.update_sentiment_data(data)
            db.reset_indicator(review_id)
        # Interrupt sentiment analysis if the script is about to have run for 1 hour
        if time.time() - begin_time > 58 * 60:
            logger.warning("Sentiment analysis taking too long, aborting to avoid conflicts with the scheduler...")
            break


##################################
###           BACKUP           ###
##################################

logger.info("Backing up...")

# Save the tables to parquet
for table in ['movies', 'reviews_raw', 'reviews_sentiments']:
    db.backup_table(table)

# Upload the files to S3
s3 = s3()
for table in ['movies', 'reviews_raw', 'reviews_sentiments']:
    file_path = s3.get_latest_local_backup(table)
    if file_path is not None:
        s3.upload_backup(file_path)

# Remove old backups
s3.clean_backup_directory()


db.close_connection()
logger.info(f"Total execution time: {(time.time() - begin_time)/60:.2f} minutes")
