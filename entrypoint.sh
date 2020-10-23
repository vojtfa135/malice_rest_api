#!/bin/sh

nohup celery -A app.celery worker > celery.out &
flask run
