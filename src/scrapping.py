import pandas as pd
import re
import time

from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from src.utils.logger import get_backend_logger

logger = get_backend_logger()

class IMDb:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        logger.info("Launching browser")


    @staticmethod
    def restore_leading_zeros(raw_id, tot_lgt):
        full_id = str(raw_id)
        if len(full_id) < tot_lgt:
            full_id = full_id.zfill(tot_lgt)
            logger.debug("Restoring leading zeros for {raw_id}")
        return full_id


    def get_movie(self, raw_movie_id):
        try:
            movie_id = IMDb.restore_leading_zeros(raw_movie_id, 7)
            
            # Load main page
            self.driver.get(f"https://www.imdb.com/title/tt{movie_id}")
            logger.info("Scrapping metadata")

            # Wait for and extract title
            title_element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//span[@data-testid="hero__primary-text"]'))
            )
            movie_title = title_element.text.strip()
            logger.info(f"Movie title: {movie_title}")

            # Wait for and extract release date
            release_date_element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//li[@data-testid="title-details-releasedate"]//a[@class="ipc-metadata-list-item__list-content-item ipc-metadata-list-item__list-content-item--link"]'))
            )
            release_date = release_date_element.text.split(" (")[0].strip()
            logger.info(f"Release date: {release_date}")

            return movie_title, release_date

        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return None


    def get_number_of_reviews(self, raw_movie_id):
        try:
            movie_id = IMDb.restore_leading_zeros(raw_movie_id, 7)
            
            # Load review page
            self.driver.get(f"https://www.imdb.com/title/tt{movie_id}/reviews")

            # Wait for, extract and parse the number of reviews
            reviews_element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@data-testid="tturv-total-reviews"]'))
            )
            reviews_text = reviews_element.text.strip()
            if "reviews" in reviews_text:
                total_reviews = reviews_text.split(" reviews")[0]    # Remove the unit
                total_reviews = total_reviews.replace(",", "")       # Remove the comma for numbers >999
                logger.info(f"Reviews: {total_reviews}")
                return int(total_reviews)                            # Convert to integer
            else:
                logger.info(f"Could not parse review count from text: '{reviews_text}'")
                return None

        except Exception as e:
            logger.error(f"Failed to get number of reviews: {e}")
            return None


    def get_reviews(self, raw_movie_id, total_reviews):
        movie_id = IMDb.restore_leading_zeros(raw_movie_id, 7)
        
        # Load reviews page
        self.driver.get(f"https://www.imdb.com/title/tt{movie_id}/reviews")
        logger.info("Scrapping reviews")
        time.sleep(7)

        # Click the button to display all reviews, using JavaScript to avoid interception issues
        if total_reviews > 25:
            try:
                all_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//span[contains(@class, "ipc-see-more")]//button[.//span[contains(text(), "All")]]'))
                )
                self.driver.execute_script("arguments[0].click();", all_button)
                logger.info("Attempting to display all reviews")
            except Exception as e:
                logger.warning(f"Button for displaying all reviews not found or not clickable: {e}")

        # Scroll down to compensate for lazy loading
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            logger.info("Scrolling down...")
            time.sleep(1)  # Give time for new reviews to load
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break  # Stop when no new content loads
            last_height = new_height

        # Loop through each review and extract information
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        reviews = soup.find_all("article", class_="user-review-item")
        data = []
        for review in reviews:
            try:
                # 1. Extract the review identifier
                permalink_tag = review.find("a", class_="ipc-link ipc-link--base", attrs={"data-testid": "permalink-link"})
                review_id = None
                if permalink_tag:
                    identifier_match = re.search(r"/rw(\d+)", permalink_tag["href"])
                    if identifier_match:
                        review_id = identifier_match.group(1)

                # 2. Extract the review date
                date_tag = review.find("li", class_="ipc-inline-list__item review-date")
                review_date = date_tag.get_text(strip=True) if date_tag else None

                # 3. Extract the review author
                author_tag = review.find("a", class_="ipc-link ipc-link--base", attrs={"data-testid": "author-link"})
                author_name = author_tag.get_text(strip=True) if author_tag else None

                # 4. Extract the upvotes and downvotes
                upvotes_tag = review.find("span", class_="ipc-voting__label__count--up")
                downvotes_tag = review.find("span", class_="ipc-voting__label__count--down")
                upvotes = upvotes_tag.get_text(strip=True) if upvotes_tag else 0
                downvotes = downvotes_tag.get_text(strip=True) if downvotes_tag else 0

                # 5. Extract the review text
                review_tag = review.find("div", class_="ipc-html-content-inner-div")
                review_text = review_tag.get_text(separator="\n", strip=True) if review_tag else None

                # 6. Extract the review title
                title_container = review.find("div", class_="ipc-title")
                review_title = None
                if title_container:
                    title_tag = title_container.find("h3", class_="ipc-title__text")
                    review_title = title_tag.get_text(strip=True) if title_tag else None

                # 7. Extract the rating
                rating_tag = review.find("span", class_="ipc-rating-star--maxRating")
                rating = None
                if rating_tag and rating_tag.previous_sibling:
                    rating = rating_tag.previous_sibling.get_text(strip=True)

                # 8. Append data to the list
                data.append({
                    "movie_id": movie_id,
                    "review_id": review_id,
                    "author": author_name,
                    "title": review_title,
                    "text": review_text,
                    "rating": rating,
                    "date": review_date,
                    "upvotes": upvotes,
                    "downvotes": downvotes,
                    "last_update": datetime.now().strftime("%Y%m%d_%H%M%S")
                })
            except Exception as e:
                logger.error(f"Failed to extract data for a review: {e}")
                continue

        # Create a dataframe from the collected data
        reviews_df = pd.DataFrame(data)
        logger.info(f"Extracted {len(reviews_df)} reviews")
        return reviews_df


    def get_spoiler(self, raw_review_id):
        review_id = IMDb.restore_leading_zeros(raw_review_id, 8)
        
        # Load review page
        self.driver.get(f"https://www.imdb.com/review/rw{review_id}/")
        time.sleep(2)  # Allow page to load

        try:
            # Locate the spoiler button and click it
            spoiler_button = self.driver.find_element(By.XPATH, '//div[@class="expander-icon-wrapper spoiler-warning__control"]')
            self.driver.execute_script("arguments[0].click();", spoiler_button)
            # Wait for the text to become visible after clicking the spoiler button
            time.sleep(1)
            text_element = self.driver.find_element(By.XPATH, '//div[@class="text show-more__control"]')
            text = text_element.text.strip()
            return text
        except Exception as e:
            logger.error(f"Failed to unspoil review {review_id}: {e}")
            return None


    def get_votes(self, raw_review_id):
        review_id = IMDb.restore_leading_zeros(raw_review_id, 8)
        
        # Load review page
        self.driver.get(f"https://www.imdb.com/review/rw{review_id}/")
        time.sleep(2)  # Allow page to load
        logger.info(f"Getting exact votes for review #{review_id}")

        # Extract votes
        try:
            votes_element = self.driver.find_element(By.XPATH, '//div[@class="actions text-muted"]')
            votes_text = votes_element.text.strip()
            votes_match = re.search(r'([\d,]+) out of ([\d,]+)', votes_text)
            if votes_match:
                upvotes = int(votes_match.group(1).replace(',', ''))
                allvotes = int(votes_match.group(2).replace(',', ''))
                downvotes = allvotes - upvotes
            return upvotes, downvotes

        except Exception as e:
            logger.error(f"Failed to get exact votes for review {review_id}: {e}")
            return None


    def close(self):
        if hasattr(self, 'driver'):
            self.driver.quit()
            logger.info("Closing browser")
