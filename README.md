# The IMDb Reviews Tracker
This project tracks the reception of movies based on user reviews published on [IMDb](https://www.imdb.com). It was realised during the [Deployment of Data Science Projects](https://www.ensae.fr/courses/6052-mise-en-production-des-projets-de-data-science) course at ENSAE (see the [companion website](https://ensae-reproductibilite.github.io/website/)).

## 1. Implementation
There are 4 main components:
- Web scraping
- Aspect-based sentiment analysis
- Dashboard
- User management

Data is stored in a PostgreSQL database and saved in the DataLab with s3. A sample with 2 movies is provided.

Architecture:
<pre>
app/
├── data/
│   ├── backup/
│   ├── covers/    
│   └── sample/
├── logs/
├── notebooks/
├── setup/
│   ├── .env.template
│   └── db_init.py
├── src/
│   ├── analysis.py
│   ├── backup.py
│   ├── manage_movies.py
│   ├── scraping.py
│   └── utils/
│       ├── db.py
│       ├── logger.py
│       └── s3.py
├── test/
│       ├── backup_test.py
│       └── connection_test.py
├── main.py
└── scheduler.py</pre>

### Installation
#### In the DataLab
Launch a Postgresql service, then create an `.env` file with the corresponding parameters:
- DB_NAME=
- DB_USER=
- DB_PASSWORD=
- DB_HOST=

Launch the installation script with `chmod +x ./install.sh && source ./install.sh`. This script:
1. Installs Chrome
2. Installs Python and dependencies with Poetry
3. Checks if credentials are present
4. Sets up the database
5. Launches the scheduler

The state of the scheduler can be checked with `pgrep -fl scheduler.py`.

#### With Docker
A `docker-compose.yml` is provided which runs the tracker, the database and the dashboard as distinct services.

An `.env` file is required, including parameters for the backup on S3 which can be retrieved [here](https://datalab.sspcloud.fr/account/storage) (see `setup/.env.template`; `DB_HOST` must be set to the name of the postgresql service in the `docker-compose`, by default, `db`).

### Manage movies
They can be added or removed with `poetry run python -m src.manage_movies --add '<movie_id_1>' '<movie_id_2>' --remove '<movie_id_3>'` (where `<movie_id>` must be retrieved manually from IMDb, e.g., `tt0033467` for [Citizen Kane](https://www.imdb.com/title/tt0033467/?ref_=fn_all_ttl_1)).

## 2. Technical aspects

### scraping
Data must be collected from three IMDB pages:
- The movie’s main page for metadata, including the total number of reviews.
- The main reviews page, which shows the 25 most popular reviews by default; some reviews are hidden behind `<spoiler>` tags, and vote counts over 999 are rounded.
- Individual review pages, where exact vote counts are displayed.

Interacting with the webpages was necessary:
- To display all reviews on the main reviews page. It turned out the “Show all” button do not actually display all reviews: it stops at the nearest multiple of 25, requiring an additional click on the “Show more” button for remaining reviews.
- To access text hidden behind `<spoiler>` tags, fetching the individual review pages proved more reliable, though slower.

The scraping process follows these steps:
- Every hour, scrape the main page to retrieve metadata.
- If new reviews have been published, the movie was just added to the database, or the last full scrape is older than 24 hours, scrape the main reviews page.
- If spoiler tags or rounded vote counts are detected, scrape the corresponding individual review pages.
- Update the database tables, flagging reviews as new or edited for sentiment analysis.

A scheduler launches one script per movie every hour, ensuring no more than five movies are scraped concurrently to avoid overloading the system. The database is also backed up hourly. For some movies, small discrepancies were observed between the number of reviews listed on the main page and the number actually scraped from the reviews page. A cursory investigation found no clear explanation. 

### Sentiment analysis
We want to determine the opinions expressed in the reviews regarding 5 main features of the movies:
- *Storytelling* (including characters and their development, narrative progression, plot twists, screenplay, dialogues, overall pacing)
- *Acting performance* (including vocal, musical, danse, or stunt work if applicable)
- *Cinematography and visual style* (including colors and lightening, set design, costumes, makeup, special effects, overall aesthetic of the film)
- *Music and sound design* (including soundtrack and scores)
- *Theme and values* (including the moral or political message, emotional resonance, cultural or societal impact)

Such a task is called **aspect-base sentiment analysis**. It is a seriously difficult task that dedicated models still struggle to solve (see [Cathy Yua et al., 2024](https://arxiv.org/abs/2311.10777)). Some models extract opinions regarding pre-determined aspects, but are inapplicable here due to the absence of movie-specific datasets to train them. Other models extract aspects and opinions autonomously, but are difficult to use at scale, as their outputs remain very granular and context-dependant.

The only workable solution is to offload sentiment analysis to a **generative LLM**. A cursory experimentation proved that this works well with an adequate prompt. However, it requires very large models, that cannot be run locally but must be called through APIs. The current implementation relies on gpt-4o-mini from OpenAI, which is inexpensive ($0.15 / M tokens) but rather slow. An alternative would be to use Gemini from Google, which has a free tier, albeit with rates limits and requiring an API key as well.

### Dashboard
With Streamlit. Includes...
- Header presenting the movie + time since last scraping
- Total number of reviews + graph of their publication date
- Average grade + graph of its evolution over time
- For each sentiment + overall sentiment: average score + histogram
- The possibility to add or remove movies
- ...

Create different clients able to track different movies, with a logging interface to the dashboard

## 3. Possible improvements
- Add an admin interface to the dashboard allowing to monitor the backend (including API costs) and manage users
- Fully separate the backend and frontend, using an API to communicate between them (with permissions depending on users)
- Use playwright for scraping, which is more flexible than Selenium
- Implement more tests
