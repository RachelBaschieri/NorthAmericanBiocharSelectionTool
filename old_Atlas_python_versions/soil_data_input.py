from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configure PostgreSQL database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Postgres500!@localhost:5432/practiceAtlas'
db = SQLAlchemy(app)

# Define Crop model
class Crop(db.Model):
    __tablename__ = 'Crop_Fertilizer_Guide'
    Crop = db.Column(db.String(255), unique=True, nullable=False)
    pH_min = db.Column(db.Float)
    pH_max = db.Column(db.Float)
    pH_opt = db.Column(db.Float)
    N_low_rate = db.Column(db.Float)
    N_upper_rate = db.Column(db.Float)
    P_low_rate = db.Column(db.Float)
    P_upper_rate = db.Column(db.Float)
    K_low_rate = db.Column(db.Float)
    K_upper_rate = db.Column(db.Float)
    Lime_low_rate = db.Column(db.Float)
    Lime_upper_rate = db.Column(db.Float)
    Reference = db.Column(db.String(255))
    ID = db.Column(db.Integer, primary_key=True)

    def __repr__(self):
        return f'<Crop {self.Crop}>'
    
@app.route('/select_crop', methods=['GET', 'POST'])

def select_crop():
    if request.method == 'POST':
        selected_crop = request.form['crop']
        crop = Crop.query.filter_by(Crop=selected_crop).first()

        if crop:
            return render_template('crop_data.html', selected_crop=selected_crop, data={
                'pH_min': crop.pH_min
            })
        
        else:
            return render_template('crop_data.html', error="Crop not found.")
    
    # Retrieve crop list from the database
    crops = Crop.query.all()
    return render_template('select_crop.html', crops=crops)


import pandas as pd


@app.route("/", methods=["GET", "POST"])
def index():
    data = None
    messages = {}
    crops = Crop.query.all()

    if request.method == "POST":
        try:
            # Retrieve form data
            soil_moisture = float(request.form.get("moisture", 0))
            organic_matter = float(request.form.get("organic_matter", 0))
            phosphorus = float(request.form.get("phosphorus", 0))
            potassium = float(request.form.get("potassium", 0))
            available_N= float(request.form.get("available_N", 0))
            pH = float(request.form.get("pH", 0))
            sand = float(request.form.get("sand", 0))
            silt = float(request.form.get("silt", 0))
            clay = float(request.form.get("clay", 0))

            # Processing soil moisture value
            if soil_moisture < 10:
                messages['Soil Moisture'] = "The soil is very dry. Consider watering your plants."
            elif 10 <= soil_moisture < 30:
                messages['Soil Moisture'] = "The soil is somewhat dry. Light watering might be needed."
            elif 30 <= soil_moisture < 60:
                messages['Soil Moisture'] = "The soil moisture level is ideal for most plants."
            else:
                messages['Soil Moisture'] = "The soil is too wet. Be cautious of overwatering."

            # Processing organic matter value
            if organic_matter < 2:
                messages['Organic Matter'] = "Organic matter content is low."
            elif 2 <= organic_matter < 10:
                messages['Organic Matter'] = "Organic matter content is adequate, but would still benefit from additions."
            else:
                messages['Organic Matter'] = "Organic matter content is high. Do not add more."

            # Processing Phosphorus
            if phosphorus < 30:
                messages['Phosphorus'] = "Phosphorus content is low."
            else:
                messages['Phosphorus'] = "Phosphorus content is sufficient."

            # Processing Potassium
            if potassium < 80:
                messages['Potassium'] = "Potassium content is low."
            else:
                messages['Potassium'] = "Potassium content is sufficient."

            # Processing Plant avaialble N
            if available_N < 10:
                messages['Plant available Nitrogen (either NH4+/NO3-) (ppm)'] = "Plant available N is low."
            else:
                messages['Plant available Nitrogen (either NH4+/NO3-) (ppm)'] = "Plant available N is sufficient."

            # Processing pH
            if pH < 5.5 and pH > 7:
                messages['pH'] = "Soil pH is in a good range for plant growth."
            else:
                messages['pH'] = "Soil pH is not in a good range for plant growth."


            # Collect all form data
            data = {
                "Soil Moisture (%)": soil_moisture,
                "Organic Matter (%)": organic_matter,
                "Phosphorus (ppm)": phosphorus,
                "Potassium (ppm)": potassium,
                "Plant available Nitrogen (either NH4+/NO3-) (ppm)": available_N,
                "pH": pH,
                "Sand (%)": sand,
                "Silt (%)": silt,
                "Clay (%)": clay
            }

        except ValueError:
            messages['error'] = "Invalid value. Please enter valid numbers for all fields."

    return render_template('index.html', data=data, messages=messages, crops=crops)

if __name__ == "__main__":
    app.run(debug=True)
