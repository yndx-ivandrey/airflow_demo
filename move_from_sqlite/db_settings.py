import os

import dotenv

dotenv.load_dotenv()


SCHEMA = 'content'

PERSON_TABLE = 'movies_person'
MOVIES_GENRES_M2M_TABLE = 'movies_movie_genres'
MOVIES_ACTORS_M2M_TABLE = 'movies_movie_actors'
MOVIES_DIRECTORS_M2M_TABLE = 'movies_movie_directors'
MOVIES_WRITERS_M2M_TABLE = 'movies_movie_writers'
GENRE_TABLE = 'movies_genre'
MOVIE_TABLE = 'movies_movie'

DSL = {
    'dbname': os.getenv('POSTGRES_DB'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'host': os.getenv('SQL_HOST'),
    'port': os.getenv('SQL_PORT'),
}
