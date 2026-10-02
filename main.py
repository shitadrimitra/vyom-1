import io
import re
import requests
import statistics
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from fastapi import FastAPI, Response, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.concurrency import run_in_threadpool
import edge_tts
from pydantic import BaseModel
from groq import Groq
from pymongo import MongoClient
import smtplib
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime
import httpx
from ddgs import DDGS

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ==========================================
# MONGODB SETUP (Replaced Supabase)
# ==========================================
MONGO_URI = "mongodb+srv://Admin:Rishi16ibl@weathergpt.jhopv4z.mongodb.net/?appName=WeatherGPT"
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client["weathergpt"]
    users_collection = db["users"]
    mongo_client.server_info() # Trigger connection check
    print("MongoDB Connected Successfully!")
except Exception as e:
    print(f"MongoDB connection warning: {e}")
    users_collection = None

client = Groq(api_key="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")
MISTRAL_API_KEY = "J7gMTCMfmjm8BrxAARA8SlkgTcbgHMo7"

def safe_ai_completion(messages, temp=0.2):
    """Attempts Groq first; falls back to Mistral AI instantly on failure."""
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="openai/gpt-oss-20b",
            temperature=temp
        )
        return response.choices[0].message.content
    except Exception as groq_err:
        print(f"Groq API Failed ({groq_err}). Switching to Mistral AI Backup...")
        try:
            headers = {
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "mistral-small-latest",
                "messages": messages,
                "temperature": temp
            }
            res = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload, timeout=12)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]
        except Exception as mistral_err:
            print(f"Mistral Fallback Failed: {mistral_err}")
            return "SYSTEM ERROR: Both primary (Groq) and backup (Mistral) AI engines are currently unreachable."

app = FastAPI(title="Vyom MoES Backend")

LANG_CODES = {
    "English": "en", "Hindi": "hi", "Bengali": "bn", "Telugu": "te",
    "Tamil": "ta", "Marathi": "mr", "Gujarati": "gu", "Kannada": "kn",
    "Malayalam": "ml", "Punjabi": "pa", "Odia": "or"
}

MODEL_MAPPING = {
    "best": "best_match", "ukmo": "ukmo_seamless", "ecmwf": "ecmwf_ifs025",
    "gfs": "gfs_seamless", "icon": "icon_seamless", "graphcast": "ecmwf_aifs025",  
    "earth2": "ecmwf_aifs025"
}

PERSONA_GUIDELINES = {
    "Farmer": "Focus on crop safety, pesticide spraying feasibility based on wind, and irrigation timing.",
    "Marine/Fisherman": "Focus on open-sea safety, offshore wind gusts, wave disturbance, and squalls.",
    "Aviation": "Focus on flight briefing: cloud cover ceilings, turbulence risks, wind vectors, and altimeter pressure.",
    "Disaster Management": "Focus on early alerts: cyclone severity, heavy downpour flood risks, and evacuation notices.",
    "Smart City Planner": "Focus on urban heat island effects, municipal storm drainage pressure, and outdoor labor safety.",
    "Adventurer": "Focus on extreme outdoor safety: hiking conditions, terrain slipperiness, visibility, UV index, and altitude/storm risks.",
    "General Citizen": "Focus on daily commute comfort, clothing requirements, umbrella necessity, and transit plans."
}

# ==========================================
# USER SYNC ENDPOINTS (MongoDB)
# ==========================================
class UserProfileSync(BaseModel):
    clerk_id: str
    email: str = ""
    phone: str = ""
    language: str = "English"
    persona: str = "General Citizen"
    health_profile: str = "None"
    lat: float = None
    lon: float = None

