#!/bin/bash

flask run
celery -A app.celery worker
