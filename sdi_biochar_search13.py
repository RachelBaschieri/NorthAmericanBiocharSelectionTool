from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import asc, func, desc
from geopy.geocoders import Nominatim 
from geopy.distance import geodesic

app = Flask(__name__)
app.secret_key = 'your_secret_key'

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
    
class SA(db.Model):
    __tablename__ = 'Surface Area'
    ID = db.Column(db.Integer, primary_key=True)
    Sample = db.Column(db.String(50), nullable=False)
    SA_mean_m2_g = db.Column(db.Float)
    SA_std = db.Column(db.Float)
    SA_CV = db.Column(db.Float)
    TPV_ave_cm3_g = db.Column(db.Float)
    Average_pore_diameter_nm = db.Column(db.Float)

class HCratio(db.Model):
    __tablename__ = 'H:C ratio'
    ID = db.Column(db.Integer, primary_key=True)
    Sample = db.Column(db.Text, nullable=False)
    H_percent = db.Column(db.Float)
    Corg_percent = db.Column(db.Float)
    HCorg_ratio = db.Column(db.Float)


class Priority(db.Model):
    __tablename__ = 'Priorities'
    ID = db.Column(db.Numeric, primary_key=True)
    priority = db.Column(db.Text)



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

@app.route('/get_crops/<state>', methods=['GET'])
def get_crops(state):
    # Fetch crops for the selected state from the database
    crops = Crop.query.filter_by(State=state).all()
    crop_list = [crop.Crop for crop in crops]
    return jsonify({"crops": crop_list})

@app.route('/analyze_soil_and_biochar', methods=['GET', 'POST'])
def analyze_soil_and_biochar():
    states = [state[0] for state in db.session.query(Crop.State).distinct().order_by(Crop.State.asc()).all()]
    session['states'] = states
    messages = {}
    data = None
    soil_data = {}
    biochar_results = None
    closest_biochars = None
    soil_type = None
    moisture_message = ""
    organic_matter_message = ""
    lime_message = ""
    priority_list = []
    show_priorities_form = False
    
    if request.method == 'POST' and 'zip_code' in request.form:
    # Fetch all unique states from the Crop table
        states = [state[0] for state in db.session.query(Crop.State).distinct().order_by(Crop.State.asc()).all()]
        session['states'] = states
    #Initialize results dictionaries
        messages = {}
        data = None
        soil_data = {}
        biochar_results = None
        closest_biochars = None
        soil_type = None
    # Initialize messages
        moisture_message = ""
        organic_matter_message = ""
        lime_message = ""
