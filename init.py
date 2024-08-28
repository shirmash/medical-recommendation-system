from flask import Flask
from pymongo import MongoClient

def create_app():
    app = Flask(__name__)
    # Import and register blueprints
    from app import main_bp
    from helpers.db_managment_helpers import db_bp
    from helpers.states_managment_helpers import states_m_bp
    from helpers.recommendation_helpers import rec_bp
    from helpers.states_discovery_helpers import states_d_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(db_bp)
    app.register_blueprint(states_m_bp)
    app.register_blueprint(states_d_bp)
    app.register_blueprint(rec_bp)

    return app