import requests
import os
from flask import Flask, render_template, request, flash, redirect, url_for, session
from dotenv import load_dotenv
from datetime import timedelta
import pandas as pd
import seaborn as sns
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io, base64
import openmeteo_requests
import requests_cache
from retry_requests import retry
import json


app = Flask(__name__)
app.secret_key = "omg"
app.permanent_session_lifetime = timedelta(days=300)
# Assigning API keys from environment variables.
secret_api_key = os.getenv("API_KEY")
weatherapi_key = os.getenv("WEATHERAPI_KEY")
# Initializing moon phases.
moon_phases_all = ["New Moon","Waxing Crescent","First Quarter","Waxing Gibbous","Full Moon","Waning Gibbous","Last Quarter","Waning Crescent"]
response_json = {}
response_json_2 = {}
forecast_response_json_1 = {}
marine_response_json_1 = {}
sports_response_json_1 = {}
pollen_response = {}
hourly_var = ""
hourly_pollen_json = {}
graph_created = ""

# The home page, and the weathercast web page opens the index() function.
@app.route('/')
@app.route('/',methods=["POST","GET"])
@app.route('/weathercast',methods=["POST","GET"])
def index():
    session["clicked_search_button"] = False
    if "temp_unit" not in session:
        session["temp_unit"] = True  # True->Celsius, False->Fahrenheit
        session["temp_unit_value"] = "℃"
    if "cities_arr" not in session:
        session["cities_arr"] = ""
    if "fav_locations" not in session:
        session["fav_locations"] = {}
    if request.method=="POST":
        session.permanent = True
        # When the search button is clicked.
        if "search_button" in request.form:
            # Set the boolean value of 'clicked_search_button' in the session as True.
            session["clicked_search_button"] = True
            # Get the input string entered in the text field.
            location_input = request.form["location_entered"]
            # Check if the input string is empty or filled with spaces.
            if location_input!="" and location_input.isspace()==False:
                # Geocoding API for fetching all the list of cities having the same name as searched in the text field by user.
                url_for_cities_list = f"https://api.weatherapi.com/v1/search.json?key={weatherapi_key}&q={location_input}"
                cities_list_response = requests.get(url_for_cities_list)
                status_received = cities_list_response.status_code
                # If the status code of the Geocoding API is 200, it means active endpoint.
                if status_received==200:
                    # Change the response received to JSON format.
                    cities_list_response_json = cities_list_response.json()
                    total_cities = len(cities_list_response_json)
                    total_cities_fetched = total_cities
                    cities_arr = []
                    countries_arr = []
                    cities_lat_arr = []
                    cities_lon_arr = []
                    for curr_item in cities_list_response_json:
                        cities_arr.append(curr_item["name"]+", "+curr_item["region"])
                        countries_arr.append(curr_item["country"])
                        cities_lat_arr.append(curr_item["lat"])
                        cities_lon_arr.append(curr_item["lon"])
                    session["cities_arr"] = cities_arr
                    session["countries_arr"] = countries_arr
                    session["cities_lat_arr"] = cities_lat_arr
                    session["cities_lon_arr"] = cities_lon_arr
                    session["total_cities_fetched"] = total_cities_fetched
                else:
                    # If the status code is not 200, the Geocoding API's endpoint is not active. Show a flash message.
                    flash("404 Error","info")
            else:
                # When the user entered input string is empty or filled with spaces, show a flash message.
                flash("Invalid location. Please enter a correct city or town!")
                return render_template("weathercast.html",cities_arr=session.get("cities_arr"))
        # When any button is clicked.
        if True:
            clicked_btn = ""
            ptr_index = ""
            if "c_f_temp_unit" in request.form:
                session["clicked_search_button"] = False
                change_temp_unit()
                if session.get("cities_arr")!="":
                    ptr_index = session.get("last_clicked_ptr")
                else:
                    return redirect("weathercast.html")
            elif session.get("clicked_search_button")==True: #"search_button" in request.form:
                ptr_index = 0
                session["last_clicked_ptr"] = 0
            elif "star_btn" in request.form:
                ptr_index = session.get("last_clicked_ptr")
                if ptr_index==None:
                    flash("Unavailable location to star as favorites. Please search a location and click on star to mark as favorite!")
                    return render_template("weathercast.html")
                add_or_remove_star()
            else:
                session["clicked_search_button"] = False
                clicked_btn = next((k for k in request.form if k.startswith("btn")), None)
                ptr_index = int(clicked_btn[3:])
            cities_arr = session.get("cities_arr")
            cities_lat_arr = session.get("cities_lat_arr")
            cities_lon_arr = session.get("cities_lon_arr")
            total_cities_fetched = session.get("total_cities_fetched")
            # Current weather details fetched from OpenWeatherMap API
            live_weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={cities_lat_arr[ptr_index]}&lon={cities_lon_arr[ptr_index]}&appid={secret_api_key}&units=metric"
            response = requests.get(live_weather_url)
            status=response.status_code
            # Current weather details fetching from WeatherAPI's url
            live_weather_url_2 = f"https://api.weatherapi.com/v1/current.json?key={weatherapi_key}&q={cities_lat_arr[ptr_index]},{cities_lon_arr[ptr_index]}&aqi=yes"
            response_2 = requests.get(live_weather_url_2)
            status_2 = response_2.status_code
            # 3 days weather forecast fetched from WeatherAPI's Forecast API.
            forecast_api_url_1 = f"https://api.weatherapi.com/v1/forecast.json?key={weatherapi_key}&q={cities_lat_arr[ptr_index]},{cities_lon_arr[ptr_index]}&days=14&aqi=no&alerts=yes"
            forecast_response_1 = requests.get(forecast_api_url_1)
            forecast_status_1 = forecast_response_1.status_code
            # Current day's marine details fetched from WeatherAPI's Marine API.
            marine_api_url = f"https://api.weatherapi.com/v1/marine.json?key={weatherapi_key}&q={cities_lat_arr[ptr_index]},{cities_lon_arr[ptr_index]}&days=1"
            marine_response_1 = requests.get(marine_api_url)
            marine_status_1 = marine_response_1.status_code
            # Upcoming sports matches for cricket, football, and golf fetched from WeatherAPI's Sports API.
            sports_api_url = f"https://api.weatherapi.com/v1/sports.json?key={weatherapi_key}&q={cities_lat_arr[ptr_index]},{cities_lon_arr[ptr_index]}"
            sports_response_1 = requests.get(sports_api_url)
            sports_status_1 = sports_response_1.status_code
            # Openmetoo API for Pollen forecast details for 3 days
            cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
            retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
            openmeteo = openmeteo_requests.Client(session=retry_session)
            url = "https://air-quality-api.open-meteo.com/v1/air-quality"
            params = {
                "latitude": cities_lat_arr[ptr_index],
                "longitude": {cities_lon_arr[ptr_index]},
                "hourly": ["alder_pollen", "birch_pollen", "grass_pollen", "mugwort_pollen", "olive_pollen",
                           "ragweed_pollen"],
                "forecast_days": 3,
            }
            responses = openmeteo.weather_api(url, params=params)
            pollen_response = responses[0]
            hourly = pollen_response.Hourly()
            # Checking if all the API endpoints are active in status. Status code 200 means active.
            if status==200 and status_2==200 and forecast_status_1==200 and marine_status_1==200 and sports_status_1==200:
                global response_json, response_json_2, forecast_response_json_1, marine_response_json_1, sports_response_json_1, hourly_pollen_json, hourly_var
                response_json = response.json()
                response_json_2 = response_2.json()
                forecast_response_json_1 = forecast_response_1.json()
                marine_response_json_1 = marine_response_1.json()
                sports_response_json_1 = sports_response_1.json()
                hourly_var = hourly
                current_temperature = ""
                feels_like_temperature = ""
                min_temp = ""
                max_temp = ""
                dew_point = ""
                if session.get("temp_unit")==True:
                    current_temperature = response_json_2["current"]["temp_c"]
                    feels_like_temperature = response_json_2["current"]["feelslike_c"]
                    min_temp = forecast_response_json_1["forecast"]["forecastday"][0]["day"]["mintemp_c"]
                    max_temp = forecast_response_json_1["forecast"]["forecastday"][0]["day"]["maxtemp_c"]
                    dew_point = response_json_2["current"]["dewpoint_c"]
                else:
                    current_temperature = response_json_2["current"]["temp_f"]
                    feels_like_temperature = response_json_2["current"]["feelslike_f"]
                    min_temp = forecast_response_json_1["forecast"]["forecastday"][0]["day"]["mintemp_f"]
                    max_temp = forecast_response_json_1["forecast"]["forecastday"][0]["day"]["maxtemp_f"]
                    dew_point = response_json_2["current"]["dewpoint_f"]
                current_temperature_description = response_json["weather"][0]["main"]
                current_temperature_description_2 = response_json["weather"][0]["description"]
                city_name = response_json["name"]
                lat_var = response_json["coord"]["lat"]
                lon_var = response_json["coord"]["lon"]
                region_name = response_json_2["location"]["region"]
                country_name = ""
                if "country" in response_json["sys"]:
                    country_name = response_json_2["location"]["country"]
                wind_speed = response_json["wind"]["speed"]
                pressure = response_json["main"]["pressure"]
                humidity = response_json["main"]["humidity"]
                visibility = response_json["visibility"]
                cloudiness = response_json["clouds"]["all"]
                local_time = response_json_2["location"]["localtime"][-5:]
                uv_index = response_json_2["current"]["uv"]
                chance_of_rain = forecast_response_json_1["forecast"]["forecastday"][0]["day"]["daily_chance_of_rain"]
                # sun and moon timings
                curr_day_sunrise_time = forecast_response_json_1["forecast"]["forecastday"][0]["astro"]["sunrise"]
                curr_day_sunset_time = forecast_response_json_1["forecast"]["forecastday"][0]["astro"]["sunset"]
                curr_day_moonrise_time = forecast_response_json_1["forecast"]["forecastday"][0]["astro"]["moonrise"]
                curr_day_moonset_time = forecast_response_json_1["forecast"]["forecastday"][0]["astro"]["moonset"]
                # air quality index and pollutants
                co_pollutant = response_json_2["current"]["air_quality"]["co"]
                no2_pollutant = response_json_2["current"]["air_quality"]["no2"]
                o3_pollutant = response_json_2["current"]["air_quality"]["o3"]
                so2_pollutant = response_json_2["current"]["air_quality"]["so2"]
                pm2_5_pollutant = response_json_2["current"]["air_quality"]["pm2_5"]
                pm10_pollutant = response_json_2["current"]["air_quality"]["pm10"]
                us_epa_index_aqi = response_json_2["current"]["air_quality"]["us-epa-index"]
                # Dictionary for values 1 to 6
                us_epa_index_dict = ["Good","Moderate","Unhealthy for sensitive","Unhealthy","Very Unhealthy","Hazardous"]
                moon_phase = forecast_response_json_1["forecast"]["forecastday"][0]["astro"]["moon_phase"]
                moon_phase_index = moon_phases_all.index(moon_phase)
                moon_phase_pic_arr = ["images/new_moon.png","images/waxing-crescent_moon.png","images/first_quarter.png",
                                      "images/waxing_gibbous.png","images/full_moon.png","images/waning_gibbous.png",
                                      "images/last_quarter.png","images/waning_crescent_moon.png"]
                moon_illumination = forecast_response_json_1["forecast"]["forecastday"][0]["astro"]["moon_illumination"]
                # hourly forecast
                temp_hour_c_arr = [0]*24
                temp_hour_f_arr = [0]*24
                temperature_icon_hourly_arr = [""]*24
                temp_hour_arr = temp_hour_c_arr
                for iter_index in range(24):
                    temperature_icon_hourly_arr[iter_index] = "https:"+forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index]["condition"]["icon"]
                    temp_hour_c_arr[iter_index] = forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index]["temp_c"]
                    temp_hour_f_arr[iter_index] = forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index]["temp_f"]
                if session.get("temp_unit")==False:
                    temp_hour_arr = temp_hour_f_arr
                session["last_visited"] = [lat_var,lon_var]
                session["last_clicked_ptr"]=ptr_index
                # Pollen forecast for 3 days
                hourly_alder_pollen = hourly.Variables(0).ValuesAsNumpy()
                hourly_birch_pollen = hourly.Variables(1).ValuesAsNumpy()
                hourly_grass_pollen = hourly.Variables(2).ValuesAsNumpy()
                hourly_mugwort_pollen = hourly.Variables(3).ValuesAsNumpy()
                hourly_olive_pollen = hourly.Variables(4).ValuesAsNumpy()
                hourly_ragweed_pollen = hourly.Variables(5).ValuesAsNumpy()
                hourly_data = {"date": pd.date_range(
                    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(seconds=hourly.Interval()),
                    inclusive="left"
                )}
                hourly_data["alder_pollen"] = hourly_alder_pollen
                hourly_data["birch_pollen"] = hourly_birch_pollen
                hourly_data["grass_pollen"] = hourly_grass_pollen
                hourly_data["mugwort_pollen"] = hourly_mugwort_pollen
                hourly_data["olive_pollen"] = hourly_olive_pollen
                hourly_data["ragweed_pollen"] = hourly_ragweed_pollen
                hourly_pollen_json = hourly_data
                return render_template("weathercast.html",cities_arr=cities_arr,location_city=city_name,
                                       location_region=region_name,location_country=country_name,
                                       curr_temp=current_temperature,feels_like_temp=feels_like_temperature,
                                       curr_weather_desc_1=current_temperature_description,lat_var=lat_var,lon_var=lon_var,
                                       is_lat_lon_correct=True,curr_weather_desc_2=current_temperature_description_2,
                                       min_temp=min_temp,max_temp=max_temp,curr_wind_speed=wind_speed,curr_pressure=pressure,
                                       curr_humidity=humidity,curr_visibility=visibility,curr_cloudiness=cloudiness,
                                       curr_local_time=local_time,curr_dewpoint=dew_point,curr_temp_unit=session.get("temp_unit"),
                                       curr_temp_unit_value=session.get("temp_unit_value"),curr_uv_index = uv_index,
                                       curr_carbon_monoxide=co_pollutant,curr_nitrogen_dioxide=no2_pollutant,
                                       curr_ozone=o3_pollutant,curr_sulphur_dioxide=so2_pollutant,curr_pm2_5=pm2_5_pollutant,
                                       curr_pm10=pm10_pollutant,aqi_us_epa_index=us_epa_index_dict[us_epa_index_aqi-1],
                                       current_day_sunrise=curr_day_sunrise_time,current_day_sunset=curr_day_sunset_time,
                                       current_day_moonrise=curr_day_moonrise_time,current_day_moonset=curr_day_moonset_time,
                                       temp_at_hour_arr=temp_hour_arr,curr_chance_rain=chance_of_rain,
                                       moon_phase = moon_phase, moon_illumination=moon_illumination,
                                       moon_phase_selected=moon_phase_pic_arr[moon_phase_index]
                                       ,temp_hour_icon_arr=temperature_icon_hourly_arr,starred_locations=session.get("fav_locations"),
                                       modified=str(session.get("cities_lat_arr")[ptr_index])+"&"+str(session.get("cities_lon_arr")[ptr_index]))
            else:
                return render_template("weathercast.html",location_city="",is_lat_lon_correct=False)
    else:
        if response_json!={} and response_json_2!={} and forecast_response_json_1!={} and marine_response_json_1!={} and sports_response_json_1!={} and "cities_lat_arr" in session:
            current_temperature = ""
            feels_like_temperature = ""
            min_temp = ""
            max_temp = ""
            dew_point = ""
            ptr_index = session.get("last_clicked_ptr")
            if session.get("temp_unit") == True:
                current_temperature = response_json_2["current"]["temp_c"]
                feels_like_temperature = response_json_2["current"]["feelslike_c"]
                min_temp = forecast_response_json_1["forecast"]["forecastday"][0]["day"]["mintemp_c"]
                max_temp = forecast_response_json_1["forecast"]["forecastday"][0]["day"]["maxtemp_c"]
                dew_point = response_json_2["current"]["dewpoint_c"]
            else:
                current_temperature = response_json_2["current"]["temp_f"]
                feels_like_temperature = response_json_2["current"]["feelslike_f"]
                min_temp = forecast_response_json_1["forecast"]["forecastday"][0]["day"]["mintemp_f"]
                max_temp = forecast_response_json_1["forecast"]["forecastday"][0]["day"]["maxtemp_f"]
                dew_point = response_json_2["current"]["dewpoint_f"]
            current_temperature_description = response_json["weather"][0]["main"]
            current_temperature_description_2 = response_json["weather"][0]["description"]
            city_name = response_json["name"]
            lat_var = response_json["coord"]["lat"]
            lon_var = response_json["coord"]["lon"]
            region_name = response_json_2["location"]["region"]
            country_name = ""
            if "country" in response_json["sys"]:
                country_name = response_json_2["location"]["country"]
            wind_speed = response_json["wind"]["speed"]
            pressure = response_json["main"]["pressure"]
            humidity = response_json["main"]["humidity"]
            visibility = response_json["visibility"]
            cloudiness = response_json["clouds"]["all"]
            local_time = response_json_2["location"]["localtime"][-5:]
            uv_index = response_json_2["current"]["uv"]
            chance_of_rain = forecast_response_json_1["forecast"]["forecastday"][0]["day"]["daily_chance_of_rain"]
            # sun and moon timings
            curr_day_sunrise_time = forecast_response_json_1["forecast"]["forecastday"][0]["astro"]["sunrise"]
            curr_day_sunset_time = forecast_response_json_1["forecast"]["forecastday"][0]["astro"]["sunset"]
            curr_day_moonrise_time = forecast_response_json_1["forecast"]["forecastday"][0]["astro"]["moonrise"]
            curr_day_moonset_time = forecast_response_json_1["forecast"]["forecastday"][0]["astro"]["moonset"]
            # air quality index and pollutants
            co_pollutant = response_json_2["current"]["air_quality"]["co"]
            no2_pollutant = response_json_2["current"]["air_quality"]["no2"]
            o3_pollutant = response_json_2["current"]["air_quality"]["o3"]
            so2_pollutant = response_json_2["current"]["air_quality"]["so2"]
            pm2_5_pollutant = response_json_2["current"]["air_quality"]["pm2_5"]
            pm10_pollutant = response_json_2["current"]["air_quality"]["pm10"]
            us_epa_index_aqi = response_json_2["current"]["air_quality"]["us-epa-index"]
            # Dictionary for values 1 to 6
            us_epa_index_dict = ["Good", "Moderate", "Unhealthy for sensitive", "Unhealthy", "Very Unhealthy", "Hazardous"]
            moon_phase = forecast_response_json_1["forecast"]["forecastday"][0]["astro"]["moon_phase"]
            moon_phase_index = moon_phases_all.index(moon_phase)
            moon_phase_pic_arr = ["images/new_moon.png", "images/waxing-crescent_moon.png", "images/first_quarter.png",
                                  "images/waxing_gibbous.png", "images/full_moon.png", "images/waning_gibbous.png",
                                  "images/last_quarter.png", "images/waning_crescent_moon.png"]
            moon_illumination = forecast_response_json_1["forecast"]["forecastday"][0]["astro"]["moon_illumination"]
            # hourly forecast
            temp_hour_c_arr = [0] * 24
            temp_hour_f_arr = [0] * 24
            temperature_icon_hourly_arr = [""] * 24
            temp_hour_arr = temp_hour_c_arr
            for iter_index in range(24):
                temperature_icon_hourly_arr[iter_index] = "https:" + \
                                                          forecast_response_json_1["forecast"]["forecastday"][0]["hour"][
                                                              iter_index]["condition"]["icon"]
                temp_hour_c_arr[iter_index] = forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index][
                    "temp_c"]
                temp_hour_f_arr[iter_index] = forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index][
                    "temp_f"]
            if session.get("temp_unit") == False:
                temp_hour_arr = temp_hour_f_arr
            session["last_visited"] = [lat_var, lon_var]
            session["last_clicked_ptr"] = ptr_index
            # Pollen forecast values for 3 days.
            hourly_alder_pollen = hourly_var.Variables(0).ValuesAsNumpy()
            hourly_birch_pollen = hourly_var.Variables(1).ValuesAsNumpy()
            hourly_grass_pollen = hourly_var.Variables(2).ValuesAsNumpy()
            hourly_mugwort_pollen = hourly_var.Variables(3).ValuesAsNumpy()
            hourly_olive_pollen = hourly_var.Variables(4).ValuesAsNumpy()
            hourly_ragweed_pollen = hourly_var.Variables(5).ValuesAsNumpy()
            hourly_data = {"date": pd.date_range(
                start=pd.to_datetime(hourly_var.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly_var.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly_var.Interval()),
                inclusive="left"
            )}
            hourly_data["alder_pollen"] = hourly_alder_pollen
            hourly_data["birch_pollen"] = hourly_birch_pollen
            hourly_data["grass_pollen"] = hourly_grass_pollen
            hourly_data["mugwort_pollen"] = hourly_mugwort_pollen
            hourly_data["olive_pollen"] = hourly_olive_pollen
            hourly_data["ragweed_pollen"] = hourly_ragweed_pollen
            hourly_pollen_json = hourly_data
            return render_template("weathercast.html", cities_arr=session.get("cities_arr"), location_city=city_name,
                                   location_region=region_name, location_country=country_name,
                                   curr_temp=current_temperature, feels_like_temp=feels_like_temperature,
                                   curr_weather_desc_1=current_temperature_description, lat_var=lat_var, lon_var=lon_var,
                                   is_lat_lon_correct=True, curr_weather_desc_2=current_temperature_description_2,
                                   min_temp=min_temp, max_temp=max_temp, curr_wind_speed=wind_speed, curr_pressure=pressure,
                                   curr_humidity=humidity, curr_visibility=visibility, curr_cloudiness=cloudiness,
                                   curr_local_time=local_time, curr_dewpoint=dew_point,
                                   curr_temp_unit=session.get("temp_unit"),
                                   curr_temp_unit_value=session.get("temp_unit_value"), curr_uv_index=uv_index,
                                   curr_carbon_monoxide=co_pollutant, curr_nitrogen_dioxide=no2_pollutant,
                                   curr_ozone=o3_pollutant, curr_sulphur_dioxide=so2_pollutant, curr_pm2_5=pm2_5_pollutant,
                                   curr_pm10=pm10_pollutant, aqi_us_epa_index=us_epa_index_dict[us_epa_index_aqi - 1],
                                   current_day_sunrise=curr_day_sunrise_time, current_day_sunset=curr_day_sunset_time,
                                   current_day_moonrise=curr_day_moonrise_time, current_day_moonset=curr_day_moonset_time,
                                   temp_at_hour_arr=temp_hour_arr, curr_chance_rain=chance_of_rain,
                                   moon_phase=moon_phase, moon_illumination=moon_illumination,
                                   moon_phase_selected=moon_phase_pic_arr[moon_phase_index]
                                   , temp_hour_icon_arr=temperature_icon_hourly_arr,starred_locations=session["fav_locations"],
                                  modified=str(session.get("cities_lat_arr")[ptr_index])+"&"+str(session.get("cities_lon_arr")[ptr_index]))
        else:
            return render_template("weathercast.html",cities_arr=session.get("cities_arr"))
            # "404 Could not connect to the server"
    return render_template("weathercast.html",cities_arr=session.get("cities_arr"))


@app.route('/<anypage>',methods=["POST","GET"])
def open_any_webpage(anypage):
    return redirect(url_for("index"))

# Function to change the unit of temperature between Celsius and Fahrenheit.
def change_temp_unit():
    session["temp_unit"] = not(session["temp_unit"])
    if session.get("temp_unit")==True:
        session["temp_unit_value"] = "℃"
    else:
        session["temp_unit_value"] = "℉"

# Function to add or remove locations as favorites.
def add_or_remove_star():
    if "last_clicked_ptr" in session and session.get("last_clicked_ptr")!=None:
        if response_json!={} and response_json_2!={} and forecast_response_json_1!={}:
            ptr_index = session.get("last_clicked_ptr")
            fav_locations_dict = session.get("fav_locations")
            lat_lon_key_formed = str(session.get("cities_lat_arr")[ptr_index]) + "&" + str(session.get("cities_lon_arr")[ptr_index])
            if lat_lon_key_formed not in fav_locations_dict:
                fav_locations_dict[
                    str(session.get("cities_lat_arr")[ptr_index]) + "&" + str(session.get("cities_lon_arr")[ptr_index])] = response_json["name"]+", "+response_json_2["location"]["region"]+", "+response_json_2["location"]["country"]
            else:
                fav_locations_dict.pop(
                    str(session.get("cities_lat_arr")[ptr_index]) + "&" + str(session.get("cities_lon_arr")[ptr_index]))
    else:
        return render_template("weathercast.html")

# Function to route to the 'forecasts' web page
@app.route('/forecasts',methods=["POST","GET"])
def forecasts():
    active_button = ""
    total_day_1 = ""
    total_day_2 = ""
    total_day_3 = ""
    city_name = ""
    x_values = [str(x) for x in range(0, 24)]
    if response_json!={}:
        city_name = response_json["name"]
    if response_json_2!={}:
        total_day_1 = find_date(response_json_2["location"]["localtime"][8:10])+" "+find_month(response_json_2["location"]["localtime"][5:7])
    if forecast_response_json_1!={}:
        total_day_1 = (find_date(forecast_response_json_1["forecast"]["forecastday"][0]["date"][8:])+" "+
                       find_month(forecast_response_json_1["forecast"]["forecastday"][0]["date"][5:7]))
        total_day_2 = (find_date(forecast_response_json_1["forecast"]["forecastday"][1]["date"][8:]) + " " +
                       find_month(forecast_response_json_1["forecast"]["forecastday"][1]["date"][5:7]))
        total_day_3 = (find_date(forecast_response_json_1["forecast"]["forecastday"][2]["date"][8:]) + " " +
                       find_month(forecast_response_json_1["forecast"]["forecastday"][2]["date"][5:7]))
    # If there are no data to display, the three dictionaries are empty, and returned to the function index().
    if response_json=={} or response_json_2=={} or forecast_response_json_1=={}:
        return redirect(url_for("index"))
    if request.method=="POST":
        if "btn_temperature" in request.form:
            y_values_arr_1 = []
            y_values_arr_2 = []
            y_values_arr_3 = []
            active_button = "btn_temperature"
            if session.get("temp_unit") == True:
                for iter_index_ in range(24):
                    y_values_arr_1.append(
                        forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["temp_c"])
            else:
                for iter_index_ in range(24):
                    y_values_arr_1.append(
                        forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["temp_f"])
            if session.get("temp_unit") == True:
                for iter_index_ in range(24):
                    y_values_arr_2.append(
                        forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["temp_c"])
            else:
                for iter_index_ in range(24):
                    y_values_arr_2.append(
                        forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["temp_f"])
            if session.get("temp_unit") == True:
                for iter_index_ in range(24):
                    y_values_arr_3.append(
                        forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["temp_c"])
            else:
                for iter_index_ in range(24):
                    y_values_arr_3.append(
                        forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["temp_f"])
            if session.get("temp_unit") == True:
                graph_created = create_graph(x_values, y_values_arr_1, "Celsius",y_values_arr_2,y_values_arr_3,total_day_1,
                                             total_day_2,total_day_3,"o")
            else:
                graph_created = create_graph(x_values, y_values_arr_1, "Fahrenheit", y_values_arr_2, y_values_arr_3,
                                             total_day_1,total_day_2,total_day_3,"o")
            return render_template("forecasts.html", graph=graph_created,active_button=active_button,
                                   location_city=city_name)
        elif "btn_temp_feels_like" in request.form:
            y_values_arr_1 = []
            y_values_arr_2 = []
            y_values_arr_3 = []
            active_button = "btn_temp_feels_like"
            if session.get("temp_unit") == True:
                for iter_index_ in range(24):
                    y_values_arr_1.append(
                        forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["feelslike_c"])
            else:
                for iter_index_ in range(24):
                    y_values_arr_1.append(
                        forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["feelslike_f"])
            if session.get("temp_unit") == True:
                for iter_index_ in range(24):
                    y_values_arr_2.append(
                        forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["feelslike_c"])
            else:
                for iter_index_ in range(24):
                    y_values_arr_2.append(
                        forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["feelslike_f"])
            if session.get("temp_unit") == True:
                for iter_index_ in range(24):
                    y_values_arr_3.append(
                        forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["feelslike_c"])
            else:
                for iter_index_ in range(24):
                    y_values_arr_3.append(
                        forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["feelslike_f"])
            if session.get("temp_unit")==True:
                graph_created = create_graph(x_values, y_values_arr_1, "Celsius", y_values_arr_2, y_values_arr_3,
                                             total_day_1,total_day_2,total_day_3,"o")
            else:
                graph_created = create_graph(x_values, y_values_arr_1, "Fahrenheit", y_values_arr_2,
                                             y_values_arr_3,total_day_1,total_day_2,total_day_3,"o")
            return render_template("forecasts.html", graph=graph_created,active_button=active_button,
                                                                        location_city=city_name)
        elif "btn_wind" in request.form:
            y_values_arr_1 = []
            y_values_arr_2 = []
            y_values_arr_3 = []
            active_button = "btn_wind"
            for iter_index_ in range(24):
                y_values_arr_1.append(
                    forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["wind_mph"])
            for iter_index_ in range(24):
                y_values_arr_2.append(
                    forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["wind_mph"])
            for iter_index_ in range(24):
                y_values_arr_3.append(
                    forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["wind_mph"])
            graph_created = create_graph(x_values, y_values_arr_1, "mph", y_values_arr_2,
                                         y_values_arr_3,total_day_1,total_day_2,total_day_3,"o")
            return render_template("forecasts.html", graph=graph_created, active_button=active_button,
                                   location_city=city_name)
        elif "btn_wind_gust" in request.form:
            y_values_arr_1 = []
            y_values_arr_2 = []
            y_values_arr_3 = []
            active_button = "btn_wind_gust"
            for iter_index_ in range(24):
                y_values_arr_1.append(
                    forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["gust_mph"])
            for iter_index_ in range(24):
                y_values_arr_2.append(
                    forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["gust_mph"])
            for iter_index_ in range(24):
                y_values_arr_3.append(
                    forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["gust_mph"])
            graph_created = create_graph(x_values, y_values_arr_1, "mph", y_values_arr_2,
                                         y_values_arr_3,total_day_1,total_day_2,total_day_3,"o")
            return render_template("forecasts.html", graph=graph_created, active_button=active_button,
                                   location_city=city_name)
        elif "btn_precipitation" in request.form:
            y_values_arr_1 = []
            y_values_arr_2 = []
            y_values_arr_3 = []
            active_button = "btn_precipitation"
            for iter_index_ in range(24):
                y_values_arr_1.append(
                    forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["precip_mm"])
            for iter_index_ in range(24):
                y_values_arr_2.append(
                    forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["precip_mm"])
            for iter_index_ in range(24):
                y_values_arr_3.append(
                    forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["precip_mm"])
            graph_created = create_graph(x_values, y_values_arr_1, "mm", y_values_arr_2,
                                         y_values_arr_3,total_day_1,total_day_2,total_day_3,"o")
            return render_template("forecasts.html", graph=graph_created, active_button=active_button,
                                   location_city=city_name)
        elif "btn_humidity" in request.form:
            y_values_arr_1 = []
            y_values_arr_2 = []
            y_values_arr_3 = []
            active_button = "btn_humidity"
            for iter_index_ in range(24):
                y_values_arr_1.append(
                    forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["humidity"])
            for iter_index_ in range(24):
                y_values_arr_2.append(
                    forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["humidity"])
            for iter_index_ in range(24):
                y_values_arr_3.append(
                    forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["humidity"])
            graph_created = create_graph(x_values, y_values_arr_1, "%", y_values_arr_2,
                                         y_values_arr_3,total_day_1,total_day_2,total_day_3,"o")
            return render_template("forecasts.html", graph=graph_created, active_button=active_button,
                                   location_city=city_name)
        elif "btn_pressure" in request.form:
            y_values_arr_1 = []
            y_values_arr_2 = []
            y_values_arr_3 = []
            active_button = "btn_pressure"
            for iter_index_ in range(24):
                y_values_arr_1.append(
                    forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["pressure_mb"])
            for iter_index_ in range(24):
                y_values_arr_2.append(
                    forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["pressure_mb"])
            for iter_index_ in range(24):
                y_values_arr_3.append(
                    forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["pressure_mb"])
            graph_created = create_graph(x_values, y_values_arr_1, "hPa", y_values_arr_2,
                                         y_values_arr_3,total_day_1,total_day_2,total_day_3,"o")
            return render_template("forecasts.html", graph=graph_created, active_button=active_button,
                                   location_city=city_name)
        elif "btn_dewpoint" in request.form:
            y_values_arr_1 = []
            y_values_arr_2 = []
            y_values_arr_3 = []
            active_button = "btn_dewpoint"
            if session.get("temp_unit")==True:
                for iter_index_ in range(24):
                    y_values_arr_1.append(
                        forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["dewpoint_c"])
                for iter_index_ in range(24):
                    y_values_arr_2.append(
                        forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["dewpoint_c"])
                for iter_index_ in range(24):
                    y_values_arr_3.append(
                        forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["dewpoint_c"])
                graph_created = create_graph(x_values, y_values_arr_1, "Celsius", y_values_arr_2,
                                             y_values_arr_3,total_day_1,total_day_2,total_day_3,"o")
            else:
                for iter_index_ in range(24):
                    y_values_arr_1.append(
                        forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["dewpoint_f"])
                for iter_index_ in range(24):
                    y_values_arr_2.append(
                        forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["dewpoint_f"])
                for iter_index_ in range(24):
                    y_values_arr_3.append(
                        forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["dewpoint_f"])
                graph_created = create_graph(x_values, y_values_arr_1, "Fahrenheit", y_values_arr_2,
                                         y_values_arr_3,total_day_1,total_day_2,total_day_3,"o")
            return render_template("forecasts.html", graph=graph_created, active_button=active_button,
                                   location_city=city_name)
        elif "btn_chance_of_rain" in request.form:
            y_values_arr_1 = []
            y_values_arr_2 = []
            y_values_arr_3 = []
            active_button = "btn_chance_of_rain"
            for iter_index_ in range(24):
                y_values_arr_1.append(
                    forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["chance_of_rain"])
            for iter_index_ in range(24):
                y_values_arr_2.append(
                    forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["chance_of_rain"])
            for iter_index_ in range(24):
                y_values_arr_3.append(
                    forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["chance_of_rain"])
            graph_created = create_graph(x_values, y_values_arr_1, "%", y_values_arr_2,y_values_arr_3,
                                         total_day_1,total_day_2,total_day_3,"o")
            return render_template("forecasts.html", graph=graph_created, active_button=active_button,
                                                                                location_city=city_name)
        elif "btn_snowfall" in request.form:
            y_values_arr_1 = []
            y_values_arr_2 = []
            y_values_arr_3 = []
            active_button = "btn_snowfall"
            for iter_index_ in range(24):
                y_values_arr_1.append(
                    forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["snow_cm"])
            for iter_index_ in range(24):
                y_values_arr_2.append(
                    forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["snow_cm"])
            for iter_index_ in range(24):
                y_values_arr_3.append(
                    forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["snow_cm"])
            graph_created = create_graph(x_values, y_values_arr_1, "cm", y_values_arr_2,y_values_arr_3,
                                         total_day_1,total_day_2,total_day_3,"o")
            return render_template("forecasts.html", graph=graph_created, active_button=active_button,
                                                                                location_city=city_name)
        elif "btn_uv" in request.form:
            y_values_arr_1 = []
            y_values_arr_2 = []
            y_values_arr_3 = []
            active_button = "btn_uv"
            for iter_index_ in range(24):
                y_values_arr_1.append(
                    forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["uv"])
            for iter_index_ in range(24):
                y_values_arr_2.append(
                    forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["uv"])
            for iter_index_ in range(24):
                y_values_arr_3.append(
                    forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["uv"])
            graph_created = create_graph(x_values, y_values_arr_1, "", y_values_arr_2, y_values_arr_3,
                                         total_day_1,total_day_2,total_day_3,"o")
            return render_template("forecasts.html", graph=graph_created, active_button=active_button,
                                                                            location_city=city_name)
        elif "btn_visibility" in request.form:
            if forecast_response_json_1!={}:
                y_values_arr_1 = []
                y_values_arr_2 = []
                y_values_arr_3 = []
                active_button = "btn_visibility"
                for iter_index_ in range(24):
                    y_values_arr_1.append(
                        forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["vis_miles"])
                for iter_index_ in range(24):
                    y_values_arr_2.append(
                        forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["vis_miles"])
                for iter_index_ in range(24):
                    y_values_arr_3.append(
                        forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["vis_miles"])
                graph_created = create_graph(x_values, y_values_arr_1, "miles", y_values_arr_2, y_values_arr_3,
                                             total_day_1, total_day_2, total_day_3,"o")
                return render_template("forecasts.html", graph=graph_created, active_button=active_button,
                                                                    location_city=city_name)
        else:
            pass
    else:
        if forecast_response_json_1!={}:
            active_button = "btn_temperature"
            y_values_arr_1 = []
            y_values_arr_2 = []
            y_values_arr_3 = []
            if session.get("temp_unit") == True:
                for iter_index_ in range(24):
                    y_values_arr_1.append(
                        forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["temp_c"])
            else:
                for iter_index_ in range(24):
                    y_values_arr_1.append(
                        forecast_response_json_1["forecast"]["forecastday"][0]["hour"][iter_index_]["temp_f"])
            if session.get("temp_unit") == True:
                for iter_index_ in range(24):
                    y_values_arr_2.append(
                        forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["temp_c"])
            else:
                for iter_index_ in range(24):
                    y_values_arr_2.append(
                        forecast_response_json_1["forecast"]["forecastday"][1]["hour"][iter_index_]["temp_f"])
            if session.get("temp_unit") == True:
                for iter_index_ in range(24):
                    y_values_arr_3.append(
                        forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["temp_c"])
            else:
                for iter_index_ in range(24):
                    y_values_arr_3.append(
                        forecast_response_json_1["forecast"]["forecastday"][2]["hour"][iter_index_]["temp_f"])
            if session.get("temp_unit") == True:
                graph_created = create_graph(x_values, y_values_arr_1, "Celsius",y_values_arr_2,y_values_arr_3,
                                             total_day_1,total_day_2,total_day_3,"o")
            else:
                graph_created = create_graph(x_values, y_values_arr_1, "Fahrenheit", y_values_arr_2, y_values_arr_3,
                                             total_day_1,total_day_2,total_day_3,"o")
            return render_template("forecasts.html", graph=graph_created,active_button=active_button,
                                   location_city=city_name)
    return redirect(url_for("index"))

# Function to create graph with three different plots
def create_graph(x_data_arr,y_data_arr,category,y_data_arr_2,y_data_arr_3,total_day_1,total_day_2,total_day_3,custom_marker):
    data = {
        'hours': x_data_arr,
        'temperature': y_data_arr
    }
    df = pd.DataFrame(data)
    plt.figure(figsize=(15, 5))
    ax = sns.lineplot(x='hours', y='temperature', data=df, color="blue", marker=custom_marker, markersize=9, linewidth=1.8,
                      markerfacecolor="black", linestyle="--",label=total_day_1)
    data = {
        'hours': x_data_arr,
        'temperature': y_data_arr_2
    }
    df = pd.DataFrame(data)
    ax = sns.lineplot(x='hours', y='temperature', data=df, color="green", marker=custom_marker, markersize=6, linewidth=1.8,
                      markerfacecolor="black", linestyle="--",label=total_day_2)
    data = {
        'hours': x_data_arr,
        'temperature': y_data_arr_3
    }
    df = pd.DataFrame(data)
    ax = sns.lineplot(x='hours', y='temperature', data=df, color="brown", marker=custom_marker, markersize=6, linewidth=1.8,
                      markerfacecolor="black", linestyle="--",label=total_day_3)

    plt.gcf().set_facecolor("#6FE6FC")
    ax.set_facecolor("white")
    plt.title('')
    plt.xlabel('Hour')
    plt.ylabel(category)
    plt.legend(
        loc="best",  # any best position inside graph
        fontsize=10,  # smaller text
        frameon=True,  # show box
        fancybox=True, shadow=True,
        title="Forecast Days"  # legend box title
    )
    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    graph_url = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()
    return graph_url

