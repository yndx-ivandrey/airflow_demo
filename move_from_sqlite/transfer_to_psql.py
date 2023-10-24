import random
import sqlite3
import uuid
from dataclasses import dataclass, field

from db_settings import (GENRE_TABLE, MOVIE_TABLE, MOVIES_ACTORS_M2M_TABLE,
                         MOVIES_DIRECTORS_M2M_TABLE, MOVIES_GENRES_M2M_TABLE,
                         MOVIES_WRITERS_M2M_TABLE, PERSON_TABLE, SCHEMA)
from logger import logger
from psycopg2.extras import DictCursor, execute_values


@dataclass
class Movie:
    title: str
    description: str
    is_suspicious: bool
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    imdb_rating: float = field(default=0.0)


@dataclass
class Person:
    name: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)


class SQLiteLoader:
    def __init__(self, conn: sqlite3.Connection):
        self.sql_conn = conn.cursor()

    def load_writers(self) -> dict:
        writers = {}
        for writer in self.sql_conn.execute('SELECT DISTINCT id, name FROM writers'):
            writers[writer['id']] = writer['name']
        return writers

    def load_movies(self) -> (list, list):
        query = """
        WITH actors_list as (
            SELECT m.id, group_concat(a.name) as actors
            FROM movies m
                     LEFT JOIN movie_actors ma on m.id = ma.movie_id
                     LEFT JOIN actors a on ma.actor_id = a.id
            GROUP BY m.id
        )
        SELECT m.id, genre, director, title, plot, 
                imdb_rating, actors_list.actors,
               CASE
                    WHEN m.writers = '' THEN m.writer
                    ELSE replace(replace(replace(replace(m.writers, '[{"id": ', ''), '}, {"id": ', ','), '}]', ''), '"', '')
               END AS writers_ids
        FROM movies m
        LEFT JOIN actors_list ON m.id = actors_list.id
        """
        movies = self.sql_conn.execute(query).fetchall()
        return movies, self.load_writers()


class PostgresSaver:
    def __init__(self, psql_conn: DictCursor):
        self.psql_conn = psql_conn
        self.movies = list()
        self.people = dict()
        self.genres = dict()
        self.subtables = {
            MOVIES_DIRECTORS_M2M_TABLE: [],
            MOVIES_ACTORS_M2M_TABLE: [],
            MOVIES_GENRES_M2M_TABLE: [],
            MOVIES_WRITERS_M2M_TABLE: [],
        }

    def save_all_data(self, movies_writers: tuple):
        self.clear_all_data()
        movies, all_writers = movies_writers

        for movie in movies:
            created_movie = Movie(
                title=movie['title'],
                is_suspicious=True if random.randrange(10) > 8 else False,
                description=movie['plot'] if movie['plot'] != 'N/A' else '',
                imdb_rating=movie['imdb_rating'] if movie['imdb_rating'] != 'N/A' else 0,
            )

            self.movies.append(created_movie)

            movie_writers_ids = movie['writers_ids'].split(',')
            writers_names = ','.join(
                [all_writers[writer_id] for writer_id in all_writers if writer_id in movie_writers_ids]
            )

            data_to_process = (
                (movie['director'], 'directors', str(created_movie.id), False),
                (movie['actors'], 'actors', str(created_movie.id), False),
                (movie['genre'], 'genres', str(created_movie.id), True),
                (writers_names, 'writers', str(created_movie.id), False),
            )
            for item in data_to_process:
                self.get_or_create_entities(
                    name_raw=item[0], position=item[1], movie_id=item[2], is_genre_generator=item[3],
                )
        self.save_data_to_database()

    def __batch_insert(self, query: str, data: list):
        execute_values(self.psql_conn, query, data, template=None, page_size=100)

    def __save_genres_to_db(self, data):
        insert_query = f'INSERT INTO {SCHEMA}.{GENRE_TABLE} (id, title)' f' VALUES %s'
        self.__batch_insert(insert_query, data)

    def __save_movies_to_db(self, data):
        insert_query = (
            f'INSERT INTO {SCHEMA}.{MOVIE_TABLE} '
            f'(id, '
            f'title, '
            f'is_suspicious, '
            f'description, '
            f'imdb_rating) VALUES %s'
        )
        self.__batch_insert(insert_query, data)

    def __save_people_to_db(self, data):
        insert_query = f'INSERT INTO {SCHEMA}.{PERSON_TABLE} (id, last_name) VALUES %s'
        self.__batch_insert(insert_query, data)

    def __save_movies_genres_rel_to_db(self, data):
        insert_query = f'INSERT INTO {SCHEMA}.{MOVIES_GENRES_M2M_TABLE} (movie_id, genre_id) VALUES %s'
        self.__batch_insert(insert_query, data)

    def __save_movies_people_M2M_to_db(self):
        for table in [
            MOVIES_DIRECTORS_M2M_TABLE,
            MOVIES_ACTORS_M2M_TABLE,
            MOVIES_WRITERS_M2M_TABLE,
        ]:
            insert_query = f'INSERT INTO {SCHEMA}.{table} (movie_id, person_id) VALUES %s ON CONFLICT DO NOTHING'
            self.__batch_insert(insert_query, self.subtables[table])

    def save_data_to_database(self):
        movies_list = [
            (
                str(created_movie.id),
                created_movie.title,
                created_movie.is_suspicious,
                created_movie.description,
                created_movie.imdb_rating,
            )
            for created_movie in self.movies
        ]
        self.__save_movies_to_db(movies_list)

        self.__save_genres_to_db([self.genres[uid] for uid in self.genres])

        self.__save_people_to_db([self.people[uid] for uid in self.people])

        self.__save_movies_genres_rel_to_db(self.subtables[MOVIES_GENRES_M2M_TABLE])

        self.__save_movies_people_M2M_to_db()

        self.psql_conn.execute(f'update {SCHEMA}.{PERSON_TABLE} set last_name = TRIM(last_name)')

    def clear_all_data(self):
        logger.debug('Clear all old data in pgsql')
        tables = (
            PERSON_TABLE,
            MOVIES_GENRES_M2M_TABLE,
            MOVIES_ACTORS_M2M_TABLE,
            MOVIES_DIRECTORS_M2M_TABLE,
            MOVIES_WRITERS_M2M_TABLE,
            GENRE_TABLE,
            MOVIE_TABLE,
        )
        for table in tables:
            self.psql_conn.execute(f'TRUNCATE {SCHEMA}.{table} CASCADE')

    def get_or_create_entities(
        self, name_raw: str, position: str, movie_id: str, is_genre_generator: bool = False,
    ) -> None:
        names_or_titles = [x.strip() for x in name_raw.split(',')]
        for name in names_or_titles:
            if name == 'N/A':
                continue
            result = self.__check_entity_existance(name, is_genre_generator)
            self.subtables[f'movies_movie_{position}'].append((movie_id, result))

    def __check_entity_existance(self, name: str, is_genre_generator: bool) -> str:
        dict_to_search = self.people if not is_genre_generator else self.genres
        found_id = dict_to_search.get(name)
        if found_id:
            return found_id[0]
        person = Person(name=name)
        dict_to_search[person.name] = (str(person.id), person.name.strip())
        return str(person.id)
