import os
import json
import pickle
import requests
import traceback

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

MODEL_PATH = os.environ.get("MODEL_PATH", "new_model_realtime.pickle")
WAQI_TOKEN = os.environ.get("WAQI_TOKEN")
DEBUG_MODE = os.environ.get("DEBUG_MODE", "true").lower() == "true"

# Load ML model
try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
except Exception as e:
    model = None
    print(f"[ERROR] Could not load model from {MODEL_PATH}: {e}")
    traceback.print_exc()

stations_list = []  # store all stations in a flat list

def fetch_all_stations():
    global stations_list
    stations_list = []
    try:
        # This covers India — change lat/lng to expand area if needed
        url = f"https://api.waqi.info/map/bounds/?token={WAQI_TOKEN}&latlng=8.0,68.0,37.0,97.0"
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            print(f"[WARN] WAQI API status not ok: {data.get('status')}")
            return

        for station in data.get("data", []):
            name = station['station']['name']
            uid = station['uid']
            stations_list.append({"name": name, "uid": uid})

        print(f"[INFO] Loaded {len(stations_list)} stations.")

    except Exception as e:
        print("[ERROR] Failed to fetch stations from WAQI API:")
        traceback.print_exc()

fetch_all_stations()

@app.route("/")
def index():
    return render_template("index.html", waqi_token=WAQI_TOKEN)

@app.route("/stations_list")
def get_all_stations():
    try:
        return jsonify(stations_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/predict", methods=["POST"])
def predict_ajax():
    try:
        if model is None:
            raise RuntimeError(f"Model not loaded from {MODEL_PATH}")
        if not WAQI_TOKEN:
            raise EnvironmentError("WAQI_TOKEN not set in server environment.")

        station_uid = request.form.get("input3", "").strip()
        if not station_uid:
            raise ValueError("input3 (station UID) is required.")

        base_url = "https://api.waqi.info"
        r = requests.get(f"{base_url}/feed/@{station_uid}/?token={WAQI_TOKEN}", timeout=10)
        r.raise_for_status()
        data = r.json()

        if data.get("status") != "ok":
            raise ValueError(f"WAQI API returned status: {data.get('status')}")

        pollutants = ['pm25', 'pm10', 'o3']
        val = []
        for p in pollutants:
            try:
                val.append(data['data']['forecast']['daily'][p][0]['avg'])
            except Exception:
                val.append(0.0)

        obs_val = [[], [], []]
        for idx, pollutant in enumerate(pollutants):
            daily_list = data['data']['forecast']['daily'].get(pollutant, [])
            for i in range(min(7, len(daily_list))):
                entry = daily_list[i]
                obs_val[idx].append([
                    entry.get('avg', 0.0),
                    entry.get('max', 0.0),
                    entry.get('min', 0.0),
                    entry.get('day', "")
                ])
            while len(obs_val[idx]) < 7:
                obs_val[idx].append([0.0, 0.0, 0.0, ""])

        temp_l = []
        for day_idx in range(7):
            date_for_day = obs_val[0][day_idx][3]
            try:
                pred_avg = float(model.predict([[obs_val[0][day_idx][0], obs_val[1][day_idx][0], obs_val[2][day_idx][0]]])[0])
            except Exception:
                pred_avg = 0.0
            try:
                pred_max = float(model.predict([[obs_val[0][day_idx][1], obs_val[1][day_idx][1], obs_val[2][day_idx][1]]])[0])
            except Exception:
                pred_max = 0.0
            try:
                pred_min = float(model.predict([[obs_val[0][day_idx][2], obs_val[1][day_idx][2], obs_val[2][day_idx][2]]])[0])
            except Exception:
                pred_min = 0.0

            temp_l.append([date_for_day, round(pred_avg, 2), round(pred_max, 2), round(pred_min, 2)])

        weekly_data = {
            'avg_val': [str(row[1]) for row in temp_l],
            'Max': [str(row[2]) for row in temp_l],
            'Min': [str(row[3]) for row in temp_l],
            'Date_val': [str(row[0]) for row in temp_l]
        }

        result1 = model.predict([val])
        classification = round(float(result1[0]), 2)

        return jsonify({
            'result': classification,
            'input3': station_uid,
            'result1': classification,
            'json_string': json.dumps(weekly_data)
        })

    except Exception as e:
        print("[ERROR] Exception in /predict route:")
        traceback.print_exc()
        if DEBUG_MODE:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }), 500
        else:
            return jsonify({"error": "Server error"}), 500

@app.route("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=True)
