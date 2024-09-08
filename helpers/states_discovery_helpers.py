from collections import defaultdict

from flask import Blueprint, render_template, request
from pymongo import MongoClient

from helpers.recommendation_helpers import *
from  helpers.states_managment_helpers import *
from  helpers.time_helpers import  *
from helpers.db_managment_helpers import *

states_d_bp = Blueprint('state_d', __name__)
client = MongoClient('mongodb+srv://shirmash:babik260621@cdssproject.vcmebbk.mongodb.net/?retryWrites=true&w=majority&appName=CDSSproject')
db = client['project_db']
patient_db = db['project_db']
loinc_db = db['loinc']
states_db=db['kb']
recommendations_db = db['recommendations']

def Systemic_toxicity(patient_samples):
    """
    This function evaluates the systemic toxicity state for the patient based on the KB rules.
    :param patient_samples: patient records
    :return: systemic toxicity state for the patient
    """
    # Aggregating samples by component
    component_samples = defaultdict(list)
    for sample in patient_samples:
        component = sample["Component"]
        if component in ["Chills", "Temperature", "Skin assessment", "Allergies"]:
            component_samples[component].append(sample)

    # Sort samples by 'Valid start time' within each component
    for component in component_samples:
        component_samples[component].sort(key=lambda x: x['Valid start time'])

    result_abstraction = []


    for i in range(len(component_samples["Temperature"])):
            try:
                parameters = {"Fever ": component_samples["Temperature"][i]['Value'],
                              "Chills": component_samples["Chills"][i]['Value'],
                              "Skin-Look": component_samples["Skin assessment"][i]['Value'],
                              "Allergic-state": component_samples["Allergies"][i]['Value']}
            except IndexError:
                break
            systemic_toxic_values = []
            for concept_name, value in parameters.items():
                systemic_toxic_values.append(get_systemic_toxic_value( concept_name, value))
            max_grade = max(systemic_toxic_values)  # take the max grade of the systemic toxicity parameters
            sample = {"Patient_name": component_samples["Temperature"][i]['First name'] + ' ' + component_samples["Temperature"][i]['Last name'],
                      "Concept_Name": "Systemic_toxicity",
                      "Valid Start Time": component_samples["Temperature"][i]['Valid start time'],
                      "Valid End Time": component_samples["Temperature"][i]['Valid end time'],
                      "Value_State": max_grade}

            result_abstraction.append(sample)
    return result_abstraction



def get_systemic_toxic_value(concept_name, value):  ##get the systemic toxic value from the kb - helper function
    if concept_name == "Fever ":
        concept_name = "Fever"
        query = {
            "ConceptName": concept_name,
            'min': {"$lte": value},
            'max': {"$gt": value}
        }
        query_result = states_db.find_one(query)
    else:
        query_result = states_db.find_one({"ConceptName": concept_name, "Value": value})

    if query_result:
        return query_result["Output_value"]
    return None

def hemoglobin(patient_samples, gender):
    result_abstraction = []
    for hemoglobin_sample in patient_samples:
        hemoglobin_value = hemoglobin_sample['Value']
        hemoglobin_kb_gender_cursor = states_db.find({
            "ConceptName": "Hemoglobin",
            "gender": gender,
            "min_hemoglobin": {"$lte": hemoglobin_value},
            "max_hemoglobin": {"$gt": hemoglobin_value}
        })
        for hemoglobin_kb_gender in hemoglobin_kb_gender_cursor:
            sample = deal_with_good_before_and_good_after(hemoglobin_sample, hemoglobin_kb_gender)
            sample["Value_State"] = hemoglobin_kb_gender["value"]
            sample["Concept_Name"] = "Hemoglobin_state"
            result_abstraction.append(sample)

    hemoglobin_samples = find_conflict_intervals(result_abstraction)
    return hemoglobin_samples


