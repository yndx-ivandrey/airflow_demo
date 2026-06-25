




from airflow.providers.standard.operators.python import PythonOperator

def process_data():
    print("Processing")

python_task = PythonOperator(
    task_id="process_data",
    python_callable=process_data
)










from airflow.providers.standard.operators.bash import BashOperator

bash_task = BashOperator(
    task_id="list_files",
    bash_command="ls -la"
)


python_task >> [bash_task, bash_task] >> python_task >> bash_task











from airflow.providers.http.operators.http import HttpOperator

http_task = HttpOperator(
    task_id="get_data",
    method="GET",
    endpoint="/users"
)













from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator

sql_task = SQLExecuteQueryOperator(
    task_id="load_data",
    postgres_conn_id="postgres_default",
    sql="SELECT * FROM users"
)

















from airflow.providers.standard.operators.python import BranchPythonOperator

def choose_branch():
    return "success_task"

branch = BranchPythonOperator(
    task_id="branch",
    python_callable=choose_branch
)
