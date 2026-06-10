#!/bin/bash
# Render deployment script to initialize database before starting app

set -e

echo "Creating database tables..."
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('✓ Database tables created')"

echo "Starting Flask application..."
exec gunicorn --bind 0.0.0.0:$PORT app:app
