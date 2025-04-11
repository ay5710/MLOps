# The IMDb Reviews Tracker
This project tracks the reception of movies based on user reviews published on [IMDb](https://www.imdb.com). It was realised during the [Deployment of Data Science Projects](https://www.ensae.fr/courses/6052-mise-en-production-des-projets-de-data-science) course at ENSAE (see the [companion website](https://ensae-reproductibilite.github.io/website/)).

## 1. Implementation
There are 4 main components:
- **Web scrapping**
- **Aspect-based sentiment analysis**
- **Dashboard**
- **User management**

Data collection is orchestrated by a scheduler.

Data is stored in a PostgreSQL database and saved in s3. A sample with 2 movies is provided.

Architecture:
<pre>
app/
├── data/
│   ├── backup/
│   └── sample/
├── logs/
├── notebooks/
├── setup/
│   ├── .env.template
│   ├── db_init.py
│   └── requirements.txt
├── src/
│   ├── analysis.py
│   ├── backup.py    
│   ├── scrapping.py
│   └── utils/
│       ├── db.py
│       ├── logger.py
│       ├── manage_movies.py
│       └── s3.py
├── test/
│       └── connection_test.py
├── main.py
├── scheduler.py</pre>

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

An `.env` file is required, including parameters for the backup on S3 which can be retrieved [here](https://datalab.sspcloud.fr/account/storage) (see `setup/.env.template`).

### Manage movies
They can be added or removed with `poetry run python -m src.utils.manage_movies --add '<movie_id_1>' '<movie_id_2>' --remove '<movie_id_3>'` (where `<movie_id>` must be retrieved manually from IMDb, e.g., `tt0033467` for [Citizen Kane](https://www.imdb.com/title/tt0033467/?ref_=fn_all_ttl_1)).

## 2. Technical aspects

### Scrapping
Data must be retrieved from 3 different pages on the IMDB website: 
- main page of the movie for the metadata, including the number of published reviews
- main page of reviews, where only the 25 more popular reviews are displayed by default, where the actual reviews are sometimes hidden behind `<poiler>`markup, and where upvotes and downvotes are rounded above 999
- individual pages of reviews, where exact votes appear

Made it necessary to interact with the webpages:
- Display all reviews on the main reviews page => it turned out that the button for displaying all reviews stops at the closest multiple of 25, then another button must be clicked for the remaining reviews
- Access text hidden behind `<spoiler>` markup => it turned out more reliable to do on the individual pages of reviews, although it is slower

Scrapping proceeds as follows:
- Every hour, scrap the main page to retrieve the metadata
- If new reviews has been published, the movie have just been added to the db, or the last full scrapping is > 24h old, scrap the reviews main page
- If spoiler markups or rounded votes are present, scrap the corresponding individual review pages
- Update the tables, while indicating if reviews are new or have been edited so they can be analyzed

A scheduler launches a script per-movie every hour, while ensuring that no more than 5 movies are scrapped concurrently to avoid overloading the system, and that the database is backed up every hour.

This process is not perfectly reliable, sometimes a few more reviews are extracted than should be present. Behavior of the IMDb website seems somewhat erratic?

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
With Streamlit? Apache superset?

***Would it be easier to store `movie_id` in the `reviews_sentiments` table?***

With...
- Header presenting the movie + time since last scrapping
- Total number of reviews + graph of their publication date
- Average grade + graph of its evolution over time
- For each sentiment + overall sentiment: average score + histogram
- The possibility to add or remove movies
- ...

## 3. Possible improvements
Which could have been done but have not...
- Use playwright for scrapping (more flexible than Selenium)
- Implement (more) tests
- Create different clients able to track different movies, with a logging interface to the dashboard

### To do
- *Optionnal:* use ArgoCD
- *Optionnal:* create an API

### Checklist
- The code is formatted properly => use Flake8
- Logs are collected
- A test procedure is available