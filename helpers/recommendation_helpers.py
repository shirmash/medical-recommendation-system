from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for,Blueprint
from pymongo import MongoClient, ReplaceOne
from datetime import datetime, timedelta
from helpers.db_managment_helpers import *
from  helpers.states_managment_helpers import *
from  helpers.time_helpers import  *
from helpers.states_discovery_helpers import *


client = MongoClient('mongodb+srv://shirmash:babik260621@cdssproject.vcmebbk.mongodb.net/?retryWrites=true&w=majority&appName=CDSSproject')
db = client['project_db']
patient_db = db['project_db']
loinc_db = db['loinc']
states_db=db['kb']
recommendations_db = db['recommendations']
rec_bp = Blueprint('rec', __name__)


@rec_bp.route('/add_recommendation', methods=['GET', 'POST'])
def add_recommendation():
    # Predefined sets of options
    genders = ["Male", "Female"]
    hemoglobin_states = [
        "Severe Anemia", "Moderate Anemia", "Mild Anemia",
        "Normal Hemoglobin", "Polycytemia"
    ]
    hematological_states = [
        "Pancytopenia", "Anemia", "Suspected Leukemia",
        "Leukopenia", "Normal", "Leukemoid reaction",
        "Suspected Polycytemia Vera", "Polyhemia"
    ]
    systematic_toxicity_levels = [1, 2, 3, 4]

    if request.method == 'POST':
        gender = request.form.get('gender')
        hemoglobin_state = request.form.get('Hemoglobin_State')
        custom_hemoglobin_state = request.form.get('Custom_Hemoglobin_State')
        hematological_state = request.form.get('Hematological_State')
        custom_hematological_state = request.form.get('Custom_Hematological_State')
        systematic_toxicity = int(request.form.get('Systematic_Toxicity'))
        recommendation = request.form.get('Recommendation')

        # Replace "Other" with the custom value if provided
        if hemoglobin_state == "Other":
            hemoglobin_state = custom_hemoglobin_state

        if hematological_state == "Other":
            hematological_state = custom_hematological_state

        # Check if the combination already exists in the database
        existing_record = recommendations_db.find_one({
            "Gender": gender,
            "Hemoglobin_State": hemoglobin_state,
            "Hematological_State": hematological_state,
            "Systematic_Toxicity": systematic_toxicity
        })

        if existing_record:
            # If it exists, ask the user if they want to replace it
            if 'confirm_replace' in request.form:
                # User confirmed to replace the recommendation
                recommendations_db.update_one(
                    {"_id": existing_record["_id"]},
                    {"$set": {"Recommendation": recommendation}}
                )
                return render_template('add_recommendation.html', genders=genders, hemoglobin_states=hemoglobin_states,
                                       hematological_states=hematological_states, systematic_toxicity_levels=systematic_toxicity_levels,
                                       success=True, message="Recommendation updated successfully.")
            elif 'cancel_replace' in request.form:
                # User chose not to replace the recommendation, return to add page
                return render_template('add_recommendation.html', genders=genders, hemoglobin_states=hemoglobin_states,
                                       hematological_states=hematological_states, systematic_toxicity_levels=systematic_toxicity_levels,
                                       gender=gender, hemoglobin_state=hemoglobin_state,
                                       hematological_state=hematological_state, systematic_toxicity=systematic_toxicity,
                                       recommendation=recommendation)
            else:
                # Ask the user if they want to replace the existing recommendation
                return render_template('add_recommendation.html', genders=genders, hemoglobin_states=hemoglobin_states,
                                       hematological_states=hematological_states, systematic_toxicity_levels=systematic_toxicity_levels,
                                       existing_record=True, existing_recommendation=existing_record["Recommendation"],
                                       gender=gender, hemoglobin_state=hemoglobin_state,
                                       hematological_state=hematological_state, systematic_toxicity=systematic_toxicity,
                                       recommendation=recommendation)
        else:
            # Insert into the database if no existing record is found
            new_recommendation = {
                "Gender": gender,
                "Hemoglobin_State": hemoglobin_state,
                "Hematological_State": hematological_state,
                "Systematic_Toxicity": systematic_toxicity,
                "Recommendation": recommendation
            }
            recommendations_db.insert_one(new_recommendation)

            return render_template('add_recommendation.html', genders=genders, hemoglobin_states=hemoglobin_states,
                                   hematological_states=hematological_states, systematic_toxicity_levels=systematic_toxicity_levels,
                                   success=True, message="Recommendation added successfully.")

    return render_template(
        'add_recommendation.html',
        genders=genders,
        hemoglobin_states=hemoglobin_states,
        hematological_states=hematological_states,
        systematic_toxicity_levels=systematic_toxicity_levels
    )

