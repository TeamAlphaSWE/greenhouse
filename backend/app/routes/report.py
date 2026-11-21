from flask import Blueprint, request, jsonify
from app.services.ai_service import AIService

report = Blueprint("reports", __name__, url_prefix="/api/v1/report")

@report.post('api/v1/report')
def generate_report():
    """Collect data once report_api sends it over to here"""
    data = request.get_json()
    start_date = data.get('start')
    end_date = data.get('end')
    zone = data.get('zone')
    sensor = data.get('sensor')