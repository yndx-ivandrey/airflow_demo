run:
	docker compose -f docker-compose-airflow.yaml -f docker-compose.yaml up -d

stop:
	docker compose -f docker-compose-airflow.yaml -f docker-compose.yaml down

django:
	cd ./django_admin && \
	uv sync --locked && \
	DJANGO_SUPERUSER_USERNAME=admin \
	DJANGO_SUPERUSER_PASSWORD=123123 \
	DJANGO_SUPERUSER_EMAIL=mail@mail.ru \
	uv run ./manage.py createsuperuser --noinput || true ; \
	uv run ./manage.py runserver

all: run django

.PHONY: run django stop