# Function to match the integers from 1 to 31 with words in string format.
def find_date(curr_date):
    dates_dict = {"01":"1st","02":"2nd","03":"3rd","04":"4th","05":"5th","06":"6th","07":"7th","08":"8th","09":"9th","10":"10th",
                  "11":"11th","12":"12th","13":"13th","14":"14th","15":"15th","16":"16th","17":"17th","18":"18th","19":"19th",
                  "20":"20th","21":"21st","22":"22nd","23":"23rd","24":"24th","25":"25th","26":"26th","27":"27th","28":"28th",
                  "29":"29th","30":"30th","31":"31st"}
    return dates_dict.get(curr_date)

# Function to match the integer from 1 to 12 with month names.
def find_month(curr_month):
    months_dict = {"01":"Jan","02":"Feb","03":"March","04":"April","05":"May","06":"Jun","07":"July","08":"Aug","09":"Sept",
                   "10":"Oct","11":"Nov","12":"Dec"}
    return months_dict.get(curr_month)

@app.route('/historical_weather',methods=["POST","GET"])
def historical_weather():
    return render_template("historical_weather.html")

# Function to route to marine web page
@app.route('/marine',methods=["POST","GET"])
def marine():
    if marine_response_json_1!={}:
        total_curr_day = (find_date(marine_response_json_1["location"]["localtime"][8:10])+" "+
                          find_month(marine_response_json_1["location"]["localtime"][5:7])+" "+
                          marine_response_json_1["location"]["localtime"][0:4])
        min_temp_marine_c = marine_response_json_1["forecast"]["forecastday"][0]["day"]["mintemp_c"]
        min_temp_marine_f = marine_response_json_1["forecast"]["forecastday"][0]["day"]["mintemp_f"]
        max_temp_marine_c = marine_response_json_1["forecast"]["forecastday"][0]["day"]["maxtemp_c"]
        max_temp_marine_f = marine_response_json_1["forecast"]["forecastday"][0]["day"]["maxtemp_f"]
        min_max_temp_arr = []
        max_wind_mph = marine_response_json_1["forecast"]["forecastday"][0]["day"]["maxwind_mph"]
        total_precipitation = marine_response_json_1["forecast"]["forecastday"][0]["day"]["totalprecip_mm"]
        average_visibility_miles = marine_response_json_1["forecast"]["forecastday"][0]["day"]["avgvis_miles"]
        average_humidity = marine_response_json_1["forecast"]["forecastday"][0]["day"]["avghumidity"]
        uv_marine = marine_response_json_1["forecast"]["forecastday"][0]["day"]["uv"]
        sunrise_marine = marine_response_json_1["forecast"]["forecastday"][0]["astro"]["sunrise"]
        sunset_marine = marine_response_json_1["forecast"]["forecastday"][0]["astro"]["sunset"]
        moonrise_marine = marine_response_json_1["forecast"]["forecastday"][0]["astro"]["moonrise"]
        moonset_marine = marine_response_json_1["forecast"]["forecastday"][0]["astro"]["moonset"]
        if session.get("temp_unit")==True:
            min_max_temp_arr = [min_temp_marine_c,max_temp_marine_c]
        else:
            min_max_temp_arr = [min_temp_marine_f,max_temp_marine_f]
        return render_template("marine.html",current_date=total_curr_day,marine_min_temp=min_max_temp_arr[0],
                               marine_max_temp=min_max_temp_arr[1],marine_max_wind_speed=max_wind_mph,
                               marine_total_precipitation=total_precipitation,average_visibility_miles=average_visibility_miles,
                               temp_unit_value=session.get("temp_unit_value"),average_humidity=average_humidity,
                               marine_uv_index=uv_marine,marine_sunrise=sunrise_marine,marine_sunset=sunset_marine,
                               marine_moonrise=moonrise_marine,marine_moonset=moonset_marine)
    else:
        return redirect(url_for("index"))