@rec_bp.route('/delete_recommendation', methods=['GET', 'POST'])
def delete_recommendation():
    if request.method == 'POST':
        selected_ids = request.form.getlist('recommendation_ids')
        confirm_delete = request.form.get('confirm_delete')

        if confirm_delete == 'yes':
            # Delete the selected records from the database
            for recommendation_id in selected_ids:
                recommendations_db.delete_one({"_id": ObjectId(recommendation_id)})
            return render_template('delete_recommendation.html', success=True, message="Selected recommendations deleted successfully.", recommendations=recommendations_db.find())
        else:
            # Return to the delete recommendation page without deleting
            return render_template('delete_recommendation.html', success=False, message="Deletion canceled.", recommendations=recommendations_db.find())

    # Fetch all existing records from the database
    recommendations = list(recommendations_db.find())
    return render_template('delete_recommendation.html', recommendations=recommendations)


@rec_bp.route('/recommendation_query', methods=['POST'])
def abstract_query_function():
    """
    This function handles the recommendation process. It receives the query date and time provided by the user and retrieves the relevant records from the database based on that time.
    The function then evaluates the combined conditions for each patient and returns the most up-to-date recommendation for each.
    :return: For each patient, the function returns the most recent and relevant recommendation, if available.
    """
    query_date = request.form.get('query_date')
    query_time = request.form.get('query_time')
    if not query_time or not query_date:
        return render_template('not_found.html')

    current_datetime = datetime.strptime(f"{query_date}T{query_time}", '%Y-%m-%dT%H:%M')
    # Construct base MongoDB query with date criteria
    # query = {
    #     "Transaction time": {##current time needs to be after transcation time
    #         "$lte": current_datetime}
    # }
    # Calculate the datetime one week before the current datetime
    one_week_ago = current_datetime - timedelta(days=3)

    # Construct MongoDB query with date range criteria
    query = {
        "Transaction time": {
            "$gte": one_week_ago,
            "$lte": current_datetime
        }
    }
    patient_samples = {}
    results = list(patient_db.find(query))
    for result in results:  # Filter results by LOINC-NUM for each patient
        loinc_num = result['LOINC-NUM']
        loinc_record = loinc_db.find_one({"LOINC_NUM": loinc_num})
        if loinc_record:
            if loinc_record["COMPONENT"] in ["Hemoglobin", "WBC", "Temperature", "Chills", "Skin assessment", "Allergies"]:
                result["Component"] = loinc_record["COMPONENT"]
                patient_id = result["First name"] + ' ' + result["Last name"] # Assuming that the patient ID is the combination of first name and last name
                gender = result["Gender"]
                if patient_id not in patient_samples:
                    patient_samples[patient_id] = {"Gender": gender, "Hemoglobin": [], "WBC": [], "Temperature": [], "Chills": [], "Skin assessment": [], "Allergies": []}
                patient_samples[patient_id][loinc_record["COMPONENT"]].append(result)

    result_abstraction = []
    results_for_return = []  #save for each patient is recommendation
    # Evaluate combined conditions for each patient - for each patient save the most updated recommendation
    for patient_id, samples in patient_samples.items():
        disease_result = None
        gender = samples["Gender"]
        hemoglobin_samples = samples.get('Hemoglobin', [])
        wbc_samples = samples.get('WBC', [])
        chills_samples = sorted(samples.get('Chills', []), key=lambda x: x['Valid start time'], reverse=True)
        fever_samples = sorted(samples.get('Temperature', []), key=lambda x: x['Valid start time'], reverse=True)
        skin_look_samples = sorted(samples.get('Skin assessment', []), key=lambda x: x['Valid start time'], reverse=True)
        allergic_state_samples = sorted(samples.get('Allergies', []), key=lambda x: x['Valid start time'], reverse=True)
        if len(hemoglobin_samples) > 0:
            for hemoglobin_sample in hemoglobin_samples:
                hemoglobin_value = hemoglobin_sample['Value']
                hemoglobin_kb_gender_cursor = states_db.find({
                    "ConceptName": "Hemoglobin",
                    "gender": gender,
                    "min_hemoglobin": {"$lte": hemoglobin_value},
                    "max_hemoglobin": {"$gt": hemoglobin_value}
                })
                for hemoglobin_kb_gender in hemoglobin_kb_gender_cursor:  # only one rule anyway but we need deal with the cursor object
                    hemoglobin_sample = deal_with_good_before_and_good_after(hemoglobin_sample, hemoglobin_kb_gender)   ## fix the interval length according to the good before and good after
                    hemoglobin_sample["Value_State"] = hemoglobin_kb_gender["value"]
                    hemoglobin_sample["Concept_Name"] = "Hemoglobin_state"
                    result_abstraction.append(hemoglobin_sample)
            hemoglobin_samples_fixed = find_conflict_intervals(result_abstraction)  ##fix the conflict between two samples and merge samples with the same abstract value if needed
            hemoglobin_samples_fixed.sort(key=lambda x: x['Valid start time before'], reverse=True)
            if (wbc_samples is not None) and (chills_samples is not None) and (fever_samples is not None) and (skin_look_samples is not None) and (allergic_state_samples is not None):  # there is no WBC sample, so we can't evaluate the hematological state
                for wbc_sample in wbc_samples:   ##evaluate the hematological state
                    wbc_value = wbc_sample['Value']
                    start_wbc_sample = parse_datetime(wbc_sample['Valid start time']) - timedelta(hours=36)  ##subtract 36 hours from the wbc sample - good before
                    end_wbc_sample = parse_datetime(wbc_sample['Valid end time']) + timedelta(hours=36) ##add 36 hours to the wbc sample - good after

                    for hemoglobin_sample in hemoglobin_samples_fixed:
                        start_hemoglobin_sample = parse_datetime(hemoglobin_sample['Valid start time before'])
                        end_hemoglobin_sample = parse_datetime(hemoglobin_sample['Valid end time after'])
                        if start_hemoglobin_sample <= end_wbc_sample and start_wbc_sample <= end_hemoglobin_sample:    # לבדוק אם הרשומה של הכדוריות נכנסת בטווח הזמן של ההמוגלובין
                            hemoglobin_value = hemoglobin_sample['Value']

                            # Evaluate hematological state based on the table
                            hematological = states_db.find_one({
                                "ConceptName": "Hematological",
                                "gender": gender,
                                "min_hemoglobin": {"$lte": hemoglobin_value},
                                "max_hemoglobin": {"$gt": hemoglobin_value},
                                "min_wbc": {"$lte": wbc_value},
                                "max_wbc": {"$gt": wbc_value}
                            })
                            # Evaluate systemic toxicity based on the table
                            for i in range(len(fever_samples)):  ## the time of the fever sample is similar to the other parameters. the assumption is that the parameters taken at the same time
                                start_fever_sample = parse_datetime(fever_samples[i]['Valid start time'])
                                end_fever_sample = parse_datetime(fever_samples[i]['Valid end time'])
                                if start_wbc_sample <= start_fever_sample and end_wbc_sample >= end_fever_sample: ##check if the fever sample is in the range of the wbc sample
                                    try:
                                        parameters = {"Fever ": fever_samples[i]['Value'],
                                                      "Chills": chills_samples[i]['Value'],
                                                      "Skin-Look": skin_look_samples[i]['Value'],
                                                      "Allergic-state": allergic_state_samples[i]['Value']}
                                    except IndexError:
                                        break
                                    systemic_toxic_values = []
                                    for concept_name, value in parameters.items():
                                        systemic_toxic_values.append(get_systemic_toxic_value(concept_name, value))
                                    max_grade = max(systemic_toxic_values)  #take the max grade of the systemic toxicity parameters

                                    sample = {"Patient_name": patient_id,
                                              "Gender": gender,
                                              "Hemoglobin_state": hemoglobin_sample["Value_State"],
                                              "Hematological_state": hematological["value"],
                                              "Systemic_toxicity": max_grade}
                                    disease_result = sample
                                    results_for_return.append(disease_result)  ##save the result for the patient and break the loop of the fever samples
                                    break
                        if disease_result is not None:  ##break the loop of the hemoglobin samples
                            break
                    if disease_result is not None:  ##break the loop of the wbc samples in order to continue to the next patient
                        break

    if len(results_for_return) > 0:  ##add the recommendation to the results
        for result in results_for_return:
            recommendation = recommendations_db.find_one({"Gender": result["Gender"], "Hemoglobin_State": result["Hemoglobin_state"], "Hematological_State": result["Hematological_state"], "Systematic_Toxicity": result["Systemic_toxicity"]})
            if recommendation is None:
                result["Recommendation"] = "No recommendation found"
            else:
                result["Recommendation"] = recommendation["Recommendation"]

    if results_for_return:
        return render_template('recommendation_results.html', results=results_for_return)
    else:
        return render_template('not_found.html')