def hematological(patient_samples, gender):
    result_abstraction = []
    hemoglobin_samples = []
    wbc_samples = []

    for sample in patient_samples:
        if sample["Component"] == "Hemoglobin":
            hemoglobin_samples.append(sample)
        elif sample["Component"] == "WBC":
            wbc_samples.append(sample)

    hemoglobin_abstractions = hemoglobin(hemoglobin_samples, gender)
    for wbc_sample in wbc_samples:
        wbc_value = wbc_sample['Value']
        start_wbc_sample = parse_datetime(wbc_sample['Valid start time']) - timedelta(hours=36)
        end_wbc_sample = parse_datetime(wbc_sample['Valid end time']) + timedelta(hours=36)

        for hemoglobin_sample in hemoglobin_abstractions:
            start_hemoglobin_sample = parse_datetime(hemoglobin_sample['Valid start time before'])
            end_hemoglobin_sample = parse_datetime(hemoglobin_sample['Valid end time after'])

            if start_hemoglobin_sample <= end_wbc_sample and start_wbc_sample <= end_hemoglobin_sample:
                hemoglobin_value = hemoglobin_sample['Value']

                hematological = states_db.find_one({
                    "ConceptName": "Hematological",
                    "gender": gender,
                    "min_hemoglobin": {"$lte": hemoglobin_value},
                    "max_hemoglobin": {"$gt": hemoglobin_value},
                    "min_wbc": {"$lte": wbc_value},
                    "max_wbc": {"$gt": wbc_value}
                })
                hematological_state = hematological["value"]

                start_time = max(start_wbc_sample, start_hemoglobin_sample)
                end_time = min(end_wbc_sample, end_hemoglobin_sample)

                sample = {
                    "Patient_name": f"{hemoglobin_sample['First name']} {hemoglobin_sample['Last name']}",
                    "Concept_Name": "Hematological_state",
                    "Valid start time before": format_datetime(start_time),
                    "Valid end time after": format_datetime(end_time),
                    "Value_State": hematological_state
                }
                result_abstraction.append(sample)
                break

    # Apply find_conflict_intervals to resolve conflicts and merge intervals
    samples = find_conflict_intervals(result_abstraction)

    return samples


def find_conflict_intervals(samples):
    if not samples:
        return []

    # Convert string dates to datetime objects
    for sample in samples:
        sample['Valid start time before'] = parse_datetime(sample['Valid start time before'])
        sample['Valid end time after'] = parse_datetime(sample['Valid end time after'])

    # Sort samples by start time
    samples.sort(key=lambda x: x['Valid start time before'])

    merged_samples = []
    current_sample = samples[0]

    for next_sample in samples[1:]:
        if current_sample['Valid end time after'] > next_sample['Valid start time before']:
            # There's an overlap
            if current_sample['Value_State'] == next_sample['Value_State']:
                # Merge samples with the same state
                current_sample['Valid end time after'] = max(current_sample['Valid end time after'],
                                                             next_sample['Valid end time after'])
            else:
                # Different states, distribute the overlap proportionally
                overlap = (current_sample['Valid end time after'] - next_sample[
                    'Valid start time before']).total_seconds()
                total_duration = (current_sample['Valid end time after'] - current_sample[
                    'Valid start time before']).total_seconds() + \
                                 (next_sample['Valid end time after'] - next_sample[
                                     'Valid start time before']).total_seconds()

                if total_duration > 0:
                    proportion = overlap / total_duration
                    new_boundary = next_sample['Valid start time before'] + timedelta(seconds=overlap * proportion)

                    current_sample['Valid end time after'] = new_boundary
                    merged_samples.append(current_sample)

                    next_sample['Valid start time before'] = new_boundary
                    current_sample = next_sample
                else:
                    # If total duration is 0, just use the midpoint
                    new_boundary = next_sample['Valid start time before'] + (
                                current_sample['Valid end time after'] - next_sample['Valid start time before']) / 2
                    current_sample['Valid end time after'] = new_boundary
                    merged_samples.append(current_sample)
                    next_sample['Valid start time before'] = new_boundary
                    current_sample = next_sample
        else:
            # No overlap, add the current sample and move to the next
            merged_samples.append(current_sample)
            current_sample = next_sample

    # Add the last sample
    merged_samples.append(current_sample)

    # Format datetime objects back to strings
    for sample in merged_samples:
        sample['Valid start time before'] = format_datetime(sample['Valid start time before'])
        sample['Valid end time after'] = format_datetime(sample['Valid end time after'])

    return merged_samples

