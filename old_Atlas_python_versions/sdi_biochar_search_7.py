from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import asc, func
from geopy.geocoders import Nominatim 
from geopy.distance import geodesic

app = Flask(__name__)


@app.route('/')
def index():
    return redirect(url_for('analyze_soil_and_biochar'))


# Configure PostgreSQL database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Postgres500!@localhost:5432/practiceAtlas'
db = SQLAlchemy(app)

# Define Crop model
class Crop(db.Model):
    __tablename__ = 'Crop Nutrients USA'
    Num = db.Column(db.Numeric, primary_key=True)
    State = db.Column(db.Text)
    Crop = db.Column(db.Text)
    pH_min = db.Column(db.Numeric)
    pH_max = db.Column(db.Numeric)
    N_upper_rate = db.Column(db.Numeric)
    P_upper_rate = db.Column(db.Numeric)
    K_upper_rate = db.Column(db.Numeric)
    Reference = db.Column(db.Text)
   

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

class Biochar(db.Model):
    __tablename__ = 'Sample_addresses'
    ID = db.Column(db.Integer, primary_key=True)
    Sample = db.Column(db.String(50), nullable=False)
    Address = db.Column(db.String(50), nullable=False)
    City = db.Column(db.String(50), nullable=False)
    State = db.Column(db.String(50), nullable=False)
    Zip_Code = db.Column(db.String(10), nullable=False)  
    Latitude = db.Column(db.Float)
    Longitude = db.Column(db.Float)

# Function to classify soil based on sand, silt, and clay percentages
def classify_soil(sand, silt, clay):
    total = sand + silt + clay
    if total != 100:
        return "Invalid soil composition, percentages do not add up to 100."

    if clay >= 40 and silt >= 40:
        return "Silty Clay"
    elif clay >= 40 and sand >= 45:
        return "Sandy Clay"
    elif clay >= 40:
        return "Clay"
    elif clay >= 27 and clay < 40 and silt >= 28 and silt < 40:
        return "Clay Loam"
    elif clay >= 27 and clay < 40 and sand >= 20 and sand < 45:
        return "Sandy Clay Loam"
    elif clay >= 20 and clay < 27 and sand >= 50 and sand < 80:
        return "Sandy Loam"
    elif clay >= 20 and clay < 27 and silt >= 28:
        return "Loam"
    elif silt >= 50 and clay < 12:
        return "Silt"
    elif silt >= 50:
        return "Silt Loam"
    elif silt >= 28 and clay >= 7 and clay < 20:
        return "Loam"
    elif sand >= 70:
        return "Sand"
    elif sand >= 52 and silt >= 12 and silt < 28:
        return "Loamy Sand"
    else:
        return "Unclassified"

# Function to get latitude and longitude of the user's zip code
def get_lat_lon_from_zip(zip_code):
    geolocator = Nominatim(user_agent="sdi_biochar_search_location3.py (rachel.baschieri@usda.gov)")
    location = geolocator.geocode(zip_code)
    if location:
        return (location.latitude, location.longitude)
    return None 

# Function to calculate distances
def calculate_distances(user_lat_lon):
    biochar_locations = Biochar.query.all()
    distances = []
    
    for biochar in biochar_locations:
        biochar_lat_lon = (biochar.Latitude, biochar.Longitude)
        distance = geodesic(user_lat_lon, biochar_lat_lon).miles  # Calculate distance in miles
        distances.append((biochar, distance))
    
    distances.sort(key=lambda x: x[1])  # Sort biochar locations by distance (ascending)
    return distances


