from pymongo import MongoClient
from flask import Blueprint, request, render_template
from helpers.recommendation_helpers import *
from  helpers.db_managment_helpers import *
from  helpers.time_helpers import  *
from helpers.states_discovery_helpers import *
import copy
# MongoDB connection
client = MongoClient('mongodb+srv://shirmash:babik260621@cdssproject.vcmebbk.mongodb.net/?retryWrites=true&w=majority&appName=CDSSproject')
db = client['project_db']
patient_db = db['project_db']
loinc_db = db['loinc']
states_db=db['kb']
recommendations_db = db['recommendations']
states_m_bp = Blueprint('states_m', __name__)

@states_m_bp.route('/edit_hematological/<gender>/<variable>', methods=['GET', 'POST'])
def edit_hematological(gender, variable):
    # Fetch unique intervals for the selected variable and gender
    hematological_records = list(states_db.aggregate([
        {"$match": {"ConceptName": "Hematological", "gender": gender}},
        {"$group": {
            "_id": {
                "min_value": f"$min_{variable}",
                "max_value": f"$max_{variable}"
            },
            "min_value": {"$first": f"$min_{variable}"},
            "max_value": {"$first": f"$max_{variable}"},
        }},
        {"$sort": {"min_value": 1}}
    ]))

    if request.method == 'POST':
        min_values = request.form.getlist(f'min_{variable}')
        max_values = request.form.getlist(f'max_{variable}')

        # Convert inputs to integers
        min_values = [int(value) for value in min_values]
        max_values = [int(value) for value in max_values]

        # Validate intervals: max of one state must equal min of the next state
        valid_intervals = True
        for i in range(len(min_values) - 1):
            if max_values[i] != min_values[i + 1]:
                valid_intervals = False
                break

        if valid_intervals:
            # Update all records matching the current intervals
            for i in range(len(min_values)):
                states_db.update_many(
                    {
                        "ConceptName": "Hematological",
                        "gender": gender,
                        f"min_{variable}": hematological_records[i]['min_value'],
                        f"max_{variable}": hematological_records[i]['max_value']
                    },
                    {"$set": {
                        f"min_{variable}": min_values[i],
                        f"max_{variable}": max_values[i],
                    }}
                )

            updated_records = list(states_db.aggregate([
                {"$match": {"ConceptName": "Hematological", "gender": gender}},
                {"$group": {
                    "_id": {
                        "min_value": f"$min_{variable}",
                        "max_value": f"$max_{variable}"
                    },
                    "min_value": {"$first": f"$min_{variable}"},
                    "max_value": {"$first": f"$max_{variable}"},
                }},
                {"$sort": {"min_value": 1}}
            ]))
            return render_template('edit_hematological.html', records=updated_records, gender=gender, variable=variable,
                                   success=True)
        else:
            return render_template('edit_hematological.html', records=hematological_records, gender=gender,
                                   variable=variable, error=True)

    return render_template('edit_hematological.html', records=hematological_records, gender=gender, variable=variable)
@states_m_bp.route('/edit_hemoglobin/<gender>', methods=['GET', 'POST'])
def edit_hemoglobin(gender):
    hemoglobin_records = list(states_db.find({"ConceptName": "Hemoglobin", "gender": gender}).sort("min_hemoglobin"))
    if request.method == 'POST':
        min_values = request.form.getlist('min_hemoglobin')
        max_values = request.form.getlist('max_hemoglobin')
        # Convert inputs to integers
        min_values = [int(value) for value in min_values]
        max_values = [int(value) for value in max_values]
        # Validate intervals: max_hemoglobin of one state must equal min_hemoglobin of the next state
        valid_intervals = True
        for i in range(len(min_values) - 1):
            if max_values[i] != min_values[i + 1]:
                valid_intervals = False
                break

        if valid_intervals:
            # Update the database with the new values
            for i, record in enumerate(hemoglobin_records):
                states_db.update_one(
                    {"_id": record['_id']},
                    {"$set": {
                        "min_hemoglobin": min_values[i],
                        "max_hemoglobin": max_values[i],
                    }}
                )
            # Fetch updated records to display the success message and updated data
            updated_records = list(
                states_db.find({"ConceptName": "Hemoglobin", "gender": gender}).sort("min_hemoglobin"))
            return render_template('edit_hemoglobin.html', records=updated_records, gender=gender, success=True)
        else:
            return render_template('edit_hemoglobin.html', records=hemoglobin_records, gender=gender, error=True)

    return render_template('edit_hemoglobin.html', records=hemoglobin_records, gender=gender)

