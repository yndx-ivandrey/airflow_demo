import json
from datetime import datetime, timedelta
from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.postgres_hook import PostgresHook
from airflow.models.taskinstance import TaskInstance
from airflow.providers.telegram.operators.telegram import TelegramOperator
from elasticsearch import Elasticsearch, helpers

import logging

from helpers.es_schema import MAPPING_MOVIES

SCHEMA = 'content'

PERSON_TABLE = 'movies_person'
MOVIES_GENRES_M2M_TABLE = 'movies_movie_genres'
MOVIES_ACTORS_M2M_TABLE = 'movies_movie_actors'
MOVIES_DIRECTORS_M2M_TABLE = 'movies_movie_directors'
MOVIES_WRITERS_M2M_TABLE = 'movies_movie_writers'
GENRE_TABLE = 'movies_genre'
MOVIE_TABLE = 'movies_movie'


def fetch_changed_movies_ids(ti: TaskInstance):
    sql = f"""
        SELECT m.id as id, m.updated_at as updated_at FROM {SCHEMA}.{MOVIE_TABLE} m 
        WHERE m.updated_at > %s
        ORDER BY m.updated_at asc
    """
    pg_hook = PostgresHook(postgres_conn_id='postgres_db')
    pg_conn = pg_hook.get_conn()
    cursor = pg_conn.cursor()

    last_updated = ti.xcom_pull(key='movies_updated_state', include_prior_dates=True) or str(datetime.min)
    logging.info('SQL query: %s', sql % last_updated)
    cursor.execute(sql, (last_updated,))
    items = cursor.fetchall()
    if items:
        ti.xcom_push(key='movies_updated_state', value=str(items[-1]['updated_at']))
    return set([x['id'] for x in items])


def fetch_changed_genres_movies_ids(ti: TaskInstance):
    sql = f"""
        SELECT mmg.movie_id as id, mg.updated_at as updated_at  FROM {SCHEMA}.{GENRE_TABLE} mg
        LEFT JOIN {SCHEMA}.{MOVIES_GENRES_M2M_TABLE} mmg ON mmg.genre_id = mg.id
        WHERE mg.updated_at > %s
        ORDER BY mg.updated_at asc
    """
    pg_hook = PostgresHook(postgres_conn_id='postgres_db')
    pg_conn = pg_hook.get_conn()
    cursor = pg_conn.cursor()

    last_updated = ti.xcom_pull(key='genres_updated_state', include_prior_dates=True) or str(datetime.min)
    cursor.execute(sql, (last_updated,))

    logging.info('SQL query: %s', sql % last_updated)

    items = cursor.fetchall()
    if items:
        ti.xcom_push(key='genres_updated_state', value=str(items[-1]['updated_at']))
    return set([x['id'] for x in items])


def fetch_changed_people_movies_ids(ti: TaskInstance):
    pg_hook = PostgresHook(postgres_conn_id='postgres_db')
    pg_conn = pg_hook.get_conn()
    cursor = pg_conn.cursor()

    tables = (
        f'{SCHEMA}.{MOVIES_ACTORS_M2M_TABLE}',
        f'{SCHEMA}.{MOVIES_DIRECTORS_M2M_TABLE}',
        f'{SCHEMA}.{MOVIES_WRITERS_M2M_TABLE}',
    )

    last_updated = ti.xcom_pull(key='people_updated_state', include_prior_dates=True) or str(datetime.min)
    movies_ids = set()

    for table in tables:
        sql = f"""
            SELECT movie_id as id FROM {table}
            WHERE person_id IN (
                SELECT p.id as id FROM {SCHEMA}.{PERSON_TABLE} p 
                WHERE p.updated_at > %s
            )
        """
        cursor.execute(sql, (last_updated,))
        results = set([x['id'] for x in cursor.fetchall()])
        movies_ids = movies_ids | results
        cursor.execute(sql, (last_updated,))
        logging.info('SQL query: %s', sql % last_updated)
        logging.info('Results are: %s', results)

    if len(movies_ids):
        ti.xcom_push(key='people_updated_state', value=str(datetime.now()))
    return movies_ids