@app.post("/api/user/sync")
def sync_user_profile(payload: UserProfileSync):
    if users_collection is None:
        return {"status": "error", "message": "MongoDB not initialized"}
    try:
        update_data = payload.dict(exclude_none=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        users_collection.update_one(
            {"clerk_id": payload.clerk_id},
            {"$set": update_data},
            upsert=True
        )
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/user/profile")
def get_user_profile(clerk_id: str):
    if users_collection is None:
        return {"status": "error", "message": "MongoDB not initialized"}
    try:
        user = users_collection.find_one({"clerk_id": clerk_id}, {"_id": 0})
        if user:
            return {"status": "success", "profile": user}
        return {"status": "not_found", "profile": None}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class AlertConfigUpdate(BaseModel):
    clerk_id: str
    alert_email: str = ""
    alert_lat: float = None
    alert_lon: float = None
    alert_rain_threshold: float = 50.0
    alert_heat_threshold: float = 42.0
    alert_wind_threshold: float = 60.0
    alert_enabled: bool = False

@app.post("/api/alerts/config")
def update_alert_config(payload: AlertConfigUpdate, background_tasks: BackgroundTasks):
    if users_collection is None:
        return {"status": "error", "message": "MongoDB not initialized"}
    try:
        users_collection.update_one(
            {"clerk_id": payload.clerk_id},
            {"$set": payload.dict()},
            upsert=True
        )
        if payload.alert_enabled:
            background_tasks.add_task(scan_and_alert_users)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================
# AUTOMATED DISASTER ALERT ENGINE
# ==========================================
def send_email_alert(to_email, subject, body):
    if not to_email: return
    try:
        print(f"\n[EMAIL DISPATCHED TO {to_email}]\nSUBJECT: {subject.encode('ascii', 'ignore').decode()}\nBODY: {body.encode('ascii', 'ignore').decode()}\n")
    except Exception:
        pass
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = "samadrito.one@gmail.com"
        msg['To'] = to_email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login("samadrito.one@gmail.com", "jzjo orhh pdjk msee")
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

def send_sms_alert(to_phone, body):
    if not to_phone: return
    print(f"\n[SMS DISPATCHED TO {to_phone}]\nBODY: {body}\n")
    # For production: Add Twilio or Fast2SMS API integration here
    # twilio_client.messages.create(body=body, from_='+1234567890', to=to_phone)

def scan_and_alert_users():
    """Background task that scans all users for upcoming natural calamities using forecasting and web search."""
    import time
    if users_collection is None: return
    
    users = users_collection.find({"alert_enabled": True, "alert_lat": {"$ne": None}, "alert_lon": {"$ne": None}})
    
    for user in users:
        lat, lon = user.get("alert_lat"), user.get("alert_lon")
        email = user.get("alert_email") or user.get("email")
        phone = user.get("phone")
        lang, persona = user.get("language", "English"), user.get("persona", "General Citizen")
        last_alert_time = user.get("last_alert_time", 0)
        
        # Cooldown check: 12 hours (43200 seconds)
        if time.time() - last_alert_time < 43200:
            continue
            
        rain_thresh = float(user.get("alert_rain_threshold", 50.0))
        heat_thresh = float(user.get("alert_heat_threshold", 42.0))
        wind_thresh = float(user.get("alert_wind_threshold", 60.0))
        
        calamity = None
        calamity_details = ""
        
        # 1. Forecast-based Hazard Detection (next 72h)
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation,wind_speed_10m,weather_code&forecast_days=3&timezone=auto"
        try:
            import requests
            res = requests.get(weather_url, timeout=5).json()
            hourly = res.get("hourly", {})
            temps = hourly.get("temperature_2m", [])
            precips = hourly.get("precipitation", [])
            winds = hourly.get("wind_speed_10m", [])
            codes = hourly.get("weather_code", [])
            times = hourly.get("time", [])
            
            for i in range(len(temps)):
                t = temps[i]
                p = precips[i]
                w = winds[i]
                c = codes[i]
                time_str = times[i]
                
                # Check for sustained heat (3 consecutive hours)
                if i >= 2 and t and temps[i-1] and temps[i-2] and t >= heat_thresh and temps[i-1] >= heat_thresh and temps[i-2] >= heat_thresh:
                    calamity = f"Extreme Heat expected around {time_str}"
                    break
                # Wind check
                elif w and w >= wind_thresh:
                    calamity = f"Destructive Winds expected around {time_str}"
                    break
                # Rolling rain sum (3 hours)
                elif i >= 2 and p is not None and sum([precips[i] or 0, precips[i-1] or 0, precips[i-2] or 0]) >= rain_thresh:
                    calamity = f"Heavy Rainfall/Flood Risk expected around {time_str}"
                    break
                # Thunderstorms/Blizzard
                elif c in [95, 96, 99]:
                    calamity = f"Severe Thunderstorm expected around {time_str}"
                    break
                elif c in [75, 77, 86] and p and p > 15:
                    calamity = f"Heavy Blizzard Risk expected around {time_str}"
                    break
        except Exception as e:
            print(f"Forecast scan failed for user {email}: {e}")

        # 2. Web Search for Impending Calamities (Cyclone, Flood)
        if not calamity:
            try:
                # Get city name
                rev_url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=10"
                rev_res = requests.get(rev_url, headers={'User-Agent': 'Vyom'}, timeout=5).json()
                address = rev_res.get("address", {})
                city = address.get("city") or address.get("state") or address.get("country", "")
                
                if city:
                    search_query = f"{city} upcoming natural calamity cyclone hurricane flood earthquake warning next 48 hours"
                    from ddgs import DDGS
                    results = DDGS().text(search_query, max_results=3)
                    if results:
                        combined_text = " ".join([r.get('body', '') for r in results])
                        ai_check_prompt = f"Analyze these search results: '{combined_text}'. Is there a confirmed upcoming natural calamity (cyclone, flood, etc.) for {city} in the next 48 hours? Reply with strictly 'YES: [calamity name]' or 'NO'."
                        ai_check = safe_ai_completion([{"role": "user", "content": ai_check_prompt}], temp=0.1)
                        if "YES:" in ai_check.upper():
                            calamity = ai_check.split(":", 1)[1].strip()
                            calamity_details = combined_text
            except Exception as e:
                print(f"Web search scan failed: {e}")

        # 3. USGS Earthquake Detection
        if not calamity:
            try:
                usgs_url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
                eq_data = requests.get(usgs_url, timeout=5).json()
                for feature in eq_data.get("features", []):
                    coords = feature["geometry"]["coordinates"]
                    eq_lon, eq_lat = coords[0], coords[1]
                    mag = feature["properties"]["mag"]
                    tsunami = feature["properties"]["tsunami"]
                    
                    dist_km = (((lat - eq_lat)**2 + (lon - eq_lon)**2)**0.5) * 111
                    
                    if dist_km < 400 and tsunami == 1:
                        calamity = f"Tsunami Warning (Triggered by Mag {mag} Earthquake)"
                        break
                    elif dist_km < 150 and mag >= 5.0:
                        calamity = f"Strong Earthquake Alert (Mag {mag} nearby)"
                        break
            except Exception as eq_e:
                print(f"Earthquake scan failed: {eq_e}")

        if calamity:
            prompt = f"""
            URGENT: A {calamity} is predicted near the user's location (Lat: {lat}, Lon: {lon}).
            Additional Context: {calamity_details}
            
            Write a detailed, life-saving emergency email for a {persona} in {lang}.
            Include:
            1. Details of the disaster and expected time to impact.
            2. What to do immediately to prepare.
            3. Suggest how far they need to move or directly suggest a safe place/action.
            Format with clear headings. Do not include any pleasantries. Be authoritative.
            """
            alert_message = safe_ai_completion([{"role": "user", "content": prompt}], temp=0.2)
            
            subject = f"⚠️ VYOM PREDICTIVE ALERT: {calamity.upper()}"
            send_email_alert(email, subject, alert_message)
            send_sms_alert(phone, f"VYOM ALERT: {calamity}. Check your email immediately for evacuation and safety instructions.")
            
            # Update cooldown
            users_collection.update_one({"_id": user["_id"]}, {"$set": {"last_alert_time": time.time(), "last_alert_calamity": calamity}})


@app.post("/api/alerts/trigger")
def trigger_alert_scan(background_tasks: BackgroundTasks):
    """Admin endpoint to manually trigger a sweep of all users for calamities."""
    background_tasks.add_task(scan_and_alert_users)
    return {"status": "success", "message": "Disaster alert scan initiated in the background."}

# ==========================================
# STANDARD ROUTES
# ==========================================
@app.get("/")
def home():
    return FileResponse("index.html", headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})

