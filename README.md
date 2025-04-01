# MLOps
Project for the Deployment of Data Science projets course at ENSAE
- Presentation: https://www.ensae.fr/courses/6052-mise-en-production-des-projets-de-data-science
- Companion website: https://ensae-reproductibilite.github.io/website/

Aim = monitor the reception of movies...

## Implementation
3 main components:
- **scrapping** => with Selenium
- **aspect-based sentiment analysis** => with the openAI API to query gpt-4o-mini
- **dashboard**

Orchestration by a main script that runs periodically to scrap new reviews and update votes, launch the sentiment analysis, and update the dashboard.
- Every hour: check for new reviews => if yes, rescrap for content => relaunch sentiment analysis for new or edited reviews
- Every 24 hours: rescrap for votes

Data is stored in a PostgreSQL database and backuped in S3-not working in Docker?

## Installation
Chrome: run in the terminal from the install directory:
`chrome.sh && ./chrome.sh`

Python packages:
`pip install -r requirements.txt`

Databases: 
In the Datalab, launch a separate Postgresql service then update the `.env` with its parameters:
- DB_NAME=
- DB_USER=
- DB_PASSWORD=
- DB_HOST=
In Docker, the Postgresql is launched automatically and the parameters are set accordingly?
Then run `db_init.ipynb`

OpenAI: specify OPENAI_API_KEY in the `.env` file.

## Sentiment analysis
Must be carried at the aspect level, to identify the opinions related to the main features of the movie. This is a seriously difficult task that dedicated models still struggle to solve (see: https://arxiv.org/abs/2311.10777). Some models are able to extract aspects and opinions autonomously, but at a very granulous level, making their results hard to use at scale.

Solution: offload the task to generative LLMs. A cursory experimentation shows that this works well with an adequate prompt. However, it requires big models, that cannot be run locally but must be called through APIs.

The current implementation relies on gpt-4o-mini from OpenAI, which is inexpensive ($0.15 / M tokens) but rather slow. It requires an API key stored in the .env file. An alternative would be to use Gemini from Google, which has a free tier (albeit with rates limits and requiring an API key as well).

## Dashboard
With Streamlit? Apache superset?

With...
- Header presenting the movie + time since last scrapping
- Total number of reviews + graph of their publication date
- Average grade + graph of its evolution over time
- For each sentiment + overall sentiment: average score + histogram
- ...

## To do
- Implement consistency checks for the results of scrapping and API calls
- Provide example data for an old movie (included in the Git repo)
- Offer the possibility to add new movies from the dashboard, preferably without too many reviews to reduce processing times
- *Optionnal:* switch db to asynchronous
- *Optionnal:* switch from GPT to Gemini 
- *Optionnal:* use ArgoCD
- *Optionnal:* API

## Checklist
- The project is well structured
- The code is formatted properly => Black + Flake8
- The code is documented
- Logs are collected
- A test procedure is available => select an old movie with 2-3 reviews to run the code on
- A Docker container is provided with postgresql install
