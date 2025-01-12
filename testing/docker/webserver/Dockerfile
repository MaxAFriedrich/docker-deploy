FROM python:3.11

# Set the working directory to /app
WORKDIR /app

# Copy server.py and index.html to /app
COPY server.py /app/
COPY index.html /app/

# Copy flag.txt to the root directory
COPY flag.txt /

# Expose port 8100
EXPOSE 80

# Run the server using Python 3.11
CMD ["python3", "server.py"]
