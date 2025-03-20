from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import asc, func

app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('select_crop'))


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

# Define Biochar models
class ExtractableP(db.Model):
    __tablename__ = 'Extractable P'
    ID = db.Column(db.Integer, primary_key=True)
    Sample = db.Column(db.String(255), unique=True, nullable=False)
    Extractable_P_mean = db.Column(db.Float)
    Extractable_P_std = db.Column(db.Float)
    ExtractablePlbs1ton = db.Column(db.Float)

class ExtractableNutrients(db.Model):
    __tablename__ = 'Extractable Nutrients'
    ID = db.Column(db.Integer, primary_key=True)
    Sample = db.Column(db.String(255), unique=True, nullable=False)
    Na_ave = db.Column(db.Float)
    Na_std = db.Column(db.Float)
    Nalb_1ton = db.Column(db.Float)
    K_ave = db.Column(db.Float)
    K_std = db.Column(db.Float)
    Klb_1ton = db.Column(db.Float)
    Mg_ave = db.Column(db.Float)
    Mg_std = db.Column(db.Float)
    Mglb_1ton = db.Column(db.Float)
    Ca_ave = db.Column(db.Float)
    Ca_std = db.Column(db.Float)
    Calb_1ton = db.Column(db.Float)
    S_ave = db.Column(db.Float)
    S_std = db.Column(db.Float)
    Slb_1ton = db.Column(db.Float)

class PlantAvailableN(db.Model):
    __tablename__ = 'Plant Available N'
    ID = db.Column(db.Integer, primary_key=True)
    Sample = db.Column(db.String(255), unique=True, nullable=False)
    reported_NH4_mean = db.Column(db.Float)
    reported_NH4_std = db.Column(db.Float)
    reported_NO3_mean = db.Column(db.Float)
    reported_NO3_std = db.Column(db.Float)
    Plant_available_N = db.Column(db.Float)
    Plant_available_Nlbs_1ton = db.Column(db.Float)

class CaCO3Eq(db.Model):
    __tablename__ = 'CaCO3-eq'
    ID = db.Column(db.Integer, primary_key=True)
    Sample = db.Column(db.String(255), unique=True, nullable=False)
    CaCO3eq_mean = db.Column(db.Float)
    CaCO3eq_STD = db.Column(db.Float)
    CaCO3lb_1ton = db.Column(db.Float)



@app.route('/select_crop', methods=['GET', 'POST'])
def select_crop():
    crops = Crop.query.all()
    messages = {}
    data = None
    soil_data = {}
    biochar_results = None

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
            # Calculate nutrient needs
            phosphorus_needed = max(0, crop.P_low_rate - (float(soil_data["Phosphorus (ppm)"]) * 2.2913))
            potassium_needed = max(0, crop.K_low_rate - (float(soil_data["Potassium (ppm)"]) * 1.2046))
            nitrogen_needed = max(0, crop.N_low_rate - (float(soil_data["Plant available Nitrogen (either NH4+/NO3-) (ppm)"]) * 2))
            lime_needed = 0
            if float(soil_data["pH"]) < crop.pH_min:
                lime_needed = crop.Lime_low_rate

            # Fetch top 5 biochar samples based on closest values to nutrient needs
            top_phosphorus = ExtractableP.query.order_by(func.abs(ExtractableP.ExtractablePlbs1ton - phosphorus_needed)).limit(5).all()
            top_potassium = ExtractableNutrients.query.order_by(func.abs(ExtractableNutrients.Klb_1ton - potassium_needed)).limit(5).all()
            top_nitrogen = PlantAvailableN.query.order_by(func.abs(PlantAvailableN.Plant_available_Nlbs_1ton - nitrogen_needed)).limit(5).all()
            top_lime = CaCO3Eq.query.filter(CaCO3Eq.CaCO3lb_1ton > 0).order_by(func.abs(CaCO3Eq.CaCO3lb_1ton - lime_needed)).limit(5).all()



            # Compile the data for rendering
            biochar_results = {
                "phosphorus": top_phosphorus,
                "potassium": top_potassium,
                "nitrogen": top_nitrogen,
                "lime": top_lime
            }

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

    return render_template('sdi_biochar_search1.html', data=soil_data, messages=messages, crops=crops, crop_data=data, biochar_results=biochar_results)


if __name__ == "__main__":
    app.run(debug=True)