@states_d_bp.route('/states_query', methods=['POST'])
def states_function():
    """
    This function manages the state query process. It receives the patient name and test type provided by the user and retrieves the relevant records from the DB.
    The function then evaluates the records and returns the summarized states for the patient, both for the specific test and across all records.
    """
    patient_name = request.form.get('patient')
    test = request.form.get('test')
    patient_name = patient_name.split(' ')

    query = {  ##query for searching the patient records
        "First name": patient_name[0],
        "Last name": patient_name[1]
    }
    gender = None
    patient_samples = list(patient_db.find(query))
    patient_test_samples = []   #the patient samples for the specific test
    for result in patient_samples:  # Filter records by LOINC-NUM for the patient
        gender = result["Gender"]
        loinc_num = result['LOINC-NUM']
        loinc_record = loinc_db.find_one({"LOINC_NUM": loinc_num})
        if loinc_record:
            if test == 'Hematological':
                if loinc_record["COMPONENT"] in ["Hemoglobin", "WBC"]:
                    result["Component"] = loinc_record["COMPONENT"]
                    patient_test_samples.append(result)
            elif test == 'Systemic_Toxicity':
                if loinc_record["COMPONENT"] in ["Temperature", "Chills", "Skin assessment", "Allergies"]:
                    result["Component"] = loinc_record["COMPONENT"]
                    patient_test_samples.append(result)
            elif test == 'Hemoglobin':
                result["Component"] = loinc_record["COMPONENT"]
                patient_test_samples.append(result)
    final_results = []  #save the results for the output
    if test == 'Hemoglobin':  ##evaluate the hemoglobin state (using good before and good after)
        abstractions = hemoglobin(patient_test_samples, gender)
        for result in abstractions:
            sample = {"Patient_name": patient_name[0] + ' ' + patient_name[1],
                      "Concept_Name": result["Concept_Name"],
                      "Valid Start Time": result["Valid start time before"],
                      "Valid End Time": result["Valid end time after"],
                      "Value": result["Value_State"]}
            final_results.append(sample)
        return render_template('states_results.html', results=final_results, patient_name=patient_name[0] + ' ' + patient_name[1])

    elif test == 'Hematological':  ##evaluate the hematological state
        abstractions = hematological(patient_test_samples, gender)
        for result in abstractions:
            sample = {"Patient_name": patient_name[0] + ' ' + patient_name[1],
                      "Concept_Name": result["Concept_Name"],
                      "Valid Start Time": result["Valid start time before"],
                      "Valid End Time": result["Valid end time after"],
                      "Value": result["Value_State"]}
            final_results.append(sample)
        return render_template('states_results.html', results=final_results, patient_name=patient_name[0] + ' ' + patient_name[1])
    else:  ##evaluate the systemic toxicity state
        abstractions = Systemic_toxicity(patient_test_samples)

    for result in abstractions:
        sample = {"Patient_name": patient_name[0] + ' ' + patient_name[1],
                  "Concept_Name": result["Concept_Name"],
                  "Valid Start Time": result["Valid Start Time"],
                  "Valid End Time": result["Valid End Time"],
                  "Value": result["Value_State"]}
        final_results.append(sample)
    final_results.sort(key=lambda x: x['Valid Start Time'])  ##sort the results by the start time

    return render_template('states_results.html', results=final_results, patient_name=patient_name[0] + ' ' + patient_name[1])


