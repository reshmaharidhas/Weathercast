import requests
import os
from flask import Flask, render_template, request, flash, redirect, url_for

app = Flask(__name__)
app.secret_key = "omg"

@app.route('/')
@app.route('/',methods=["POST","GET"])
@app.route('/weathercast',methods=["POST","GET"])
def index():
    if request.method=="POST":
        secret_api_key = os.getenv("API_KEY")
        lat_var = request.form["latitude"]
        lon_var = request.form["longitude"]
        if lat_var.isalpha() or lon_var.isalpha():
            flash("Incorrect latitude and longitude! Please enter the values in numbers","info")
            return render_template("weathercast.html",location_city="",is_lat_lon_correct=False)
        lat = abs(float(lat_var))
        lon = abs(float(lon_var))
        correct_latitude_longitude = True
        if (lat>=0 and lat<=90) and (lon>=0 and lon<=180):
            custom_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat_var}&lon={lon_var}&appid={secret_api_key}&units=metric"
            response = requests.get(custom_url)
            status=response.status_code
            if status==200:
                response_json = response.json()
                current_temperature = response_json["main"]["temp"]
                feels_like_temperature = response_json["main"]["feels_like"]
                current_temperature_description = response_json["weather"][0]["main"]
                city_name = response_json["name"]
                is_Country = False
                country_name = ""
                if "country" in response_json["sys"]:
                    is_Country = True
                    country_name = response_json["sys"]["country"]
                min_temp = response_json["main"]["temp_min"]
                max_temp = response_json["main"]["temp_max"]
                return render_template("weathercast.html",curr_temp=current_temperature,curr_weather_desc_1=current_temperature_description,location_city=city_name,feels_like_temp=feels_like_temperature,lat_var=lat_var,lon_var=lon_var,
                                       min_temp=min_temp,max_temp=max_temp,is_Country=is_Country,location_country=country_name,is_lat_lon_correct=correct_latitude_longitude)
            else:
                return render_template("weathercast.html",curr_temp="",curr_weather_desc_1="",location_city="",is_lat_lon_correct=correct_latitude_longitude)
        else:
            correct_latitude_longitude = False
            if (lat<(-90) or lat>90) and (lon>=0 and lon<=180):
                flash("Incorrect latitude!","info")
            elif (lon<(-180) and lon>180) and (lat>=0 and lat<=90):
                flash("Incorrect longitude!","info")
            else:
                flash("Incorrect latitude and longitude","info")
            return render_template("weathercast.html",curr_temp="",curr_weather_desc_1="",location_city="",is_lat_lon_correct=correct_latitude_longitude)
    else:
        secret_api_key = os.getenv("API_KEY")
        custom_url = f"http://api.openweathermap.org/data/2.5/weather?q=Dubai&APPID={secret_api_key}&units=metric"
        response = requests.get(custom_url)
        status = response.status_code
        if status==200:
            response_json = response.json()
            current_temperature = response_json["main"]["temp"]
            feels_like_temperature = response_json["main"]["feels_like"]
            current_temperature_description = response_json["weather"][0]["main"]
            city_name = response_json["name"]
            lat_var = response_json["coord"]["lat"]
            lon_var = response_json["coord"]["lon"]
            is_Country = False
            country_name = ""
            if "country" in response_json["sys"]:
                is_Country = True
                country_name = response_json["sys"]["country"]
            min_temp = response_json["main"]["temp_min"]
            max_temp = response_json["main"]["temp_max"]
            return render_template("weathercast.html", curr_temp=current_temperature,
                                   curr_weather_desc_1=current_temperature_description, location_city=city_name,feels_like_temp=feels_like_temperature,lat_var=lat_var,lon_var=lon_var,
                                   min_temp=min_temp,max_temp=max_temp,is_Country=is_Country,location_country=country_name,is_lat_lon_correct=True)
        else:
            return render_template("weathercast.html",location_city="",is_lat_lon_correct=False)

@app.route('/<anypage>')
def open_any_webpage(anypage):
    return redirect(url_for("index"))

if __name__=="__main__":
    app.run(debug=True)