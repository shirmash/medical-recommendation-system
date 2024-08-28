# File: app.py
from flask import Blueprint, render_template, request, redirect, url_for
from helpers.recommendation_helpers import *

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/retrieval_query')
def retrieval_query():
    return render_template('retrieval_query.html')

@main_bp.route('/update_query')
def update_query():
    return render_template('update_query.html')

@main_bp.route('/retrieval_history_query')
def retrieval_history_query():
    return render_template('retrieval_history_query.html')

@main_bp.route('/deletion_query')
def deletion_query():
    return render_template('deletion_query.html')

@main_bp.route('/recommendation_query')
def recommendations_query():
    return render_template('recommendation_query.html')

@main_bp.route('/set_states')
def set_states():
    return render_template('set_states.html')


@main_bp.route('/select_gender', methods=['GET', 'POST'])
def select_gender():
    if request.method == 'POST':
        gender = request.form['gender']
        return redirect(url_for('states_m.edit_hemoglobin', gender=gender))
    return render_template('select_gender.html')


@main_bp.route('/select_hematological', methods=['GET', 'POST'])
def select_hematological():
    if request.method == 'POST':
        gender = request.form['gender']
        variable = request.form['variable']  # Either 'hemoglobin' or 'wbc'
        return redirect(url_for('states_m.edit_hematological', gender=gender, variable=variable))
    return render_template('select_hematological.html')

@main_bp.route('/recommendation_query')
def recommendation_query():
    return render_template('recommendation_query.html')


@main_bp.route('/states_query')
def retrieval_states_query():
    return render_template('states_query.html')

@main_bp.route('/manage_recommendations')
def manage_recommendations():
    return render_template('manage_recommendations.html')

#######################################################################################################################








#
#
# if __name__ == '__main__':
#     app.run(debug=True)