@app.route('/analyze_soil_and_biochar', methods=['GET', 'POST'])
def analyze_soil_and_biochar():
    # Fetch all unique states from the Crop table
    states = db.session.query(Crop.State).distinct().order_by(Crop.State.asc()).all()
    crops = [state[0] for state in states]  # Flatten list of tuples
    
    messages = {}
    data = None
    soil_data = {}
    biochar_results = None
    closest_biochars = None
    soil_type = None

    if request.method == 'POST':
        # Get the form inputs
        selected_state = request.form['state']
        selected_crop = request.form['crop']
        user_zip = request.form.get('zip_code')

        # Gather soil data
        sand = float(request.form.get("sand"))
        silt = float(request.form.get("silt"))
        clay = float(request.form.get("clay"))
        user_pH = float(request.form.get("pH"))

        soil_data = {
            "Soil Moisture (%)": request.form.get("moisture"),
            "Organic Matter (%)": request.form.get("organic_matter"),
            "Phosphorus (ppm)": request.form.get("phosphorus"),
            "Potassium (ppm)": request.form.get("potassium"),
            "Plant available Nitrogen (either NH4+/NO3-) (ppm)": request.form.get("available_N"),
            "pH": request.form.get("pH"),
            "SMP buffer pH": request.form.get("SMP buffer pH") or "N/A",
            "Sand (%)": request.form.get("sand"),
            "Silt (%)": request.form.get("silt"),
            "Clay (%)": request.form.get("clay")
        }

        # Classify soil type
        soil_type = classify_soil(sand, silt, clay)
    

        # Fetch selected crop details
        crop = Crop.query.filter_by(State=selected_state, Crop=selected_crop).first()

        if crop:
            # Calculate nutrient needs
            phosphorus_needed = max(0, float(crop.P_upper_rate) - (float(soil_data["Phosphorus (ppm)"]) * 2.2913))
            potassium_needed = max(0, float(crop.K_upper_rate) - (float(soil_data["Potassium (ppm)"]) * 1.2046))
            nitrogen_needed = max(0, float(crop.N_upper_rate) - (float(soil_data["Plant available Nitrogen (either NH4+/NO3-) (ppm)"]) * 2))
            lime_needed = 0
            #lime requirement calculation
            texture_factors = {
                "sandy loam": 3,
                "sand": 2,
            }

            soil_texture_factor = texture_factors.get(soil_type.lower(), 4)

             # Check if the user's pH is lower than pH_min
            if user_pH < float(crop.pH_min):
                almost_lime_needed = (float(crop.pH_min) - user_pH) * soil_texture_factor
                lime_needed = (almost_lime_needed * 2204.62)/2.47105

            # Check if the user's pH is higher than pH_max
            elif user_pH > float(crop.pH_max):
                messages['lime_requirement'] = "Soil pH is higher than the maximum for this crop, consider applying elemental sulfur."
            
            # If pH is within range, no lime is needed
            else:
                messages['lime_requirement'] = "No lime needed. Your soil pH is within the recommended range for this crop."


            # Fetch top 5 biochar samples based on closest values to nutrient needs
            top_phosphorus = ExtractableP.query.order_by(func.abs(ExtractableP.ExtractablePlbs1ton - phosphorus_needed)).limit(5).all()
            top_potassium = ExtractableNutrients.query.order_by(func.abs(ExtractableNutrients.Klb_1ton - potassium_needed)).limit(5).all()
            top_nitrogen = PlantAvailableN.query.order_by(func.abs(PlantAvailableN.Plant_available_Nlbs_1ton - nitrogen_needed)).limit(5).all()
            top_lime = CaCO3Eq.query.filter(CaCO3Eq.CaCO3lb_1ton > 0).order_by(func.abs(CaCO3Eq.CaCO3lb_1ton - lime_needed)).limit(5).all()



            # Compile biochar results for rendering
            biochar_results = {
                "phosphorus": top_phosphorus,
                "potassium": top_potassium,
                "nitrogen": top_nitrogen,
                "lime": top_lime
            }

            # Compile the required nutrient amounts for rendering
            data = {
                "Crop": selected_crop,
                "Required Phosphorus (lbs/acre)": phosphorus_needed,
                "Required Potassium (lbs/acre)": potassium_needed,
                "Required Nitrogen (lbs/acre)": nitrogen_needed,
            }

            if lime_needed > 0:
                data["Required Lime (lbs/acre)"] = lime_needed
        
             # Zip Code to Biochar Location Distance Calculation
            user_lat_lon = get_lat_lon_from_zip(user_zip)
            if user_lat_lon:
                distances = calculate_distances(user_lat_lon)
                closest_biochars = distances[:5]  # Get the top 5 closest biochars
                print("Closest biochars:" , closest_biochars) #debug output
                print("User lattitude and longitude:", user_lat_lon)
                print("Distances are:", distances)
            else:
                messages['error'] = "Unable to find location for the given zip code."

        else:
            messages['error'] = "Crop not found."

    return render_template('sdi_search_6.html', soil_data=soil_data, messages=messages, crops=states, crop_data=data, biochar_results=biochar_results, biochars=closest_biochars, soil_type = soil_type)

@app.route('/get_crops/<state>', methods=['GET'])
def get_crops(state):
    # Fetch crops for the selected state from the database
    crops = Crop.query.filter_by(State=state).all()
    crop_list = [crop.Crop for crop in crops]
    return jsonify({"crops": crop_list})

if __name__ == "__main__":
    app.run(debug=True)