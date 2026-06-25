from datetime import datetime
from airflow.models import DAG
from airflow.models.taskinstance import TaskInstance
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator
import logging


def first(ti: TaskInstance):
    result = 1
    for x in range(100_000_000):
        result = result + x
    return result


def second(ti: TaskInstance):
    prev_result = ti.xcom_pull(task_ids="first_task")
    logging.info("The result is: %s", prev_result)


with DAG(
    dag_id="simple_test_dag",
    schedule=None,
    start_date=datetime(year=2025, month=10, day=1),
    catchup=False,
) as dag:

    first_task = PythonOperator(task_id="first_task", python_callable=first)
    second_task = PythonOperator(task_id="second_task", python_callable=second)

    third_task = EmptyOperator(task_id="third_task")

    first_task >> second_task >> third_task
