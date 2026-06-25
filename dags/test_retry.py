from datetime import datetime, timedelta
from airflow.sdk import task, dag
from airflow.providers.standard.operators.empty import EmptyOperator
from random import randint
import logging


@dag(
    dag_id="simple_retry",
    dag_display_name="Simple retry DAG demo",
    start_date=datetime(2026, 6, 25),
    schedule=None,
    catchup=False,
)
def test_retry_pipeline():

    @task(retries=5, retry_delay=timedelta(seconds=1))
    def first() -> None:
        if randint(0, 9) < 6:
            logging.info("Try again - you have bad luck today")
            raise RuntimeError("Bad luck!")
        logging.info("Task completed")

    third_task = EmptyOperator(task_id="third_task")
    first_task = first()
    first_task >> third_task


test_retry_pipeline()
