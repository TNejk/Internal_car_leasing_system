FROM python:3

ENV PYTHONUNBUFFERED 1

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory and copy requirements file
WORKDIR /app
COPY req.txt /app/

# Install pip requirements
RUN python3 -m pip install -r req.txt

# Copy the rest of the application files
COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
RUN adduser -u 5679 --disabled-password --gecos "" apiuser && chown -R apiuser /app

RUN chown -R apiuser:apiuser /app

# Create a directory for excel reports
RUN mkdir -p ./reports && chown apiuser:apiuser ./reports

# Create a volume directory for car images, that will be reflected at: /var/www/fl.gamo.sosit-wh.net/images
RUN mkdir -p ./images && chown apiuser:apiuser ./images

USER apiuser

# Command to run the app using Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:9183", "main:app"]
#CMD ["python", "wsgi.py"]
