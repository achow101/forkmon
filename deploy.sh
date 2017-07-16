#! /bin/bash
# Script to deploy everything
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic
