import streamlit as st
import sqlite3
import re
import os
import requests
from textblob import TextBlob
from googletrans import Translator
import speech_recognition as sr
from thefuzz import process
import pandas as pd
import random

# --- Global Variables 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'travel_bot.db')

# Translator 
translator = Translator()

# Page Configuration
st.set_page_config(page_title="SL Travel Bot", page_icon="🌍", layout="centered")

# Sidebar Admin Section 
with st.sidebar:
    st.title("🎓 Project Information")
    st.info("AI Travel Assistant - UniManage Project")
    st.markdown("""
    **Features Integrated:**
    * 🎤 Voice-to-Text (Auto-stop)
    * 🧠 NLP & Fuzzy Matching
    * 😊 Sentiment Analysis
    * 🌍 Multilingual (SI/EN)
    * ☀️ Live Weather API
    """)
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.subheader("🔐 Admin Access")
    
    # Password input එක
    admin_password = st.text_input("Enter Admin Password", type="password")
    
    # Sidebar Admin Section
    if admin_password == "admin123":
        st.success("Access Granted!")
        
        if st.checkbox("📊 Show User Feedback"):
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("CREATE TABLE IF NOT EXISTS Feedback (Query TEXT, Response TEXT, Rating TEXT)")
                df = pd.read_sql_query("SELECT * FROM Feedback", conn)
                
                if not df.empty:
                    st.dataframe(df, use_container_width=True)

                    if st.button("🗑️ Clear All Feedback"):
                        conn.execute("DELETE FROM Feedback")
                        conn.commit()
                        st.success("All feedback records cleared!")
                        st.rerun() 
                else:
                    st.info("No feedback yet recorded.")
                conn.close()
            except Exception as e:
                st.error(f"Error: {e}")

        # 3. Teach the Bot & Auto-Delete from Unknowns
        st.divider()
        st.subheader("🎓 Teach the Bot")
        with st.expander("Add New Knowledge"):
            new_place = st.text_input("Place/Destination Name")
            new_desc = st.text_area("Description/Details")
            
            if st.button("Add to Database"):
                if new_place and new_desc:
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        conn.execute("INSERT INTO Destinations (PlaceName, Description) VALUES (?, ?)", (new_place, new_desc))
                        # Unknowns table
                        conn.execute("DELETE FROM Unknowns WHERE Query LIKE ?", ('%' + new_place + '%',))
                        conn.commit()
                        conn.close()
                        st.success(f"Successfully taught the bot about {new_place} and updated knowledge base!")
                        # st.rerun() 
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Please fill both fields.")
        # 2. Unknown Queries 
        if st.checkbox("🔍 Show Unknown Queries", key="chk_unknowns"):
            try:
                conn = sqlite3.connect(DB_PATH)
                df_unknown = pd.read_sql_query("SELECT * FROM Unknowns", conn)
                
                if not df_unknown.empty:
                    st.write("Bot හට තේරුම් නොගිය ප්‍රශ්න ලැයිස්තුව:")
                    st.dataframe(df_unknown, use_container_width=True)
                    if st.button("Clear All Unknowns"):
                        conn.execute("DELETE FROM Unknowns")
                        conn.commit()
                        st.rerun()
                else:
                    st.info("No unknown queries recorded yet.")
                conn.close()
            except Exception as e:
                st.error(f"Error loading unknowns: {e}")

# Database Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'travel_bot.db')

def listen_to_voice():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300  
    recognizer.pause_threshold = 0.5   
    recognizer.non_speaking_duration = 0.5 

    with sr.Microphone() as source:
        st.toast("🎤 Listening... Speak now.")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            # timeout=3: 
            # phrase_time_limit=5: 
            audio = recognizer.listen(source, timeout=3, phrase_time_limit=5)
            text = recognizer.recognize_google(audio)
            return text
        except sr.WaitTimeoutError:
            st.warning("No speech detected.")
            return None
        except Exception:
            return None

# Live Weather Function 
def get_weather(city_name):
    api_key = "268dacc65805bd4b48e9ad0c1b4e65bd" 
    base_url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name},LK&appid={api_key}&units=metric"
    try:
        response = requests.get(base_url).json()
        if response["cod"] == 200:
            temp = response["main"]["temp"]
            desc = response["weather"][0]["description"]
            return f" (Current Weather: {temp}°C, {desc})"
        return ""
    except:
        return ""

