from pymongo import MongoClient
from flask import Blueprint, request, render_template
from helpers.recommendation_helpers import *
from  helpers.states_managment_helpers import *
from  helpers.time_helpers import  *
from helpers.states_discovery_helpers import *
db_bp = Blueprint('db', __name__)
# MongoDB connection

@db_bp.route('/retrieval_query', methods=['POST'])
def retrieval_query_function():
    loinc_num = request.form.get('loinc_num')
    component = request.form.get('component')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    query_date = request.form.get('query_date')
    query_time = request.form.get('query_time')
    current_date = request.form.get('current_date')
    current_time = request.form.get('current_time')


    if not (loinc_num or component) or not first_name or not last_name or not query_date or not current_date or not current_time:
        return render_template('not_found.html')

    current_datetime = datetime.strptime(f"{current_date}T{current_time}", '%Y-%m-%dT%H:%M')
    # Construct base MongoDB query with date criteria
    query = {"First name": first_name, "Last name": last_name,
             "Transaction time": {  ##current time needs to be after transcation time
                 "$lte": current_datetime
             },
              "$or": [
            {"Deletion time": {"$gte": current_datetime}},
            {"Deletion time": {"$eq": datetime.strptime("2100-01-01T10:00", '%Y-%m-%dT%H:%M')}}  # Exclude empty strings for Deletion time
        ]}

    if loinc_num:  # If LOINC Number is provided, use it directly
        query["LOINC-NUM"] = loinc_num
        loinc_record = loinc_db.find_one({"LOINC_NUM": loinc_num})
        if loinc_record:
            component = loinc_record["COMPONENT"]
    elif component:  # If Component is provided, find corresponding LOINC Numbers
        loinc_records = loinc_db.find({"COMPONENT": component})
        loinc_nums = [record["LOINC_NUM"] for record in loinc_records]
        if loinc_nums:
            query["LOINC-NUM"] = {"$in": loinc_nums}
        else:
            return render_template('not_found.html')  # Handle not found scenario
    if query_time:
        # Set exact time range for query
        query["Valid start time"] = {"$lte": datetime.strptime(f"{query_date}T{query_time}", '%Y-%m-%dT%H:%M'),"$gte":datetime.strptime(query_date, '%Y-%m-%d')}
    else:
        # Find the latest measurement of the day if no time specified
        end_of_day = datetime.strptime(query_date, '%Y-%m-%d') + timedelta(days=1)
        query["Valid start time"] = {
            "$lt": end_of_day,
            "$gte": datetime.strptime(query_date, '%Y-%m-%d')
        }
    # Execute MongoDB query
    results = list(patient_db.find(query).sort("Transaction time", -1))  # Sort by Transaction time in descending order
    if results:
        latest_result = results[0]  # Get the most updated record
        latest_result["Component"] = component
        return render_template('retrieval_results.html', result=latest_result)
    else:
        return render_template('not_found.html')

