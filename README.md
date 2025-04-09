# The IMDb Reviews Tracker
This project tracks the reception of movies based on user reviews published on [IMDb](https://www.imdb.com). It was realised during the [Deployment of Data Science Projects](https://www.ensae.fr/courses/6052-mise-en-production-des-projets-de-data-science) course at ENSAE (see the [companion website](https://ensae-reproductibilite.github.io/website/)).

## 1. Implementation
There are 4 main components:
- **Web scrapping**
- **Aspect-based sentiment analysis**
- **Dashboard**
- **User management**

Data collection is orchestrated by a scheduler which ensures that...
- Movie metadata is rescraped every hour to check if new reviews have been published.
- Movie reviews are rescraped entirely every 24 hours or when new reviews have been detected.
- No more than 5 movies are scrapped concurrently to avoid overloading the system.
- The database is backed up every hour.

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
2. Installs Python and dependencies within a virtual environment
3. Checks if credentials are present
4. Sets up the database
5. Launches the scheduler

The state of the scheduler can be checked with `pgrep -fl scheduler.py`.

#### With Docker
A `docker-compose.yml` is provided which runs the tracker, the database and the dashboard as distinct services.

An `.env` file is required, including parameters for the backup on S3 which can be retrieved [here](https://datalab.sspcloud.fr/account/storage) (see `setup/.env.template`).

### Manage movies
They can be added or removed with `python -m src.utils.manage_movies --add '<movie_id_1>' '<movie_id_2>' --remove '<movie_id_3>'` (where `<movie_id>` must be retrieved manually from IMDb and stripped from the `tt` prefix, e.g., `0033467` for [Citizen Kane](https://www.imdb.com/title/tt0033467/?ref_=fn_all_ttl_1)).

## 2. Technical aspects

### Scrapping
In progress: parallelize by running 1 main script per movie
- *Adapting main.py*
- *Rewrite the scheduler, while...*
- - *Avoiding running too many scripts in parallel*
  - *Manage script duration to avoid launching a script for a movie if one is still running (especially if a new movie with many reviews has been added)*
- *Move backups to the scheduler*
- Have different logs per movie => need to create another log generator and pass the one to use as an argument to `PostgreSQLDatabase` and `IMDb` classes

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