# Bangalore Traffic Router

A web application that helps users find optimal routes between locations in Bangalore city, using OpenStreetMap data.

## Features

- Calculate routes between any two locations in Bangalore
- View routes on an interactive map
- Get estimated travel time
- SQLite database for storing bus stops and routes

## Setup

1. Install Python 3.8 or higher

2. Install required packages:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
python app.py
```

4. Open your web browser and navigate to `http://localhost:5000`

## Usage

1. Enter your start location in Bangalore (e.g., "Indiranagar")
2. Enter your destination (e.g., "Whitefield")
3. Click "Calculate Route"
4. View the route on the map and check the estimated travel time

## Technical Details

- Uses OSMnx for handling OpenStreetMap data
- Flask web framework for the backend
- Folium for map visualization
- SQLite database for storing route information
- Nominatim geocoding service for location search

## Note

This is a basic version of the application. Future updates will include:

- Real-time traffic data integration
- Multiple route options
- Bus stop information
- Route optimization based on traffic conditions
