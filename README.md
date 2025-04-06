This project was realised during the [Deployment of Data Science Projects](https://www.ensae.fr/courses/6052-mise-en-production-des-projets-de-data-science) course at ENSAE (see the [companion website](https://ensae-reproductibilite.github.io/website/)). It aims to track the reception of movies based on user reviews published on [IMDb](https://www.imdb.com).

### Implementation
3 main components:
- **scrapping** => with Selenium
- **aspect-based sentiment analysis** => with the openAI API to query gpt-4o-mini
- **dashboard** => with Streamlit?

Orchestration by a scheduler running a main script periodically:
- Rescrap movie metadata every hour and check if new reviews have been published
- Rescrap everything every 24 hours or when new reviews are detected, launch the sentiment analysis and save

Data is stored in a PostgreSQL database and saved in S3 => *this may not work in Docker*

### Installation
#### In the DataLab
An installation script is available (to be launched with `chmod +x ./install.sh && ./install.sh`) which performs the following operations:

(1) Chrome: `chmod +x ./setup/chrome.sh && ./setup/chrome.sh`

(2) Python packages: `pip install -r ./setup/requirements.txt`

Databases: 
In the Datalab, launch a separate Postgresql service then update the `.env` with its parameters:
- DB_NAME=
- DB_USER=
- DB_PASSWORD=
- DB_HOST=
In Docker, the Postgresql is launched automatically and the parameters are set accordingly-hopefully...
Then, run `python -m setup.db_init.py`

For backups from outside the DataLab, add these parameters to the `.env` file:
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=
AWS_S3_ENDPOINT=
AWS_DEFAULT_REGION=

(3) OpenAI: set the OPENAI_API_KEY in the `.env` file.

(4) Launch the scheduler with `python scheduler.py &` (and check if it's running with `pgrep -fl scheduler.py`)

=> *Add a movie to track with `python -m src.utils.add_movie <movie_id>` (where `<movie_id>` must be retrieved manually from IMDb)*

#### With Docker
Use the provided `docker-compose.yml` file and the same `.env` as above (with `DB_HOST=db`).

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
- ...

### To do
- Add a function to remove movies
- Autocleaning of S3 directory => keep lonly the 5 last files for each table => lacks permissions?
- Implement consistency checks for the results of scrapping and API calls
- Offer the possibility to add new movies from the dashboard, preferably without too many reviews to reduce processing times
- *Optionnal:* use [enlighten](https://python-enlighten.readthedocs.io/en/stable/index.html) for progress bars
- *Optionnal:* switch from GPT to Gemini 
- *Optionnal:* use ArgoCD
- *Optionnal:* create an API

### Checklist
- The project is well structured
- The code is formatted properly => use Flake8
- The code is documented
- Logs are collected
- A test procedure is available => select an old movie with 2-3 reviews to run the code on
- A Docker container is provided with postgresql install

### Improvements
Which could have been done but have not...
- Use playwright for scrapping (more flexible than Selenium)
- Parallelize by running 1 main script per movie => would have require to move the db to asynchronous
- Implement (more) tests => but the log is already quite verbose