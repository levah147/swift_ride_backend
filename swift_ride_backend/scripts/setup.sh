#!/bin/bash

# Create virtual environment
echo "Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install development dependencies
echo "Installing development dependencies..."
pip install -r requirements/development.txt

# Create .env file from example if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    
    # Generate a random secret key
    SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")
    sed -i "s/your-secret-key-here/$SECRET_KEY/g" .env
fi

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs

# Run migrations
echo "Running migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser
echo "Creating superuser..."
python manage.py createsuperuser

echo "Setup complete! You can now run the development server with:"
echo "python manage.py runserver"
