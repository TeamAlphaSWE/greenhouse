from flask import Blueprint, abort, jsonify, request

from app.repositories.plants import plants as plant_repository

plants = Blueprint("plants", __name__, url_prefix="/api/v1/plants")


@plants.get("")
def list_plants():
    return jsonify(plant_repository.find())


@plants.get("/<plant_id>")
def get_plant(plant_id):
    plant = plant_repository.get(plant_id)
    if plant is None:
        abort(404)
    return jsonify(plant)


@plants.post("")
def create_plant():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    plant = plant_repository.create({"name": data["name"]})
    return jsonify(plant), 201


@plants.patch("/<plant_id>")
def update_plant(plant_id):
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    plant = plant_repository.update(plant_id, {"name": data["name"]})
    if plant is None:
        abort(404)
    return jsonify(plant)


@plants.delete("/<plant_id>")
def delete_plant(plant_id):
    if not plant_repository.delete(plant_id):
        abort(404)
    return "", 204
