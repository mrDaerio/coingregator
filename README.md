# Coingregator

A simple API endpoint that enables the retrieval of data from multiple sources without rate limitations or access tokens.

The current use is mostly for cryptocurrency information retrieval (hence the name) and only works with:

-   [Coingecko](https://www.coingecko.com), whose API does not require an authentication
-   [Coinglass](https://www.coinglass.com/), whose API requires an authentication through an API key (provided with a free account)


## How it works

The application is written with a three tier architecture in mind:
 - a __frontend__, written with the `fastapi` framework and running on a `uvicorn` server instance.
 - a __database__, running on a redis instance.
 - an __updater__, a simple script to update the data in the database.

The requests are managed by the frontend, which asks the database for the data from the other APIs.
The updater runs, by default, once every hour.

Every tier is written to leverage asynchronous execution and is containerized and run through `docker compose`.

## Pre-installation steps

Before installing, you need to provide the following files (in the same directory of `docker-compose.yml`):

-   `api_keys.txt`, which currently should contain only your Coinglass API key
    
-   `coinlist.txt`, which contains the list of coins from Coinglass which you are interested in. A list of coins available at the time of writing is provided.


## Installation and execution

To install and run, use `docker compose`:

    docker compose up --build -d

The frontend server will be listening to GET requests on port 80.


## Use

You can retrieve the data from Coingecko at <http://localhost:80/coingecko> and the data from Coinglass at <http://localhost:80/coinglass/{operation}>.

The `operation` keyword in the Coinglass request can be:

-   `funding_rates_u`
-   `funding_rates_c`
-   `open_interest`

An optional `coin` parameter can be provided in the Coinglass request to specify which coin you want to retrieve information for.
(e.g: <http://localhost:80/coinglass/funding_rates_u?coin=BTC>)

An optional `page` parameter can be provided in the Coingecko request to specify which page you want to retrieve (see the [coingecko api](https://www.coingecko.com/en/api) documentation for more informations).
(e.g: <http://localhost:80/coingecko?page=4>)