@app.route('/pollen',methods=["POST","GET"])
def pollen():
    active_button = "btn_alder"
    pollen_available = True
    x_value_arr = [str(x) for x in range(0, 24)]
    y_values_arr_1 = []
    y_values_arr_2 = []
    y_values_arr_3 = []
    total_day_1 = ""
    total_day_2 = ""
    total_day_3 = ""
    city_name = ""
    # Checking if the data is fetched from different API endpoints.
    # If not fetched, redirect to the home page with no data to show.
    if response_json=={} or response_json_2=={} or forecast_response_json_1=={}:
        return redirect(url_for("index"))
    if response_json!={}:
        city_name = response_json["name"]
    if response_json_2!={}:
        total_day_1 = find_date(response_json_2["location"]["localtime"][8:10])+" "+find_month(response_json_2["location"]["localtime"][5:7])
    if forecast_response_json_1!={}:
        total_day_1 = (find_date(forecast_response_json_1["forecast"]["forecastday"][0]["date"][8:])+" "+
                       find_month(forecast_response_json_1["forecast"]["forecastday"][0]["date"][5:7]))
        total_day_2 = (find_date(forecast_response_json_1["forecast"]["forecastday"][1]["date"][8:]) + " " +
                       find_month(forecast_response_json_1["forecast"]["forecastday"][1]["date"][5:7]))
        total_day_3 = (find_date(forecast_response_json_1["forecast"]["forecastday"][2]["date"][8:]) + " " +
                       find_month(forecast_response_json_1["forecast"]["forecastday"][2]["date"][5:7]))
    if request.method=="POST":
        # When Alder button is clicked.
        if "btn_alder" in request.form:
            y_values_arr_1 = hourly_pollen_json["alder_pollen"][0:24]
            y_values_arr_2 = hourly_pollen_json["alder_pollen"][24:48]
            y_values_arr_3 = hourly_pollen_json["alder_pollen"][48:]
            if y_values_arr_1[0]=="nan":
                pollen_available = False
            active_button = "btn_alder"
            graph_created = create_graph(x_value_arr, y_values_arr_1, "grains", y_values_arr_2, y_values_arr_3, total_day_1, total_day_2,
                                         total_day_3,"X")
            return render_template("pollen.html", pollen_graph=graph_created, active_button=active_button,
                                   pollen_available=pollen_available,location_city=city_name)
        # When Birch button is clicked.
        elif "btn_birch" in request.form:
            y_values_arr_1 = hourly_pollen_json["birch_pollen"][0:24]
            y_values_arr_2 = hourly_pollen_json["birch_pollen"][24:48]
            y_values_arr_3 = hourly_pollen_json["birch_pollen"][48:]
            active_button = "btn_birch"
            if y_values_arr_1[0]=="nan":
                pollen_available = False
            graph_created = create_graph(x_value_arr, y_values_arr_1, "grains", y_values_arr_2, y_values_arr_3, total_day_1, total_day_2,
                                         total_day_3,"X")
            return render_template("pollen.html", pollen_graph=graph_created, active_button=active_button,
                                   pollen_available=pollen_available,location_city=city_name)
        # When Grass button is clicked.
        elif "btn_grass" in request.form:
            y_values_arr_1 = hourly_pollen_json["grass_pollen"][0:24]
            y_values_arr_2 = hourly_pollen_json["grass_pollen"][24:48]
            y_values_arr_3 = hourly_pollen_json["grass_pollen"][48:]
            if y_values_arr_1[0]=="nan":
                pollen_available = False
            active_button = "btn_grass"
            graph_created = create_graph(x_value_arr, y_values_arr_1, "grains", y_values_arr_2, y_values_arr_3, total_day_1, total_day_2,
                                         total_day_3,"X")
            return render_template("pollen.html", pollen_graph=graph_created, active_button=active_button,
                                   pollen_available=pollen_available,location_city=city_name)
        # When Mugwort button is clicked.
        elif "btn_mugwort" in request.form:
            y_values_arr_1 = hourly_pollen_json["mugwort_pollen"][0:24]
            y_values_arr_2 = hourly_pollen_json["mugwort_pollen"][24:48]
            y_values_arr_3 = hourly_pollen_json["mugwort_pollen"][48:]
            if y_values_arr_1[0]=="nan":
                pollen_available = False
            active_button = "btn_mugwort"
            graph_created = create_graph(x_value_arr, y_values_arr_1, "grains", y_values_arr_2, y_values_arr_3, total_day_1, total_day_2,
                                         total_day_3,"X")
            return render_template("pollen.html", pollen_graph=graph_created, active_button=active_button,
                                   pollen_available=pollen_available,location_city=city_name)
        # When Olive button is clicked.
        elif "btn_olive" in request.form:
            y_values_arr_1 = hourly_pollen_json["olive_pollen"][0:24]
            y_values_arr_2 = hourly_pollen_json["olive_pollen"][24:48]
            y_values_arr_3 = hourly_pollen_json["olive_pollen"][48:]
            if y_values_arr_1[0]=="nan":
                pollen_available = False
            active_button = "btn_olive"
            graph_created = create_graph(x_value_arr, y_values_arr_1, "grains", y_values_arr_2, y_values_arr_3, total_day_1, total_day_2,
                                         total_day_3,"X")
            return render_template("pollen.html", pollen_graph=graph_created, active_button=active_button,
                                   pollen_available=pollen_available,location_city=city_name)
        # When Ragweed button is clicked.
        elif "btn_ragweed" in request.form:
            y_values_arr_1 = hourly_pollen_json["ragweed_pollen"][0:24]
            y_values_arr_2 = hourly_pollen_json["ragweed_pollen"][24:48]
            y_values_arr_3 = hourly_pollen_json["ragweed_pollen"][48:]
            if y_values_arr_1[0]=="nan":
                pollen_available = False
            active_button = "btn_ragweed"
            graph_created = create_graph(x_value_arr, y_values_arr_1, "grains", y_values_arr_2, y_values_arr_3, total_day_1, total_day_2,total_day_3,"X")
            return render_template("pollen.html", pollen_graph=graph_created, active_button=active_button,
                                   pollen_available=pollen_available,location_city=city_name)
    # Data to display initially when the pollen page is opened is Alder pollen.
    else:
        y_values_arr_1 = hourly_pollen_json["alder_pollen"][0:24]
        y_values_arr_2 = hourly_pollen_json["alder_pollen"][24:48]
        y_values_arr_3 = hourly_pollen_json["alder_pollen"][48:]
        if y_values_arr_1[0] == "nan":
            pollen_available = False
        graph_created = create_graph(x_value_arr,y_values_arr_1,"grains",y_values_arr_2,y_values_arr_3,total_day_1,total_day_2,total_day_3,"X")
        return render_template("pollen.html",pollen_graph=graph_created, active_button=active_button,
                               pollen_available=pollen_available,location_city=city_name)

# Opens the favorites web page.
@app.route('/favorites')
def favorites():
    fav_locations_dict = session.get("fav_locations")
    return render_template("favorites.html",starred_locations=fav_locations_dict)

# Opens the sports web page.
@app.route('/sports')
def sports():
    if response_json!={} and sports_response_json_1!={}:
        city_name = response_json["name"]
        upcoming_cricket_matches = sports_response_json_1.get("cricket")
        upcoming_football_matches = sports_response_json_1.get("football")
        upcoming_golf_matches = sports_response_json_1.get("golf")
        return render_template("sports.html",cricket_matches=upcoming_cricket_matches,
                               football_matches=upcoming_football_matches,golf_matches=upcoming_golf_matches,location_city=city_name)
    else:
        return redirect(url_for("index"))

# Running the flask app.
if __name__=="__main__":
    app.run(debug=True)
