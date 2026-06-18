#!/sh
set -e

echo "Waiting for postgres..."

python -c "
import socket
import time
import os
from urllib.parse import urlparse

db_url = os.environ.get('DATABASE_URL', '')
url = urlparse(db_url)
host = url.hostname or 'postgres-db'
port = url.port or 5432

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect((host, port))
        s.close()
        break
    except socket.error:
        time.sleep(1)
"

echo "PostgreSQL started. Running database migrations..."
alembic upgrade head

echo "Running data seed script..."
python seed.py

echo "Starting Streamlit application..."
exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0