@app.get("/news")
def get_weather_news(response: Response):
    try:
        rss_url = f'https://news.google.com/rss/search?q=extreme+weather+OR+climate+change+OR+flood+OR+cyclone+OR+hurricane+OR+wildfire+OR+heatwave+when:1d&hl=en-US&gl=US&ceid=US:en&_={int(time.time())}'
        res = requests.get(rss_url, timeout=5)
        root = ET.fromstring(res.content)
        items = root.findall('.//item')
        
        parsed_items = []
        for item in items:
            title = item.find('title').text
            link = item.find('link').text
            pub_date_str = item.find('pubDate').text if item.find('pubDate') is not None else ''
            
            try:
                dt = parsedate_to_datetime(pub_date_str)
                if dt.tzinfo is None:
                    from datetime import timezone
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                from datetime import timezone
                dt = datetime.min.replace(tzinfo=timezone.utc)
                
            clean_title = title.rsplit(" - ", 1)[0] if " - " in title else title
            parsed_items.append({
                "title": clean_title, 
                "link": link,
                "dt": dt
            })
            
        parsed_items.sort(key=lambda x: x["dt"], reverse=True)
        news_items = [{"title": x["title"], "link": x["link"]} for x in parsed_items[:15]]
        
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return {"news": news_items}
    except Exception as e:
        return {"news": [{"title": "Live global news currently unavailable.", "link": "#"}]}

