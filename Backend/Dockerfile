# Step 1: Use official Python image as a base
FROM python:3.10-slim-buster

# Step 2: Set the working directory in the container
WORKDIR /app

# Step 3: Copy the requirements file
COPY requirements.txt .

# Step 4: Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the rest of the application files
COPY . .

# Step 6: Expose the port (default 8000 for FastAPI)
EXPOSE 8000

# Step 7: Run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