def accumulate_results(ti: TaskInstance):
    genres_ids, movies_ids, people_ids = ti.xcom_pull(
        task_ids=['fetch_changed_genres_movies_ids', 'fetch_changed_movies_ids', 'fetch_changed_people_movies_ids']
    )
    logging.info('Results fetched from database: %s', (genres_ids, movies_ids, people_ids))
    return genres_ids | movies_ids | people_ids


def enrich_results(ti: TaskInstance):
    ids = ti.xcom_pull(task_ids='accumulate_results')
    logging.info('Movies IDs need to enrich: %s', ids)

    if ids == set():
        logging.info('No records need to be updated')
        return []

    sql = f"""
        WITH actors_list as (
            SELECT m.id,
            string_agg(TRIM(CONCAT(a.last_name || ' ', a.first_name)), ',') as actors,
            string_agg(a.id::varchar, ',') as actors_ids
                FROM {SCHEMA}.{MOVIE_TABLE} m
                LEFT JOIN {SCHEMA}.{MOVIES_ACTORS_M2M_TABLE} ma on m.id = ma.movie_id
                LEFT JOIN {SCHEMA}.{PERSON_TABLE} a on ma.person_id = a.id
            GROUP BY m.id
        ),
        directors_list as (
            SELECT m.id,
            string_agg(TRIM(CONCAT(a.last_name || ' ', a.first_name)), ',') as directors,
            string_agg(a.id::varchar, ',') as directors_ids
                FROM {SCHEMA}.{MOVIE_TABLE} m
                LEFT JOIN {SCHEMA}.{MOVIES_DIRECTORS_M2M_TABLE} ma on m.id = ma.movie_id
                LEFT JOIN {SCHEMA}.{PERSON_TABLE} a on ma.person_id = a.id
            GROUP BY m.id
        ),
        writers_list as (
            SELECT m.id,
            string_agg(TRIM(CONCAT(a.last_name || ' ', a.first_name)), ',') as writers,
            string_agg(a.id::varchar, ',') as writers_ids
                FROM {SCHEMA}.{MOVIE_TABLE} m
                LEFT JOIN {SCHEMA}.{MOVIES_WRITERS_M2M_TABLE} mw on m.id = mw.movie_id
                LEFT JOIN {SCHEMA}.{PERSON_TABLE} a on mw.person_id = a.id
            GROUP BY m.id
        ),
        genres_list as (
            SELECT m.id,
            string_agg(g.title, ',') as genres,
            string_agg(g.id::varchar, ',') as genres_ids
                FROM {SCHEMA}.{MOVIE_TABLE} m
                LEFT JOIN {SCHEMA}.{MOVIES_GENRES_M2M_TABLE} mg on m.id = mg.movie_id
                LEFT JOIN {SCHEMA}.{GENRE_TABLE} g on mg.genre_id = g.id
            GROUP BY m.id
        )
        SELECT m.id as id,
        m.imdb_rating as imdb_rating,
        m.title as title,
        m.is_suspicious as is_suspicious,
        m.description as description,
        actors_list.actors as actors_names,
        actors_list.actors_ids as actors_ids,
        directors_list.directors as directors_names,
        directors_list.directors_ids as directors_ids,
        writers_list.writers as writers_names,
        writers_list.writers_ids as writers_ids,
        genres_list.genres as genres_titles,
        genres_list.genres_ids as genres_ids
        FROM {SCHEMA}.{MOVIE_TABLE} m
        LEFT JOIN actors_list ON m.id = actors_list.id
        LEFT JOIN writers_list ON m.id = writers_list.id
        LEFT JOIN directors_list ON m.id = directors_list.id
        LEFT JOIN genres_list ON m.id = genres_list.id
        WHERE m.id::varchar IN %(movies)s
    """
    pg_hook = PostgresHook(postgres_conn_id='postgres_db')
    pg_conn = pg_hook.get_conn()
    cursor = pg_conn.cursor()
    logging.info('SQL query: %s', sql)
    cursor.execute(sql, {'movies': tuple(ids)})
    results = cursor.fetchall()
    dict_result = [
        dict(x)
        for x in results
    ]
    json_object = json.dumps(dict_result, indent=4)
    logging.info('Enriched movies ready for ES: %s', json_object)
    return json_object