def fallback_web_search(original_query: str) -> str:
    try:
        search_query = f"{original_query} current weather or climate"
        results = DDGS().text(search_query, max_results=3)
        if not results:
            return f"I couldn't find a direct answer. Please refine your query."

        compiled_text = f"**Based on real-time data analysis:**\n\n"
        for i, r in enumerate(results):
            compiled_text += f"- {r.get('body', '')}\n"

        # We also pass it to the AI to summarize if possible
        ai_prompt = f"The user asked about: '{original_query}'. Here is real-time data: {compiled_text}. Synthesize a helpful, conversational, and direct meteorological response. DO NOT provide cultural, political, or geographic trivia. ONLY discuss weather, climate, and meteorological data (including historical climate if asked). DO NOT mention that you searched the web or used real-time data."
        ai_summary = safe_ai_completion([{"role": "user", "content": ai_prompt}], temp=0.3)

        if ai_summary and not ai_summary.startswith("SYSTEM ERROR"):
            return ai_summary

        return compiled_text
    except Exception as e:
        return f"I couldn't process this complex query: {str(e)}"

@app.get("/weather")
def get_live_weather(
    query: str = "", lat: float = None, lon: float = None,
    language: str = "English", persona: str = "General Citizen",
    health_profile: str = "None", model: str = "best"
):
    try:
        headers = {'User-Agent': 'MoES-WeatherGPT/1.0'}
        city_name = "the selected location"

        if lat is not None and lon is not None:
            try:
                headers['Accept-Language'] = 'en-US,en;q=0.9'
                rev_url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=18"
                rev_res = requests.get(rev_url, headers=headers, timeout=5).json()
                feat_name = rev_res.get("name")
                addr = rev_res.get("address", {})
                if feat_name:
                    city_name = feat_name
                else:
                    city_name = (
                        addr.get("natural") or addr.get("peak") or addr.get("waterway") or
                        addr.get("tourism") or addr.get("city") or addr.get("town") or 
                        addr.get("village") or addr.get("county") or "the selected location"
                    )
            except Exception:
                city_name = "the selected location"
        else:
            if not query:
                return {"weather_report": "Please enter a location.", "weather_code": 0, "telemetry": {}}

            extraction_prompt = f"Analyze the following weather query: '{query}'. If this is a simple request for CURRENT weather at a SINGLE, specific location, return ONLY a highly specific, fully-qualified GIS search string formatted as 'Location, State/Region, Country'. If the query involves a route, multiple locations, historical weather, past climate, future climate change, a general meteorological question, or is ambiguous, return exactly the word 'COMPLEX'. If no location is found at all, return 'UNKNOWN'. Reply with nothing but the qualified location string, 'COMPLEX', or 'UNKNOWN'."
            
            raw_location = safe_ai_completion([{"role": "user", "content": extraction_prompt}], temp=0.1)
            extracted_location = raw_location.strip().strip('"').strip("'")

            if extracted_location.upper() in ["UNKNOWN", "COMPLEX"] or not extracted_location:
                fallback_response = fallback_web_search(query)
                return {"weather_report": fallback_response, "weather_code": 0, "telemetry": {}}

            geo_url = "https://nominatim.openstreetmap.org/search"
            geo_params = {"q": extracted_location, "format": "json", "limit": 1}
            geo_res = requests.get(geo_url, headers=headers, params=geo_params).json()

            if not geo_res:
                simplified_query = extracted_location.split(',')[0].strip()
                geo_params = {"q": simplified_query, "format": "json", "limit": 1}
                geo_res = requests.get(geo_url, headers=headers, params=geo_params).json()

            if not geo_res:
                fallback_response = fallback_web_search(query)
                return {"weather_report": fallback_response, "weather_code": 0, "telemetry": {}}

            lat = float(geo_res[0]["lat"])
            lon = float(geo_res[0]["lon"])
            city_name = geo_res[0].get("name", extracted_location)

        active_health_profile = health_profile if persona == "General Citizen" else "None"
        selected_model_param = MODEL_MAPPING.get(model.lower(), "best_match")

        consensus_models = ["ecmwf_ifs025", "gfs_seamless", "ukmo_seamless", "icon_seamless"]
        model_temps = []
        for m_name in consensus_models:
            m_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m&models={m_name}"
            try:
                m_res = requests.get(m_url, timeout=3).json()
                t_val = m_res.get("current", {}).get("temperature_2m")
                if t_val is not None: model_temps.append(float(t_val))
            except Exception: pass

        temp_spread = round(statistics.stdev(model_temps), 2) if len(model_temps) > 1 else 0.0

        current_year = datetime.now().year
        past_start = f"{current_year - 10}-01-01"
        past_end = f"{current_year - 1}-12-31"
        climate_url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={past_start}&end_date={past_end}&daily=temperature_2m_mean"
        
        anomaly_index = 0.0
        try:
            cl_res = requests.get(climate_url, timeout=4).json()
            daily_temps = cl_res.get("daily", {}).get("temperature_2m_mean", [])
            valid_historical = [t for t in daily_temps if t is not None]
            if valid_historical:
                historical_avg = statistics.mean(valid_historical)
                current_temp_sample = model_temps[0] if model_temps else 20.0
                anomaly_index = round(current_temp_sample - historical_avg, 1)
        except Exception:
            anomaly_index = 0.0

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,precipitation,weather_code"
            f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code"
            f"&forecast_days=3&timezone=auto&models={selected_model_param}"
        )
        
        weather_res = requests.get(weather_url)
        
        if weather_res.status_code != 200 or not weather_res.json().get("current", {}).get("temperature_2m"):
            fallback_url = weather_url.replace(selected_model_param, "best_match")
            weather_res = requests.get(fallback_url)

        if weather_res.status_code != 200:
            return {"weather_report": "Sensors unreachable.", "weather_code": 0, "telemetry": {}, "location_name": city_name}
             
        data = weather_res.json()
        current_data = data.get("current")
        hourly_data = data.get("hourly", {})
        
        if not current_data:
            return {"weather_report": "No verified data available.", "weather_code": 0, "telemetry": {}, "location_name": city_name}

        elevation = data.get("elevation", 0)
        raw_pressure = current_data.get("surface_pressure", 1013.25)
        effective_oxygen = round(20.9 * (float(raw_pressure) / 1013.25), 1)
        wind_speed = float(current_data.get("wind_speed_10m", 0.0))
        precipitation = float(current_data.get("precipitation", 0.0))
        temperature = float(current_data.get("temperature_2m", 0.0))

        infra_risk = "Low"
        if wind_speed > 50 or precipitation > 20: infra_risk = "Critical"
        elif wind_speed > 30 or precipitation > 10: infra_risk = "High"

        travel_risk = "Low"
        if precipitation > 15 or temperature < -10 or elevation > 4000: travel_risk = "Critical"
        elif precipitation > 5 or temperature < 0: travel_risk = "High"

        health_risk = "Low"
        if elevation > 3500 or temperature < -15: health_risk = "Critical"
        elif elevation > 2000 or temperature > 40 or temperature < -5: health_risk = "High"
        
        current_data.update({
            "elevation": elevation, "effective_oxygen": effective_oxygen, 
            "model_spread": temp_spread, "climate_anomaly": anomaly_index,
            "risk_matrix": {"infrastructure": infra_risk, "travel": travel_risk, "health": health_risk},
            "hourly": hourly_data
        })

        active_persona = persona
        active_guideline = PERSONA_GUIDELINES.get(persona, "General overview.")
        if elevation > 3500:
            active_persona = "Expert Alpine Mountaineer"
            active_guideline = "CRITICAL: Extreme high-altitude. Focus on frostbite, hypothermia, hypoxia."

        prompt = f"""
        You are WeatherGPT, an authoritative meteorological decision AI for India's Ministry of Earth Sciences.
        Natural Language Query: "{query}"
        Detected Location: {city_name} (Coordinates: {lat}, {lon}). Elevation: {elevation} meters.
        Model Spread: ±{temp_spread}°C. Climate Baseline Anomaly: {anomaly_index}°C.
        Current Telemetry: {current_data}.
        Target Stakeholder: {active_persona} (Guideline: {active_guideline}).
        Biometric Profile: {active_health_profile}.

        MANDATORY RULES:
        1. STRICT LANGUAGE ENFORCEMENT: Answer in {language}.
        2. PHYSICS OVERRIDE: If temp < 0°C, interpret precipitation as snow/ice.
        3. SEVERE WEATHER ALERT: If severe, start with [ALERT: <Urgent warning>]
        4. Direct Answer: Mention {city_name} in sentence 1.
        5. WEATHER ONLY: NEVER provide history, political data, or general geographic facts about the place. ONLY discuss the current and forecasted weather conditions, telemetry, and actionable advice.
        """

        ai_response_text = safe_ai_completion([{"role": "user", "content": prompt}], temp=0.2)

        # Fallback if AI response is empty or an error message
        if not ai_response_text or ai_response_text.strip() == "" or ai_response_text.startswith("SYSTEM ERROR"):
            # First try web search fallback for complex queries
            web_fallback = fallback_web_search(query)
            if web_fallback and not web_fallback.startswith("I searched the web") and not web_fallback.startswith("I couldn't process"):
                ai_response_text = web_fallback + f"\n\n*Live Telemetry Context: {city_name} is currently at {temperature}°C.*"
            else:
                wc = current_data.get('weather_code', 0)
                conditions_map = {
                    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                    45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
                    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                    71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
                    77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
                    82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
                    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
                }
                condition = conditions_map.get(wc, "Variable conditions")
                ai_response_text = (
                    f"**Current Weather in {city_name}:**\n\n"
                    f"**Conditions:** {condition}\n"
                    f"**Temperature:** {temperature}°C\n"
                    f"**Wind Speed:** {wind_speed} km/h\n"
                    f"**Humidity:** {current_data.get('relative_humidity_2m', 'N/A')}%\n"
                    f"**Pressure:** {raw_pressure} hPa\n"
                    f"**Elevation:** {elevation}m\n\n"
                    f"*AI analysis is temporarily unavailable. The telemetry data above reflects live conditions.*"
                )

        alert_text = None
        if "[ALERT:" in ai_response_text:
            try:
                alert_text = ai_response_text.split("[ALERT:")[1].split("]")[0].strip()
                ai_response_text = ai_response_text.replace(f"[ALERT: {alert_text}]", "").replace(f"[ALERT:{alert_text}]", "").strip()
            except: pass

        return {
            "weather_report": ai_response_text,
            "weather_code": current_data.get("weather_code", 0),
            "telemetry": current_data,
            "location_name": city_name,
            "alert": alert_text,
            "lat": lat, # Return coords so frontend can sync them to Mongo
            "lon": lon
        }
    except Exception as e:
        return {"weather_report": f"Error processing telemetry: {str(e)}", "weather_code": 0, "telemetry": {}}

