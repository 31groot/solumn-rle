FROM python:3.11.9-slim
COPY stub_server.py products.json relay.crt relay.key /srv/
CMD ["python3", "-u", "/srv/stub_server.py"]
