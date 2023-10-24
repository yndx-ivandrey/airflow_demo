from datetime import timedelta, datetime
from airflow.models import DAG
from airflow.models.taskinstance import TaskInstance
from airflow.operators.python import PythonOperator
import logging


def first(ti: TaskInstance):
    result = 1
    for x in range(100_000_000):
        result = result + x
    return result


def second(ti: TaskInstance):
    prev_result = ti.xcom_pull(task_ids='first_task')
    logging.info('The result is: %s', prev_result)


with DAG(
    dag_id='simple_test_dag',
    schedule_interval=None,
    start_date=datetime(year=2023, month=2, day=1),
    catchup=False,
) as dag:

    first_task = PythonOperator(
        task_id='first_task', python_callable=first
    )
    second_task = PythonOperator(
        task_id='second_task', python_callable=second
    )

    first_task >> second_task