@app.get("/pdf-brief")
def generate_executive_pdf(
    location: str = "Unknown", temp: float = 0.0, humidity: float = 0.0, wind: float = 0.0,
    pressure: float = 1013.0, elevation: float = 0.0, oxygen: float = 20.9, spread: float = 0.0,
    anomaly: float = 0.0, infra_risk: str = "Low", travel_risk: str = "Low", health_risk: str = "Low",
    model: str = "Best", persona: str = "General Citizen", report: str = "No report generated."
):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()

    # Try to load Nirmala UI font for Indian languages support
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    import os
    
    font_regular = 'Helvetica'
    font_bold = 'Helvetica-Bold'
    
    try:
        if os.path.exists('C:/Windows/Fonts/Nirmala.ttc'):
            pdfmetrics.registerFont(TTFont('Nirmala', 'C:/Windows/Fonts/Nirmala.ttc', subfontIndex=0))
            pdfmetrics.registerFont(TTFont('Nirmala-Bold', 'C:/Windows/Fonts/Nirmala.ttc', subfontIndex=1))
            registerFontFamily('Nirmala', normal='Nirmala', bold='Nirmala-Bold', italic='Nirmala', boldItalic='Nirmala-Bold')
            font_regular = 'Nirmala'
            font_bold = 'Nirmala-Bold'
    except Exception as e:
        print("Font registration error:", e)

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=15, textColor=colors.HexColor('#0f172a'), spaceAfter=4, fontName=font_bold)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=8.5, textColor=colors.HexColor('#64748b'), spaceAfter=12, fontName=font_regular)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=10.5, textColor=colors.HexColor('#0d9488'), spaceBefore=10, spaceAfter=4, fontName=font_bold)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=8.5, textColor=colors.HexColor('#334155'), spaceAfter=6, leading=12, fontName=font_regular)

    story.append(Paragraph("MINISTRY OF EARTH SCIENCES (MoES) — OFFICIAL METEOROLOGICAL BRIEF", title_style))
    story.append(Paragraph(f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Classification: RESTRICTED", subtitle_style))
    story.append(Spacer(1, 2))

    story.append(Paragraph("1. TARGET LOCATION & TOPOGRAPHY", heading_style))
    loc_data = [[Paragraph("<b>Location:</b>", body_style), Paragraph(location, body_style), Paragraph("<b>Elevation:</b>", body_style), Paragraph(f"{elevation} m", body_style)]]
    t1 = Table(loc_data, colWidths=[90, 180, 90, 180])
    t1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')), ('PADDING', (0,0), (-1,-1), 5), ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1'))]))
    story.append(t1)
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. ATMOSPHERIC TELEMETRY", heading_style))
    tel_data = [
        [Paragraph("<b>Temperature:</b>", body_style), Paragraph(f"{temp}°C", body_style), Paragraph("<b>Infrastructure Risk:</b>", body_style), Paragraph(infra_risk, body_style)],
        [Paragraph("<b>Wind Speed:</b>", body_style), Paragraph(f"{wind} km/h", body_style), Paragraph("<b>Climate Anomaly:</b>", body_style), Paragraph(f"{anomaly}°C", body_style)]
    ]
    t2 = Table(tel_data, colWidths=[90, 180, 90, 180])
    t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')), ('PADDING', (0,0), (-1,-1), 5), ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1'))]))
    story.append(t2)
    story.append(Spacer(1, 6))

    story.append(Paragraph(f"3. OFFICIAL STAKEHOLDER ADVISORY", heading_style))
    
    # Clean markdown and problematic characters
    clean_report = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', report) # Bold
    clean_report = re.sub(r'\*(.*?)\*', r'<i>\1</i>', clean_report) # Italic
    clean_report = clean_report.replace('•', '-') # Fix black dots from bullets
    clean_report = re.sub(r'[#`~]', '', clean_report) # Remove leftover markdown
    clean_report = clean_report.replace('\n', '<br/>')
    
    story.append(Paragraph(clean_report, body_style))

    doc.build(story)
    pdf_buffer.seek(0)
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=MoES_Briefing_{location.replace(' ', '_')}.pdf"})