@states_m_bp.route('/edit_fever', methods=['GET', 'POST'])
def edit_fever():
    # Fetch unique intervals for Fever and order them by Output_value
    fever_records = list(states_db.aggregate([
        {"$match": {"ConceptName": "Fever"}},
        {"$group": {
            "_id": {
                "min_value": "$min",
                "max_value": "$max",
                "Output_value": "$Output_value"
            },
            "min_value": {"$first": "$min"},
            "max_value": {"$first": "$max"},
            "Output_value": {"$first": "$Output_value"}
        }},
        {"$sort": {"Output_value": 1}}  # Sort by Output_value indicating severity
    ]))

    if request.method == 'POST':
        min_values = request.form.getlist('min_value')
        max_values = request.form.getlist('max_value')
        output_values = request.form.getlist('Output_value')

        # Convert inputs to appropriate types
        min_values = [float(value) for value in min_values]
        max_values = [float(value) for value in max_values]
        output_values = [int(value) for value in output_values]

        # Validate intervals: Ensure no gaps or overlaps
        valid_intervals = True

        # Sort the intervals by min_value to check for gaps/overlaps
        intervals = sorted(zip(min_values, max_values, output_values), key=lambda x: x[0])

        for i in range(len(intervals) - 1):
            current_max = intervals[i][1]
            next_min = intervals[i + 1][0]

            # There should be no gap or overlap between current max and next min
            if current_max > next_min or current_max < next_min:
                valid_intervals = False
                break

        if valid_intervals:
            # Update all records matching the current intervals
            for i in range(len(min_values)):
                states_db.update_many(
                    {
                        "ConceptName": "Fever",
                        "min": fever_records[i]['min_value'],
                        "max": fever_records[i]['max_value'],
                        "Output_value": fever_records[i]['Output_value']
                    },
                    {"$set": {
                        "min": min_values[i],
                        "max": max_values[i],
                        "Output_value": output_values[i]
                    }}
                )

            updated_records = list(states_db.aggregate([
                {"$match": {"ConceptName": "Fever"}},
                {"$group": {
                    "_id": {
                        "min_value": "$min",
                        "max_value": "$max",
                        "Output_value": "$Output_value"
                    },
                    "min_value": {"$first": "$min"},
                    "max_value": {"$first": "$max"},
                    "Output_value": {"$first": "$Output_value"}
                }},
                {"$sort": {"Output_value": 1}}  # Sort by Output_value indicating severity
            ]))
            return render_template('edit_fever.html', records=updated_records, success=True)
        else:
            return render_template('edit_fever.html', records=fever_records, error=True)

    return render_template('edit_fever.html', records=fever_records)

@states_m_bp.route('/edit_chills', methods=['GET', 'POST'])
def edit_chills():
    # Fetch unique records for Chills and order them by Output_value
    chills_records = list(states_db.aggregate([
        {"$match": {"ConceptName": "Chills"}},
        {"$group": {
            "_id": {
                "Value": "$Value",
                "Output_value": "$Output_value"
            },
            "Value": {"$first": "$Value"},
            "Output_value": {"$first": "$Output_value"}
        }},
        {"$sort": {"Output_value": 1}}  # Sort by Output_value indicating severity
    ]))

    predefined_values = ["None", "Shaking", "Rigor"]

    if request.method == 'POST':
        values = request.form.getlist('Value')
        custom_values = request.form.getlist('CustomValue')
        output_values = request.form.getlist('Output_value')

        # Convert output values to integers
        output_values = [int(value) for value in output_values]
        # Replace "Other" with the custom values
        for i in range(len(values)):
            if values[i] == "Other":
                values[i] = custom_values[i]

        # Ensure all selected values are valid
        if all(value != "" for value in values):
            # Update all records matching the current values
            for i in range(len(values)):
                states_db.update_many(
                    {
                        "ConceptName": "Chills",
                        "Value": chills_records[i]['Value'],
                        "Output_value": chills_records[i]['Output_value']
                    },
                    {"$set": {
                        "Value": values[i],
                        "Output_value": output_values[i]
                    }}
                )

            updated_records = list(states_db.aggregate([
                {"$match": {"ConceptName": "Chills"}},
                {"$group": {
                    "_id": {
                        "Value": "$Value",
                        "Output_value": "$Output_value"
                    },
                    "Value": {"$first": "$Value"},
                    "Output_value": {"$first": "$Output_value"}
                }},
                {"$sort": {"Output_value": 1}}  # Sort by Output_value indicating severity
            ]))
            return render_template('edit_chills.html', records=updated_records, predefined_values=predefined_values,
                                   success=True)
        else:
            return render_template('edit_chills.html', records=chills_records, predefined_values=predefined_values,
                                   error=True)

    return render_template('edit_chills.html', records=chills_records, predefined_values=predefined_values)

