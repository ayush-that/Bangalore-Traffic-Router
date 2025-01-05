from flask import Flask, render_template, request, jsonify
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import folium
import sqlite3
import json
from datetime import datetime
import math
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize Nominatim geocoder
geolocator = Nominatim(user_agent="bangalore_traffic_router")

# Bangalore center coordinates
BANGALORE_CENTER = [12.9716, 77.5946]
BANGALORE_BOUNDS = {
    "min_lat": 12.8347,
    "max_lat": 13.1407,
    "min_lon": 77.3947,
    "max_lon": 77.7519,
}


def init_db():
    try:
        conn = sqlite3.connect("bangalore_traffic.db")
        c = conn.cursor()

        # Create tables for bus stops and routes
        c.execute(
            """CREATE TABLE IF NOT EXISTS bus_stops
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL UNIQUE,
                      latitude REAL NOT NULL,
                      longitude REAL NOT NULL)"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS routes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      start_stop_id INTEGER,
                      end_stop_id INTEGER,
                      route_data TEXT,
                      estimated_time INTEGER,
                      timestamp DATETIME,
                      FOREIGN KEY (start_stop_id) REFERENCES bus_stops (id),
                      FOREIGN KEY (end_stop_id) REFERENCES bus_stops (id))"""
        )

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


def estimate_travel_time(start_coords, end_coords):
    """
    Estimate travel time based on distance and average speed
    Returns time in minutes
    """
    try:
        distance = geodesic(start_coords, end_coords).kilometers
        avg_speed = 20  # km/h (accounting for traffic)
        return math.ceil((distance / avg_speed) * 60)  # Convert to minutes
    except Exception as e:
        logger.error(f"Error estimating travel time: {str(e)}")
        raise


def is_within_bangalore(lat, lon):
    """Check if coordinates are within Bangalore bounds"""
    return (
        BANGALORE_BOUNDS["min_lat"] <= lat <= BANGALORE_BOUNDS["max_lat"]
        and BANGALORE_BOUNDS["min_lon"] <= lon <= BANGALORE_BOUNDS["max_lon"]
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/calculate_route", methods=["POST"])
def calculate_route():
    try:
        data = request.get_json()
        if not data or "start" not in data or "end" not in data:
            return jsonify({"error": "Invalid request data"}), 400

        start_location = data["start"]
        end_location = data["end"]

        logger.info(f"Calculating route from {start_location} to {end_location}")

        # Geocode locations
        start_loc = geolocator.geocode(f"{start_location}, Bangalore, Karnataka, India")
        end_loc = geolocator.geocode(f"{end_location}, Bangalore, Karnataka, India")

        if not start_loc or not end_loc:
            logger.warning(
                f"Location not found: start={bool(start_loc)}, end={bool(end_loc)}"
            )
            return jsonify({"error": "One or both locations not found"}), 404

        logger.debug(f"Start coordinates: {start_loc.latitude}, {start_loc.longitude}")
        logger.debug(f"End coordinates: {end_loc.latitude}, {end_loc.longitude}")

        # Verify locations are within Bangalore
        if not (
            is_within_bangalore(start_loc.latitude, start_loc.longitude)
            and is_within_bangalore(end_loc.latitude, end_loc.longitude)
        ):
            return (
                jsonify({"error": "Locations must be within Bangalore city limits"}),
                400,
            )

        # Calculate estimated time
        estimated_time = estimate_travel_time(
            (start_loc.latitude, start_loc.longitude),
            (end_loc.latitude, end_loc.longitude),
        )

        # Create a map centered between start and end points
        center_lat = (start_loc.latitude + end_loc.latitude) / 2
        center_lon = (start_loc.longitude + end_loc.longitude) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

        # Add markers for start and end points
        folium.Marker(
            [start_loc.latitude, start_loc.longitude],
            popup="Start: " + start_location,
            icon=folium.Icon(color="green"),
        ).add_to(m)

        folium.Marker(
            [end_loc.latitude, end_loc.longitude],
            popup="End: " + end_location,
            icon=folium.Icon(color="red"),
        ).add_to(m)

        # Draw a line between points
        points = [
            [start_loc.latitude, start_loc.longitude],
            [end_loc.latitude, end_loc.longitude],
        ]
        folium.PolyLine(points, weight=2, color="blue", opacity=0.8).add_to(m)

        try:
            # Store route in database
            conn = sqlite3.connect("bangalore_traffic.db")
            c = conn.cursor()

            # Store or get start location
            c.execute(
                """INSERT OR IGNORE INTO bus_stops (name, latitude, longitude)
                        VALUES (?, ?, ?)""",
                (start_location, start_loc.latitude, start_loc.longitude),
            )
            c.execute("SELECT id FROM bus_stops WHERE name = ?", (start_location,))
            start_id = c.fetchone()[0]

            # Store or get end location
            c.execute(
                """INSERT OR IGNORE INTO bus_stops (name, latitude, longitude)
                        VALUES (?, ?, ?)""",
                (end_location, end_loc.latitude, end_loc.longitude),
            )
            c.execute("SELECT id FROM bus_stops WHERE name = ?", (end_location,))
            end_id = c.fetchone()[0]

            # Store route
            route_data = json.dumps(points)
            c.execute(
                """INSERT INTO routes (start_stop_id, end_stop_id, route_data, 
                                           estimated_time, timestamp)
                        VALUES (?, ?, ?, ?, ?)""",
                (start_id, end_id, route_data, estimated_time, datetime.now()),
            )

            conn.commit()
            conn.close()
            logger.info("Route stored in database successfully")

        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}")
            # Continue even if database storage fails

        return jsonify({"estimated_time": estimated_time, "map_html": m._repr_html_()})

    except Exception as e:
        logger.error(f"Error calculating route: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