def get_bot_response(user_input):
    """
    The orchestrator for conversational synthesis. Computes emotional vectors, 
    normalizes multilingual records, maps user intent and executes fuzzy string alignment.
    """
    try:
        # Clear localized runtime states to prevent variable bleeding
        bot_answer = ""
        found = False
        
        # Step A: Affective Tone Analysis via TextBlob Polarity Measurement
        analysis = TextBlob(user_input)
        polarity = analysis.sentiment.polarity
        tone_prefix = ""
        if polarity < -0.2:
            tone_prefix = "I'm very sorry to hear that. I'll try my best to help. "
        elif polarity > 0.2:
            tone_prefix = "That's great! I'm happy to assist you. "

        # Step B1: Linguistic Localization Check and Translation Dispatch
        detected = translator.detect(user_input)
        lang = detected.lang
        
        # Safe translation execution wrapper
        try:
            search_query = translator.translate(user_input, dest='en').text if lang == 'si' else user_input
            search_query = search_query.lower()
        except:
            search_query = user_input.lower()

        # CRITICAL FIX
        direct_target = None

        # Step B2: English Alias & Phonetic Mapping (Handles voice-to-text spelling mistakes)
        english_aliases = {
            "candy": "Kandy",
            "kandie": "Kandy",
            "gale": "Galle",
            "colomboo": "Colombo",
            "nuwaraeliya": "Nuwara Eliya",
            "nuvara eliya": "Nuwara Eliya",
            "ellaa": "Ella"
        }
        for alias, official_name in english_aliases.items():
            if alias in search_query:
                direct_target = official_name
                break

        # Step B3: Direct Sinhala Keyword Pre-processing (Prevents Translation Hallucinations)
        raw_input_lower = user_input.lower()
        sinhala_mapping = {
            "නුවරඑළිය": "Nuwara Eliya",
            "මහනුවර": "Kandy",
            "නුවර": "Kandy",
            "ගාල්ල": "Galle",
            "කොළඹ": "Colombo",
            "ඇල්ල": "Ella",
            "සීගිරිය": "Sigiriya"
        }
        for sin_keyword, eng_keyword in sinhala_mapping.items():
            if sin_keyword in raw_input_lower:
                direct_target = eng_keyword
                break

        # Step C: Relational Transaction Initialization
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Sub-step C1: Phatic Communication & Conversational Small Talk Matrix
        smart_replies = {
            "hi": ["Hello! Welcome to SL Travel Assistant.", "Hi there! How can I help?", "Greetings!"],
            "hello": ["Hi there! Looking for some beautiful places?", "Hello! Ask me anything!"],
            "good morning": ["Good morning! Have a great day.", "Morning! How can I assist you?"],
            "thanks": ["You're welcome!", "Happy to help!", "Anytime!"],
            "thank you": ["You are very welcome!", "My pleasure!", "Glad I could help!"],
            "who are you": ["I am your AI Travel Assistant.", "I'm a bot specialized in SL tourism."],
            "ok": ["Great!", "Understood.", "Cool!", "Noted."],
            "yes": ["Understood. How can I assist you further?", "Okay, I'm listening."],
            "no": ["No problem! Feel free to ask whenever you're ready.", "Alright, let me know if you need help."]
        }
        words = search_query.split()
        for word in words:
            if word in smart_replies:
                bot_answer = random.choice(smart_replies[word])
                found = True
                break

        # Extract numeric scaling fields for dynamic tourist calculation routines
        numbers = re.findall(r'\d+', search_query)
        num_people = int(numbers[0]) if numbers else 1

        # Sub-step C2: Intent Structural Classification Engine
        
        # Bypass Fuzzy Logic if Direct Mapping or Alias is Triggered
        if not found and direct_target:
            is_weather_query = any(word in search_query for word in ["weather", "wether", "climate", "temp"]) or "කාලගුණය" in raw_input_lower
            
            if is_weather_query:
                weather_info = get_weather(direct_target)
                bot_answer = f"The current weather in {direct_target} is {weather_info}."
                found = True
            else:
                cursor.execute("SELECT Description FROM Destinations WHERE PlaceName = ?", (direct_target,))
                row = cursor.fetchone()
                if row:
                    desc = row[0]
                    weather_data = get_weather(direct_target)
                    bot_answer = f"{direct_target}: {desc}{weather_data}"
                    found = True

        # Fallback to Heuristic Levenshtein Distance Comparison if Direct Mapping Fails
        if not found:
            # Branch 1: Weather Intent via Fuzzy Matching
            is_weather_query = any(word in search_query for word in ["weather", "wether", "climate", "temp"]) or "කාලගුණය" in raw_input_lower
            if is_weather_query:
                cursor.execute("SELECT PlaceName FROM Destinations")
                places = [row[0] for row in cursor.fetchall()]
                if places:
                    best_match, score = process.extractOne(search_query, places)
                    if score > 85:
                        weather_info = get_weather(best_match)
                        bot_answer = f"The current weather in {best_match} is {weather_info}."
                        found = True

            # Branch 2: Commercial Tourism Packages Matching
            if not found and any(word in search_query for word in ["package", "price", "cost", "tour", "rate"]):
                cursor.execute("SELECT PackageName, Price, Duration FROM Packages")
                for pkg_name, price_str, duration in cursor.fetchall():
                    if pkg_name.split()[0].lower() in search_query:
                        price_digits = re.findall(r'\d+', price_str)
                        if price_digits:
                            total = int(price_digits[0]) * num_people
                            bot_answer = f"The {pkg_name} for {num_people} person(s) costs Rs. {total}. Duration: {duration}."
                            found = True
                            break

            # Branch 3: Standard Destination Lookup via Fuzzy Matching
            if not found:
                cursor.execute("SELECT PlaceName, Description FROM Destinations")
                dest_data = {row[0]: row[1] for row in cursor.fetchall()}
                places = list(dest_data.keys())
                if places:
                    best_match, score = process.extractOne(search_query, places)
                    if score > 85:
                        desc = dest_data[best_match]
                        weather_data = get_weather(best_match) 
                        bot_answer = f"{best_match}: {desc}{weather_data}"
                        found = True

        # Step D: Response Assembly and Failure Mitigation Auditing
        if found:
            full_reply = tone_prefix + bot_answer
        # CRITICAL FIX (Small Talk)
        elif not found and tone_prefix != "":
            full_reply = tone_prefix + "Is there a specific destination's weather or travel package you would like to know about?"
        else:
            cursor.execute("INSERT INTO Unknowns (Query) VALUES (?)", (user_input,))
            conn.commit()
            full_reply = "I'm sorry, I don't have detailed information about that yet. Our team will update this soon!"
        conn.close()

        # Step E: Response Translation Mapping for Linguistic Symmetry
        if lang == 'si':
            return translator.translate(full_reply, dest='si').text
        else:
            return full_reply
    except Exception as e:
        return f"⚠️ System Error: {str(e)}"