def es_create_index(ti: TaskInstance):
    elastic = Elasticsearch('http://elasticsearch:9200')
    # _ = elastic.indices.delete(index='movies', ignore=[400, 404])
    response = elastic.indices.create(index='movies', body=MAPPING_MOVIES, ignore=400)
    if 'acknowledged' in response:
        if response['acknowledged']:
            logging.info('Индекс создан: {}'.format(response['index']))
    elif 'error' in response:
        logging.error('Ошибка: {}'.format(response['error']['root_cause']))
    logging.info(response)


def write_to_es(ti):
    elastic = Elasticsearch('http://elasticsearch:9200')
    raw = ti.xcom_pull(task_ids='enrich_results')
    if not raw:
        return
    movies = json.loads(raw)
    logging.info(f'Processing {len(movies)} movie:')
    actions = []
    for movie in movies:
        actors = (
            [
                {'uuid': _id, 'full_name': name}
                for _id, name in zip(
                    movie['actors_ids'].split(','),
                    movie['actors_names'].split(','),
                )
            ]
            if movie['actors_ids']
            else []
        )
        directors = (
            [
                {'uuid': _id, 'full_name': name}
                for _id, name in zip(
                    movie['directors_ids'].split(','),
                    movie['directors_names'].split(','),
                )
            ]
            if movie['directors_ids']
            else []
        )
        writers = (
            [
                {'uuid': _id, 'full_name': name}
                for _id, name in zip(
                    movie['writers_ids'].split(','),
                    movie['writers_names'].split(','),
                )
            ]
            if movie['writers_ids']
            else []
        )
        genres = (
            [
                {'uuid': _id, 'name': name}
                for _id, name in zip(
                    movie['genres_ids'].split(','),
                    movie['genres_titles'].split(','),
                )
            ]
            if movie['genres_ids']
            else []
        )
        action = {
            '_index': 'movies',
            '_id': movie['id'],
            '_source': {
                'uuid': movie['id'],
                'imdb_rating': float(movie['imdb_rating']),
                'genres_titles': movie['genres_titles'],
                'title': movie['title'],
                'is_suspicious': movie['is_suspicious'],
                'description': movie['description'],
                'directors_names': movie['directors_names'],
                'actors_names': movie['actors_names'],
                'writers_names': movie['writers_names'],
                'genres': genres,
                'directors': directors,
                'actors': actors,
                'writers': writers,
            },
        }
        actions.append(action)

    helpers.bulk(elastic, actions)
    logging.info(f'Transfer completed, {len(movies)} updated...')
    return len(movies)


telegram_token = '6489792840:AAGiXzh3oHEGvVDVJC03SdAFvI198G2wdII'
telegram_chat_id = '269105707'


with DAG(
    dag_id='Theatre_ETL',
    schedule_interval=timedelta(minutes=1),
    start_date=datetime(year=2023, month=2, day=1),
    catchup=False,
) as dag:

    task_get_movies_ids = PythonOperator(
        task_id='fetch_changed_movies_ids', python_callable=fetch_changed_movies_ids, do_xcom_push=True
    )

    fetch_changed_genres_movies_ids = PythonOperator(
        task_id='fetch_changed_genres_movies_ids', python_callable=fetch_changed_genres_movies_ids
    )

    fetch_changed_people_movies_ids = PythonOperator(
        task_id='fetch_changed_people_movies_ids', python_callable=fetch_changed_people_movies_ids
    )

    accumulate_results = PythonOperator(task_id='accumulate_results', python_callable=accumulate_results)
    enrich_results = PythonOperator(task_id='enrich_results', python_callable=enrich_results)

    es_create_index = PythonOperator(task_id='es_create_index', python_callable=es_create_index)
    write_to_es = PythonOperator(task_id='write_to_es', python_callable=write_to_es)

    send_notification = TelegramOperator(
        task_id='send_notification',
        token=telegram_token,
        chat_id=telegram_chat_id,
        text='Было обновлено фильмов: {{ ti.xcom_pull(task_ids="write_to_es") }}',
    )

    es_create_index >> enrich_results
    task_get_movies_ids >> accumulate_results
    fetch_changed_genres_movies_ids >> accumulate_results
    fetch_changed_people_movies_ids >> accumulate_results
    accumulate_results >> enrich_results >> write_to_es >> send_notification