@states_m_bp.route('/edit_skin_look', methods=['GET', 'POST'])
def edit_skin_look():
    # Fetch unique records for Skin-Look and order them by Output_value
    skin_look_records = list(states_db.aggregate([
        {"$match": {"ConceptName": "Skin-Look"}},
        {"$group": {
            "_id": {
                "Value": "$Value",
                "Output_value": "$Output_value"
            },
            "Value": {"$first": "$Value"},
            "Output_value": {"$first": "$Output_value"}
        }},
        {"$sort": {"Output_value": 1}}  # Sort by Output_value indicating severity
    ]))

    predefined_values = ["Erythema", "Vesiculation", "Desquamation", "Exfoliation"]

    if request.method == 'POST':
        values = request.form.getlist('Value')
        custom_values = request.form.getlist('CustomValue')
        output_values = request.form.getlist('Output_value')

        # Convert output values to integers
        output_values = [int(value) for value in output_values]

        # Update records
        for i in range(len(values)):
            # Check if the value is 'Other'
            if values[i] == "Other":
                # Replace 'Other' with the custom value
                update_value = custom_values[i]
            else:
                update_value = values[i]

            # Update the record in the database
            states_db.update_many(
                {
                    "ConceptName": "Skin-Look",
                    "Value": skin_look_records[i]['Value'],
                    "Output_value": skin_look_records[i]['Output_value']
                },
                {"$set": {
                    "Value": update_value,
                    "Output_value": output_values[i]
                }}
            )

        # Fetch updated records
        updated_records = list(states_db.aggregate([
            {"$match": {"ConceptName": "Skin-Look"}},
            {"$group": {
                "_id": {
                    "Value": "$Value",
                    "Output_value": "$Output_value"
                },
                "Value": {"$first": "$Value"},
                "Output_value": {"$first": "$Output_value"}
            }},
            {"$sort": {"Output_value": 1}}  # Sort by Output_value indicating severity
        ]))
        return render_template('edit_skin_look.html', records=updated_records, predefined_values=predefined_values, success=True)

    return render_template('edit_skin_look.html', records=skin_look_records, predefined_values=predefined_values)

@states_m_bp.route('/edit_allergic_state', methods=['GET', 'POST'])
def edit_allergic_state():
    # Fetch unique records for Allergic-state and order them by Output_value
    allergic_state_records = list(states_db.aggregate([
        {"$match": {"ConceptName": "Allergic-state"}},
        {"$group": {
            "_id": {
                "Value": "$Value",
                "Output_value": "$Output_value"
            },
            "Value": {"$first": "$Value"},
            "Output_value": {"$first": "$Output_value"}
        }},
        {"$sort": {"Output_value": 1}}  # Sort by Output_value indicating severity
    ]))

    predefined_values = ["Edema", "Bronchospasm", "Sever-Bronchospasm", "Anaphylactic-Shock"]

    if request.method == 'POST':
        values = request.form.getlist('Value')
        custom_values = request.form.getlist('CustomValue')
        output_values = request.form.getlist('Output_value')

        # Convert output values to integers
        output_values = [int(value) for value in output_values]

        # Replace "Other" with the custom values
        for i in range(len(values)):
            if values[i] == "Other":
                values[i] = custom_values[i]

        # Ensure all selected values are valid
        if all(value != "" for value in values):
            # Update all records matching the current values
            for i in range(len(values)):
                states_db.update_many(
                    {
                        "ConceptName": "Allergic-state",
                        "Value": allergic_state_records[i]['Value'],
                        "Output_value": allergic_state_records[i]['Output_value']
                    },
                    {"$set": {
                        "Value": values[i],
                        "Output_value": output_values[i]
                    }}
                )

            updated_records = list(states_db.aggregate([
                {"$match": {"ConceptName": "Allergic-state"}},
                {"$group": {
                    "_id": {
                        "Value": "$Value",
                        "Output_value": "$Output_value"
                    },
                    "Value": {"$first": "$Value"},
                    "Output_value": {"$first": "$Output_value"}
                }},
                {"$sort": {"Output_value": 1}}  # Sort by Output_value indicating severity
            ]))
            return render_template('edit_allergic_state.html', records=updated_records,
                                   predefined_values=predefined_values, success=True)
        else:
            return render_template('edit_allergic_state.html', records=allergic_state_records,
                                   predefined_values=predefined_values, error=True)

    return render_template('edit_allergic_state.html', records=allergic_state_records,
                           predefined_values=predefined_values)