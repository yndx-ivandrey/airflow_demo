from datetime import datetime
from airflow.sdk import task, dag
from airflow.providers.standard.operators.empty import EmptyOperator
import logging


@dag(
    dag_id="simple_dag_demo",
    dag_display_name="Simple DAG demo",
    start_date=datetime(2026, 6, 25),
    schedule=None,
    catchup=False,
)
def test_simple_pipeline():

    @task()
    def first() -> int:
        result = 1
        for x in range(100_000_000):
            result = result + x
        return result

    @task()
    def second(prev_result: int):
        logging.info("The result is: %s", prev_result)

    third_task = EmptyOperator(task_id="third_task")

    second_task = second(first())
    second_task >> third_task


test_simple_pipeline()