VOICE_MAPPING = {
    "English": "en-IN-NeerjaExpressiveNeural", 
    "Hindi": "hi-IN-SwaraNeural",
    "Bengali": "bn-IN-TanishaaNeural",
    "Telugu": "te-IN-ShrutiNeural",
    "Tamil": "ta-IN-PallaviNeural",
    "Marathi": "mr-IN-AarohiNeural",
    "Gujarati": "gu-IN-DhwaniNeural",
    "Kannada": "kn-IN-SapnaNeural",
    "Malayalam": "ml-IN-SobhanaNeural",
    "Punjabi": "hi-IN-SwaraNeural", 
    "Odia": "hi-IN-SwaraNeural"     
}

@app.get("/speak")
async def text_to_speech(text: str, language: str = "English"):
    try:
        # Prompt AI to summarize into a short, natural voice response in the correct language
        summary_prompt = f"Summarize the following weather report into 2-3 natural spoken sentences for a voice assistant. Keep the summary and the very important parts only. You MUST respond strictly in the {language} language. Do NOT include markdown, lists, or symbols. Text: {text}"
        
        # Run synchronous Groq/Mistral AI function in threadpool
        summary_text = await run_in_threadpool(
            safe_ai_completion, 
            [{"role": "user", "content": summary_prompt}], 
            0.3
        )
        
        if not summary_text or summary_text.startswith("SYSTEM ERROR"):
            summary_text = text # fallback
            
        clean_text = re.sub(r'[*#_`~>-]', '', summary_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        voice = VOICE_MAPPING.get(language, "en-IN-NeerjaExpressiveNeural")
        communicate = edge_tts.Communicate(clean_text, voice)
        
        async def audio_stream():
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
                    
        return StreamingResponse(audio_stream(), media_type="audio/mpeg")
    except Exception as e:
        print(f"TTS Error: {e}")
        return {"error": "Audio synthesis failed."}

import asyncio

@app.on_event("startup")
async def start_periodic_scan():
    async def periodic_task():
        while True:
            await asyncio.sleep(600)  # wait 10 mins (600 seconds)
            try:
                await asyncio.to_thread(scan_and_alert_users)
            except Exception as e:
                print(f"Periodic scan error: {e}")
                
    asyncio.create_task(periodic_task())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)