# Fetch all priorities from the database
        priorities = Priority.query.all()
    # Extract the priority names into a list
        priority_list = [p.priority for p in priorities]


    
    # Get the form inputs
        selected_state = request.form.get('state')
        selected_crop = request.form.get('crop')
        user_zip = request.form.get('zip_code')
    #store user_zip for later
        session['user_zip'] = user_zip
    # Gather soil data
        sand = float(request.form.get("sand"))
        silt = float(request.form.get("silt"))
        clay = float(request.form.get("clay"))
        user_pH = float(request.form.get("pH"))

        soil_data = {
            "Soil Moisture (%)": request.form.get("moisture"),
            "Organic Matter (%)": request.form.get("organic_matter"),
            "Phosphorus (ppm)": float(request.form.get("phosphorus")),
            "Potassium (ppm)": float(request.form.get("potassium")),
            "Plant available Nitrogen (either NH4+/NO3-) (ppm)": float(request.form.get("available_N")),
            "pH": float(request.form.get("pH")),
            "SMP buffer pH": request.form.get("SMP buffer pH") or "N/A",
            "Sand (%)": float(request.form.get("sand")),
            "Silt (%)": float(request.form.get("silt")),
            "Clay (%)": float(request.form.get("clay"))
        }
        session['soil_data'] = soil_data
        # Soil Moisture statement
        soil_moisture = float(request.form.get("moisture"))
        # Check soil moisture levels and set appropriate messages
        if soil_moisture < 20:
            moisture_message = (
            "Soil moisture is too low for most plants, consider applying biochar "
            "with high surface area to increase water holding capacity."
            )
        elif 20 < soil_moisture < 60:
            moisture_message = (
            "Soil moisture is good for growing most plants."
            )
        elif soil_moisture > 60:
            moisture_message = (
            "Soil moisture is too high for most plants, consider applying biochar "
            "with a high average pore diameter to facilitate drainage."
            )

        #Organic Matter statement
        om = float(request.form.get("organic_matter"))
        if om <= 1:
            organic_matter_message = (
            "Soil organic matter is low."
            )
        elif 1 < om < 3:
            organic_matter_message = (
            "Soil organic matter is average and can be increased by leaving plant residues," 
            "by applying biochar, compost, or other types of organic matter, and by reducing tillage."
            )
        elif 3 < om < 5:
            organic_matter_message = (
            "Soil organic matter is high and can be increased by leaving plant residues,"
             "by applying biochar, compost, or other types of organic matter, and by reducing tillage."
            )
        elif 5 < om < 10:
            organic_matter_message = (
            "Soil organic matter is very high."
            )
        else:
            organic_matter_message = (
            "This is an organic soil and does not need biochar addition."
            )

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
               lime_message = (
                "Soil pH is higher than the maximum for this crop, consider applying elemental sulfur."
               )
            
            # If pH is within range, no lime is needed
            else:
                lime_message = (
                "No lime needed. Your soil pH is within the recommended range for this crop."
                )

            # Fetch top 5 biochar samples based on closest values to nutrient needs
            top_phosphorus = ExtractableP.query.order_by(func.abs(ExtractableP.ExtractablePlbs1ton - phosphorus_needed)).limit(5).all()
            top_potassium = ExtractableNutrients.query.order_by(func.abs(ExtractableNutrients.Klb_1ton - potassium_needed)).limit(5).all()
            top_nitrogen = PlantAvailableN.query.order_by(func.abs(PlantAvailableN.Plant_available_Nlbs_1ton - nitrogen_needed)).limit(5).all()
            top_lime = CaCO3Eq.query.filter(CaCO3Eq.CaCO3lb_1ton > 0).order_by(func.abs(CaCO3Eq.CaCO3lb_1ton - lime_needed)).limit(5).all()
            
            # Store the results in session
            session['top_phosphorus'] = [(p.Sample, p.ExtractablePlbs1ton) for p in top_phosphorus]
            session['top_potassium'] = [(k.Sample, k.Klb_1ton) for k in top_potassium]
            session['top_nitrogen'] = [(n.Sample, n.Plant_available_Nlbs_1ton) for n in top_nitrogen]
            session['top_lime'] = [(l.Sample, l.CaCO3lb_1ton) for l in top_lime]


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
                
                

            else:
                messages = "Unable to find location for the given zip code."

        else:
            messages = "Crop not found."

        # After processing the soil data, display the priorities form
        show_priorities_form = True

        return render_template('sdi_biochar_search13.html', soil_data=soil_data, messages=messages, lime_message=lime_message, crops=states, crop_data=data, biochar_results=biochar_results, biochars=closest_biochars, soil_type = soil_type, moisture_message=moisture_message, organic_matter_message = organic_matter_message, priority_list=priority_list, show_priorities_form=show_priorities_form)

   
    elif request.method == 'POST' and 'priority1' in request.form:
        priority_results = {}
        messages = None
        lime_message = None
        states = session.get('states')
        biochar_results = {}
        soil_type = None
        moisture_message=None
        organic_matter_message = None
        priority_list= {}
        data = {}
        submitted_priorities = {
            'priority1': request.form.get('priority1'),
            'priority2':request.form.get('priority2'),
            'priority3':request.form.get('priority3')
                }
        # Retrieve stored data from the session
        top_phosphorus = session.get('top_phosphorus', [])
        top_potassium = session.get('top_potassium', [])
        top_nitrogen = session.get('top_nitrogen', [])
        top_lime = session.get('top_lime', [])
        user_zip = session.get('user_zip')
        soil_data = session.get('soil_data')
        #closest_biochars = session.get('closest_biochars', [])
        user_lat_lon = get_lat_lon_from_zip(user_zip)
        if user_lat_lon:
                distances = calculate_distances(user_lat_lon)
                closest_biochars = distances[:5]

        # Iterate through the submitted priorities
        for key, p in submitted_priorities.items():
            if p == 'N requirement':
                # Perform the query and append the result to the dictionary
                query_result = top_nitrogen
                columns = ['Sample', 'Plant available N (lbs/ton)']
                priority_results[key] = {'columns': columns, 'data': query_result}
                
            elif p == 'P requirement':
                # Perform the query and append the result to the dictionary
                query_result = top_phosphorus
                columns = ['Sample', 'Plant available P (lbs/ton)']
                priority_results[key] = {'columns': columns, 'data': query_result}

            elif p == 'K requirement':
                # Perform the query and append the result to the dictionary
                query_result = top_potassium
                columns = ['Sample', 'Plant available K (lbs/ton)']
                priority_results[key] = {'columns': columns, 'data': query_result}

            elif p == 'Lime requirement':
                # Perform the query and append the result to the dictionary
                query_result = top_lime
                columns = ['Sample', 'Lime equivalent (lbs/ton)']
                priority_results[key] = {'columns': columns, 'data': query_result}

            elif p == 'Increase soil organic matter':
                # Perform the query and append the result to the dictionary
                pre_query_result = HCratio.query.order_by(desc(HCratio.Corg_percent)).limit(5).all()
                query_result = [(row.Sample, row.Corg_percent) for row in pre_query_result]
                columns = ['Sample', 'Organic C %']
                priority_results[key] = {'columns': columns, 'data': query_result}

            elif p == 'Sequester C':
                pre_query_result = HCratio.query.order_by(desc(HCratio.HCorg_ratio)).limit(5).all()
                query_result = [(row.Sample, row.HCorg_ratio) for row in pre_query_result]
                columns = ['Sample', 'H:Corg ratio']
                priority_results[key] = {'columns': columns, 'data': query_result}

            elif p == 'Increase drainage':
                pre_query_result = SA.query.order_by(desc(SA.Average_pore_diameter_nm)).limit(5).all()
                query_result = [(row.Sample, row.Average_pore_diameter_nm) for row in pre_query_result]
                columns = ['Sample', 'Average pore diameter (nm)']
                priority_results[key] = {'columns': columns, 'data': query_result}

            elif p == 'Increase water retention':
                pre_query_result = SA.query.order_by(desc(SA.SA_mean_m2_g)).limit(5).all()
                query_result = [(row.Sample, row.SA_mean_m2_g) for row in pre_query_result]
                columns = ['Sample', 'Surface area (m2/g)']
                priority_results[key] = {'columns': columns, 'data': query_result}

            else:
                query_result = closest_biochars
                columns = ['Sample', 'Closest Biochar']
                priority_results[key] = {'columns': columns, 'data': query_result}
        print(priority_results)
        return render_template('sdi_biochar_search13.html', priority_results = priority_results, soil_data=soil_data, messages=messages, lime_message=lime_message, crops=states, crop_data=data, biochar_results=biochar_results, soil_type = soil_type, moisture_message=moisture_message, organic_matter_message = organic_matter_message, priority_list=priority_list, submitted_priorities=submitted_priorities, show_priorities_form=False)
    # If GET request or form not submitted
    else:
        priority_results = {}
        messages = None
        lime_message = None
        states = session.get('states')
        biochar_results = {}
        soil_type = None
        moisture_message=None
        organic_matter_message = None
        priority_list={}
        soil_data = {}
        data = {}
        closest_biochars = {}
        return render_template('sdi_biochar_search13.html', priority_results=priority_results, soil_data=soil_data, messages=messages, lime_message=lime_message, crops=states, crop_data=data, biochar_results=biochar_results, biochars=closest_biochars, soil_type = soil_type, moisture_message=moisture_message, organic_matter_message = organic_matter_message, priority_list=priority_list, show_priorities_form=False)
if __name__ == "__main__":
    app.run(debug=True, port=5001)





















