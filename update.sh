#!/usr/bin/env bash
bash /opt/python/current/env
source /opt/python/run/venv/bin/activate
python /opt/python/current/app/manage.py node_updates