# UI Layout
st.title("🌍 Sri Lanka Travel Assistant")
st.markdown("##### *AI Smart Agent with Voice & Weather Integration*")
st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Combined Input Section 
user_query = None
cols = st.columns([1, 10]) 
with cols[0]:
    if st.button("🎤", help="Click and speak. Stops automatically."):
        user_query = listen_to_voice()

if prompt := st.chat_input("Ask anything (e.g. මහනුවර කාලගුණය කෝමද?)"):
    user_query = prompt

# Process Input
if user_query:
    st.session_state.last_query = user_query
    
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)
    
    with st.spinner("Analyzing..."):
        response = get_bot_response(user_query)
        st.session_state.last_response = response 
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    with st.chat_message("assistant"):
        st.markdown(response)

# Feedback Buttons 
if "last_query" in st.session_state:
    st.write("---")
    st.caption("Was this response helpful?")
    fb_col1, fb_col2 = st.columns([1, 8])
    q = st.session_state.last_query
    r = st.session_state.last_response

    with fb_col1:
        if st.button("👍", key="feedback_up"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("CREATE TABLE IF NOT EXISTS Feedback (Query TEXT, Response TEXT, Rating TEXT)")
            conn.execute("INSERT INTO Feedback (Query, Response, Rating) VALUES (?, ?, ?)", (q, r, "Positive"))
            conn.commit()
            conn.close()
            st.success("Feedback saved!")
            del st.session_state.last_query 
            
    with fb_col2:
        if st.button("👎", key="feedback_down"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("CREATE TABLE IF NOT EXISTS Feedback (Query TEXT, Response TEXT, Rating TEXT)")
            conn.execute("INSERT INTO Feedback (Query, Response, Rating) VALUES (?, ?, ?)", (q, r, "Negative"))
            conn.commit()
            conn.close()
            st.toast("Feedback recorded!")
            del st.session_state.last_query


# Listing 5.3: Asynchronous Web API Interfacing with Try-Except Architecture
import requests

def get_live_meteorological_data(city_name):
    api_key = "your_openweather_api_key_here"
    endpoint_url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric"
    
    try:
        # Distribute synchronous HTTP GET request with a strict timeout parameter
        response = requests.get(endpoint_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            weather_desc = data['weather'][0]['description']
            temp = data['main']['temp']
            return f"{weather_desc.capitalize()}, Temperature: {temp}°C"
        else:
            return "Weather telemetry updates are currently unavailable."
            
    except requests.exceptions.RequestException as error_flag:
        # Graceful degradation logic protecting primary runtime interface from network crashes
        print(f"Logging API Runtime Exception: {error_flag}")
        return "Weather service is temporarily unreachable due to network latency."