@db_bp.route('/retrieval_history_query', methods=['POST'])
def retrieval_history_query_function():
    loinc_num = request.form.get('loinc_num')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    from_query_date = request.form.get('from_query_date')
    from_query_time = request.form.get('from_query_time')
    to_query_date = request.form.get('to_query_date')
    to_query_time = request.form.get('to_query_time')
    current_date = request.form.get('current_date')
    current_time = request.form.get('current_time')

    if not loinc_num  or not first_name or not last_name or not from_query_date or not to_query_date or not current_date or not current_time:
        return render_template('not_found.html')

    current_datetime = datetime.strptime(f"{current_date}T{current_time}", '%Y-%m-%dT%H:%M')
    # Construct base MongoDB query with date criteria
    query = {
        "First name": first_name,
        "Last name": last_name,
        #??? whay do i need the current time
        "Transaction time": {##current time needs to be after transcation time
            "$lt": current_datetime},
        "$or": [
            {"Deletion time": {"$lt": current_datetime }},
            {"Deletion time": {"$eq": datetime.strptime("2100-01-01T10:00", '%Y-%m-%dT%H:%M')}}  # Exclude empty strings for Deletion time
        ]
    }

    if loinc_num:  # If LOINC Number is provided, use it directly
        query["LOINC-NUM"] = loinc_num
        loinc_record = loinc_db.find_one({"LOINC_NUM": loinc_num})
        if loinc_record:
            component = loinc_record["COMPONENT"]

    if from_query_time:
        from_date = datetime.strptime(f"{from_query_date}T{from_query_time}", '%Y-%m-%dT%H:%M')
        to_date = datetime.strptime(f"{to_query_date}T{to_query_time}", '%Y-%m-%dT%H:%M')
        query["Valid start time"] = {"$gte": from_date, "$lte": to_date}
    else:
        from_date = datetime.strptime(from_query_date, '%Y-%m-%d')
        to_date = datetime.strptime(to_query_date, '%Y-%m-%d') + timedelta(days=1)
        query["Valid start time"] = {"$gte": from_date, "$lt": to_date}
    results = list(patient_db.find(query))
    # Prepare results with components
    results_with_components = []
    for result in results:
        result["Transaction time"] = result["Transaction time"].strftime('%Y-%m-%d %H:%M:%S')
        result["Valid start time"] = result["Valid start time"].strftime('%Y-%m-%d %H:%M:%S')
        if component:
            result["Component"] = component
        results_with_components.append(result)
    results_with_components.sort(key=lambda x: x["Valid start time"])
    if results_with_components:
        return render_template('retrieval_history_results.html', results=results_with_components)
    else:
        return render_template('not_found.html')


@db_bp.route('/update_query', methods=['POST'])
def update_query_function():
    loinc_num = request.form.get('loinc_num')
    component = request.form.get('component')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    current_date = request.form.get('current_date')
    current_time = request.form.get('current_time')
    update_date = request.form.get('update_date')
    update_time = request.form.get('update_time')
    updated_value = request.form.get('updated_value')


    if not (loinc_num or component) or not first_name or not last_name or not update_date or not current_date or not current_time:
        return render_template('not_found.html')

    current_datetime = datetime.strptime(f"{current_date}T{current_time}", '%Y-%m-%dT%H:%M')
    update_datetime = datetime.strptime(f"{update_date}T{update_time}",  '%Y-%m-%dT%H:%M') if update_time else datetime.strptime(update_date, '%Y-%m-%d')

    # Construct base MongoDB query with date criteria
    query = {
        "First name": first_name,
        "Last name": last_name,
        "Transaction time": {##current time needs to be after transcation time
            "$lt": current_datetime
        },
        "Valid start time": {
            "$lte": update_datetime,
            "$gte": update_datetime
        },
        "$or": [
            {"Deletion time": {"$lt": current_datetime}},
            {"Deletion time": {"$eq": datetime.strptime("2100-01-01T10:00", '%Y-%m-%dT%H:%M')}}  # include empty strings for Deletion time
        ]
    }

    if loinc_num:  # If LOINC Number is provided, use it directly
        query["LOINC-NUM"] = loinc_num
        loinc_record = loinc_db.find_one({"LOINC_NUM": loinc_num})
        if loinc_record:
            component = loinc_record["COMPONENT"]
    elif component:  # If Component is provided, find corresponding LOINC Number
        loinc_record = loinc_db.find_one({"COMPONENT": component})
        if loinc_record:
            query["LOINC-NUM"] = loinc_record["LOINC_NUM"]
        else:
            return render_template('not_found.html')  # Handle not found scenario
    if update_time:
        # Set exact time range for query
        query["Valid start time"] = {"$lte": datetime.strptime(f"{update_date}T{update_time}", '%Y-%m-%dT%H:%M'),
            "$gte": datetime.strptime(f"{update_date}T{update_time}", '%Y-%m-%dT%H:%M')}
    else:
        # Find the latest measurement of the day if no time specified
        end_of_day = datetime.strptime(update_date, '%Y-%m-%d') + timedelta(days=1)
        query["Valid start time"] = {
            "$lt": end_of_day,
            "$gte": datetime.strptime(update_date, '%Y-%m-%d')
        }
    # Execute MongoDB query
    results = list(patient_db.find(query))
    if len(results) > 1:
        results.sort(key=lambda x: x["Transaction time"], reverse=True)  # Sort by Transaction time descending
        old_result = results[0]  # Choose the first (latest) record
    elif len(results)==1:
        old_result = results[0]
    else:
        return render_template('not_found.html')
    updated_result = copy.deepcopy(old_result)
    updated_result['Value'] = updated_value
    updated_result['Transaction time'] = current_datetime
    patient_db.insert_one(updated_result)##insert update to db
    ##add compunent for the output
    updated_result["Component"] = component
    old_result["Component"] = component
    return render_template('update_results.html', old_result=old_result,updated_result = updated_result)


