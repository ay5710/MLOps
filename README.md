# MLOps
Project for the Deployment of Data Science projets course at ENSAE
- Presentation: https://www.ensae.fr/courses/6052-mise-en-production-des-projets-de-data-science
- Companion website: https://ensae-reproductibilite.github.io/website/

## Implementation

3 main components:
- scrapping
- aspect-based sentiment analysis
- dashboard

Orchestration by a main script running periodically that runs periodically to check whether new reviews have been published, existing reviews have been edited and their votes have changed, launch the sentiment analysis, update the dashboard.

Working:
- Databases for reviews
- Sentiment analysis

## Installation

Chrome: run in the terminal from the install directory:
`chrome.sh && ./chrome.sh`

Python packages:
`pip install -r requirements.txt`

Databases: edit the `.env` file with the following variables then run `db_init.ipynb`
- DB_NAME=
- DB_USER=
- DB_PASSWORD=
- DB_HOST=


If trouble loading the function from `install/`, check and set the wd with:
`os.getcwd()` and `os.chdir(os.path.expanduser("~/work/MLOps"))`

## Databases

Requires a postgreSQL database that cannot be run directly from Python. It is currently run in the DataLab.

A helper class is located in src/utils/db.py which retrieve logging information from the .env file.

Current implementation: 3 tables, for the movies, the reviews as scrapped, and the results of sentiment analysis.

To do:
- Switch to asynchronous?
- Include a postgreSQL service in the project Docker container

## Scrapping

Could be improved to get the exact votes and get rid of the language check, otherwise ok?

## Sentiment analysis

Must be carried at the aspect level, to identify the opinions related to the main features of the movie. This is a seriously difficult task that dedicated models still struggle to solve (see: https://arxiv.org/abs/2311.10777). Some models are able to extract aspects and opinions autonomously, but at a very granulous level, making their results hard to use at scale.

Solution: offload the task to generative LLMs. A cursory experimentation shows that this works well with an adequate prompt. However, it requires big models, that cannot be run locally but must be called through APIs.

The current implementation relies on gpt-4o-mini from OpenAI, which is inexpensive ($0.15 / M tokens) but rather slow. It requires an API key stored in the .env file. An alternative would be to use Gemini from Google, which has a free tier (albeit with rates limits and requiring an API key as well).

To do:
- Implement a consistency check for the API answers

## Dashboard

To do:
- Provide example data for an old movie (included in the Git repo)
- Offer the possibility to add new movies, preferably without too many reviews to reduce processing times

## Checklist
- The project is well structured
- The code is formatted properly => Black + Flake8
- The code is documented
- Logs are collected
- A test procedure is available => select an old movie with 2-3 reviews to run the code on
- A Docker container is provided
- *Optionnal:* API
- *Optionnal:* use ArgoCD
