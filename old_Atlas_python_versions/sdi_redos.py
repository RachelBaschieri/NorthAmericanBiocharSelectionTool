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
    crops = Crop.query.all()
    messages = {}

    #initialize data to None
    data = None
    soil_data = {}

    if request.method == 'POST':
        selected_crop = request.form['crop']

        soil_data = {
            "Soil Moisture (%)": request.form.get("moisture"),
            "Organic Matter (%)": request.form.get("organic_matter"),
            "Phosphorus (ppm)": request.form.get("phosphorus"),
            "Potassium (ppm)": request.form.get("potassium"),
            "Plant available Nitrogen (either NH4+/NO3-) (ppm)": request.form.get("available_N"),
            "pH": request.form.get("pH"),
            "Sand (%)": request.form.get("sand"),
            "Silt (%)": request.form.get("silt"),
            "Clay (%)": request.form.get("clay")
        }

        crop = Crop.query.filter_by(Crop=selected_crop).first()

        if crop:
            # Calculate how much more nutrients are needed based on crop requirements
            phosphorus_needed = max(0, crop.P_low_rate - (float(soil_data["Phosphorus (ppm)"]) * 2.2913))
            potassium_needed = max(0, crop.K_low_rate - (float(soil_data["Potassium (ppm)"]) * 1.2046))
            nitrogen_needed = max(0, crop.N_low_rate - (float(soil_data["Plant available Nitrogen (either NH4+/NO3-) (ppm)"]) * 2))
            lime_needed = 0
            if float(soil_data["pH"]) < crop.pH_min:
                lime_needed = crop.Lime_low_rate
            
            # Display the required nutrient amounts to the user
            data = {
                "Crop": selected_crop,
                "Required Phosphorus (lbs/acre)": phosphorus_needed,
                "Required Potassium (lbs/acre)": potassium_needed,
                "Required Nitrogen (lbs/acre)": nitrogen_needed,
            }

            if lime_needed > 0:
                data["Required Lime (lbs/acre)"] = lime_needed

        else:
            messages['error'] = "Crop not found."
        
    return render_template('sdi_redos_index.html', data=soil_data, messages=messages, crops=crops, crop_data=data)


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
                messages['Soil Moisture'] = "The soil is very dry. Consider biochar that will increase the soil's water holding capacity."
            elif 10 <= soil_moisture < 30:
                messages['Soil Moisture'] = "The soil is somewhat dry."
            elif 30 <= soil_moisture < 60:
                messages['Soil Moisture'] = "The soil moisture level is ideal for most plants."
            else:
                messages['Soil Moisture'] = "The soil is too wet. Consider biochar that will increase drainage."

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
            if pH > 5.5 and pH <= 7:
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

    return render_template('sdi_redos_index.html', data=data, messages=messages, crops=crops)

if __name__ == "__main__":
    app.run(debug=True)