@db_bp.route('/deletion_query', methods=['POST'])
def deletion_query_function():
    loinc_num = request.form.get('loinc_num')
    component = request.form.get('component')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    current_date = request.form.get('current_date')
    current_time = request.form.get('current_time')
    update_date = request.form.get('update_date')
    update_time = request.form.get('update_time')


    if not (loinc_num or component) or not first_name or not last_name or not update_date or not current_date or not current_time:
        return render_template('not_found.html')

    update_datetime = datetime.strptime(f"{update_date}T{update_time}",  '%Y-%m-%dT%H:%M') if update_time else datetime.strptime(update_date, '%Y-%m-%d')
    current_datetime = datetime.strptime(f"{current_date}T{current_time}", '%Y-%m-%dT%H:%M')

    # Construct base MongoDB query with date criteria
    query = {
        "First name": first_name,
        "Last name": last_name,
        "Transaction time": {##current time needs to be after transcation time
            "$lt": current_datetime
        },
        "Valid start time": {
            "$lte": update_datetime,
            "$gte": update_datetime
        },
        "$or": [
            {"Deletion time": {"$lt": current_datetime}},
            {"Deletion time": {"$eq": datetime.strptime("2100-01-01T10:00", '%Y-%m-%dT%H:%M')}}  # include empty strings for Deletion time
        ]
    }

    if loinc_num:  # If LOINC Number is provided, use it directly
        query["LOINC-NUM"] = loinc_num
        loinc_record = loinc_db.find_one({"LOINC_NUM": loinc_num})
        if loinc_record:
            component = loinc_record["COMPONENT"]
    elif component:  # If Component is provided, find corresponding LOINC Numbers
        loinc_records = loinc_db.find({"COMPONENT": component})
        loinc_nums = [record["LOINC_NUM"] for record in loinc_records]
        if loinc_nums:
            query["LOINC-NUM"] = {"$in": loinc_nums}
        else:
            return render_template('not_found.html')  # Handle not found scenario
    if update_time:
        # Set exact time range for query
        query["Valid start time"] = {"$lte": datetime.strptime(f"{update_date}T{update_time}", '%Y-%m-%dT%H:%M'),
            "$gte": datetime.strptime(f"{update_date}T{update_time}", '%Y-%m-%dT%H:%M')}
    else:
        # Find the latest measurement of the day if no time specified
        end_of_day = datetime.strptime(update_date, '%Y-%m-%d') + timedelta(days=1)
        query["Valid start time"] = {
            "$lt": end_of_day,
            "$gte": datetime.strptime(update_date, '%Y-%m-%d')
        }
    results = list(patient_db.find(query))
    if len(results) > 1:
        results.sort(key=lambda x: x["Transaction time"], reverse=True)  # Sort by Transaction time descending
        old_result = results[0]  # Choose the first (latest) record
    elif len(results)==1:
        old_result = results[0]
    else:
        return render_template('not_found.html')

    updated_result = copy.deepcopy(old_result)
    updated_result['Deletion time'] = current_datetime
    updated_result["Component"] = component

        # Step 2: Extract IDs from the fetched records
    ids_to_update = [old_result["_id"]]
    records_to_update = list(patient_db.find({"_id": {"$in": ids_to_update}})) ## get all possible updates of the same recods
    print(records_to_update)
    # Step 2: Create updated records
    updated_records = []
    for record in records_to_update:
        updated_record = copy.deepcopy(record)
        updated_record['Deletion time'] = current_datetime
        updated_record["Component"] = component
        updated_records.append(updated_record)

    # Step 3: Delete old records
    patient_db.delete_many({"_id": {"$in": ids_to_update}})

    # Step 4: Insert updated records
    if updated_records:
        patient_db.insert_many(updated_records)

    return render_template('deletion_results.html', updated_result=updated_result)