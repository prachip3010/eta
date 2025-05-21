from flask import Flask, request, jsonify
import pandas as pd
import requests

app = Flask(__name__)

# Load the CSV once at startup
CSV_PATH = "route_df_processed.csv"
df = pd.read_csv(CSV_PATH)

API_KEY = "dbf1d1d3-729f-4cfb-aebd-d31facb9fbfd"

def get_route_info(p1, p2, key):
    url = "https://graphhopper.com/api/1/route"
    params = {
        "point": [f"{p1[0]},{p1[1]}", f"{p2[0]},{p2[1]}"],
        "profile": "car",
        "locale": "en-GB",
        "key": key,
        "elevation": "false",
        "instructions": "false"
    }
    try:
        response = requests.get(url, params=params).json()
        path = response["paths"][0]
        return path["distance"], path["time"]  # in meters, milliseconds
    except Exception as e:
        print("Error:", e)
        return None, None

@app.route("/get_travel_time", methods=["POST"])
def get_travel_time():
    data = request.get_json()

    bus_lat = data.get("lat")
    bus_long = data.get("long")
    src_rd_id = data.get("next_station_no")
    dst_rd_id = data.get("destination_station_no")

    if src_rd_id is None or dst_rd_id is None:
        return jsonify({"error": "Missing station numbers"}), 400

    src_row = df[df["rd_id"] == src_rd_id]
    dst_row = df[df["rd_id"] == dst_rd_id]

    if src_row.empty or dst_row.empty:
        return jsonify({"error": "Source or destination rd_id not found"}), 404

    if src_rd_id > dst_rd_id:
        return jsonify({"error": "Source rd_id must be less than or equal to destination rd_id"}), 400

    bus_location = (bus_lat, bus_long)
    source_coords = (src_row.iloc[0]["source_lat"], src_row.iloc[0]["source_long"])

    # Bus to Source
    bus_to_src_dist, bus_to_src_time = get_route_info(bus_location, source_coords, API_KEY)

    # Source to Destination
    route_rows = df[(df["rd_id"] >= src_rd_id) & (df["rd_id"] <= dst_rd_id)]
    total_dist = 0
    total_time = 0

    for _, r in route_rows.iterrows():
        dist, time = get_route_info(
            (r["source_lat"], r["source_long"]),
            (r["destination_lat"], r["destination_long"]),
            API_KEY
        )
        total_dist += dist or 0
        total_time += time or 0

    grand_total_time_ms = (bus_to_src_time or 0) + total_time
    grand_total_time_min = round(grand_total_time_ms / 1000 )

    return "Model is running."
    return jsonify({
        "total_time_seconds": grand_total_time_min
    })

if __name__ == '__main__':
    app.run(debug=True)
