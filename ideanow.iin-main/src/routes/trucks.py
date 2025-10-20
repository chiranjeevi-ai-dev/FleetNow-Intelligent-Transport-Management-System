from flask import Blueprint, jsonify, request
from bson import ObjectId
from src.models.mongo_models import Truck

trucks_bp = Blueprint('trucks', __name__)

@trucks_bp.route('/trucks', methods=['GET'])
def get_trucks():
    """Get all trucks with optional filtering"""
    try:
        status = request.args.get('status', '')
        region = request.args.get('region', '')
        filter_dict = {}
        if status:
            filter_dict['status'] = status
        if region:
            filter_dict['region'] = region
        trucks = Truck.find_all(filter_dict)
        truck_list = [Truck.to_dict(truck) for truck in trucks]
        return jsonify({'trucks': truck_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trucks_bp.route('/trucks/<truck_id>', methods=['GET'])
def get_truck(truck_id):
    """Get a specific truck by ID"""
    try:
        truck = Truck.find_by_id(truck_id)
        if truck:
            return jsonify({'truck': Truck.to_dict(truck)})
        return jsonify({'error': 'Truck not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trucks_bp.route('/trucks/<truck_id>/view', methods=['POST'])
def view_truck(truck_id):
    """Increment view count for a truck and return it"""
    try:
        truck = Truck.find_by_id(truck_id)
        if not truck:
            return jsonify({'error': 'Truck not found'}), 404
        views = truck.get('views', 0) + 1
        Truck.update_one(truck_id, {'views': views})
        updated_truck = Truck.find_by_id(truck_id)
        return jsonify({'message': 'Truck viewed', 'truck': Truck.to_dict(updated_truck)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trucks_bp.route('/trucks', methods=['POST'])
def create_truck():
    """Create a new truck and return it"""
    try:
        data = request.get_json()
        required_fields = ['truck_number', 'make', 'model', 'year', 'license_plate','insurance_expiry', 'vin', 'fuel_capacity','fc_expiry','fc_number','insurance_number']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        collection = Truck.get_collection()
        for unique_field in ['truck_number', 'license_plate', 'vin']:
            if collection.find_one({unique_field: data[unique_field]}):
                return jsonify({'error': f"{unique_field.replace('_', ' ').title()} already exists"}), 400

        truck_doc = {
            'truck_number': data['truck_number'],
            'make': data['make'],
            'model': data['model'],
            'year': data['year'],
            'license_plate': data['license_plate'],
            'insurance_expiry':data['insurance_expiry'],
            'insurance_number':data['insurance_number'],
            'fc_number':data['fc_number'],
            'fc_expiry':data['fc_expiry'],
            'vin': data['vin'],
            'fuel_capacity': data['fuel_capacity'],
            'status': data.get('status', 'active'),
            'region': data.get('region'),
        }
        truck_id = Truck.insert_one(truck_doc)
        new_truck = Truck.find_by_id(str(truck_id))
        return jsonify({
            'message': 'Truck created successfully',
            'truck': Truck.to_dict(new_truck)
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trucks_bp.route('/trucks/<truck_id>', methods=['PUT'])
def update_truck(truck_id):
    """Update an existing truck and return the updated truck"""
    try:
        truck = Truck.find_by_id(truck_id)
        if not truck:
            return jsonify({'error': 'Truck not found'}), 404

        data = request.get_json()
        collection = Truck.get_collection()
        for unique_field in ['truck_number', 'license_plate', 'vin']:
            if unique_field in data and data[unique_field] != truck.get(unique_field):
                if collection.find_one({unique_field: data[unique_field], '_id': {'$ne': ObjectId(truck_id)}}):
                    return jsonify({'error': f"{unique_field.replace('_', ' ').title()} already exists"}), 400

        updatable_fields = ['truck_number', 'make', 'model', 'year', 'license_plate','insurance_expiry', 'vin', 'fuel_capacity', 'status', 'region','fc_expiry','fc_number','insurance_number']
        update_doc = {field: data[field] for field in updatable_fields if field in data}
        Truck.update_one(truck_id, update_doc)
        updated_truck = Truck.find_by_id(truck_id)
        return jsonify({
            'message': 'Truck updated successfully',
            'truck': Truck.to_dict(updated_truck)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trucks_bp.route('/trucks/<truck_id>', methods=['DELETE'])
def delete_truck(truck_id):
    """Soft delete a truck (set status to 'Inactive')"""
    try:
        truck = Truck.find_by_id(truck_id)
        if not truck:
            return jsonify({'error': 'Truck not found'}), 404
        Truck.update_one(truck_id, {'status': 'Inactive'})
        return jsonify({'message': 'Truck retired successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500