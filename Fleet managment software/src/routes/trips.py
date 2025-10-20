from flask import Blueprint, jsonify, request
from datetime import datetime
from src.models.mongo_models import Trip, SubTrip
from bson import ObjectId

trips_bp = Blueprint('trips', __name__)

def parse_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def update_trip_revenue(trip_id):
    """Sum all subtrip costs and update the parent trip's revenue."""
    subtrips = SubTrip.find_all({'trip_id': trip_id})
    total_revenue = sum(float(sub.get('cost', 0) or 0) for sub in subtrips)
    Trip.update_one(trip_id, {'revenue': total_revenue})

@trips_bp.route('/trips', methods=['GET'])
def get_trips():
    try:
        truck_id = request.args.get('truck_id', '')
        driver_id = request.args.get('driver_id', '')
        status = request.args.get('status', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')

        filter_dict = {}
        if truck_id:
            filter_dict['truck_id'] = truck_id
        if driver_id:
            filter_dict['driver_id'] = driver_id
        if status:
            filter_dict['status'] = status

        # Date range filtering
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter['$gte'] = datetime.fromisoformat(start_date)
            if end_date:
                date_filter['$lte'] = datetime.fromisoformat(end_date)
            filter_dict['start_date'] = date_filter

        trips = Trip.find_all(filter_dict)
        trip_list = []
        for trip in trips:
            trip_dict = Trip.to_dict_populated(trip)
            trip_list.append(trip_dict)

        return jsonify({
            'trips': trip_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips/<trip_id>', methods=['GET'])
def get_trip(trip_id):
    try:
        trip = Trip.find_by_id(trip_id)
        if trip:
            trip_dict = Trip.to_dict_populated(trip)
            # Get subtrips for this trip
            subtrips = SubTrip.find_all({'trip_id': trip_id})
            trip_dict['subtrips'] = [SubTrip.to_dict(sub) for sub in subtrips]
            return jsonify({'trip': trip_dict})
        return jsonify({'error': 'Trip not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips', methods=['POST'])
def create_trip():
    try:
        data = request.get_json()
        required_fields = ['trip_number', 'truck_id', 'driver_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        collection = Trip.get_collection()
        if collection.find_one({'trip_number': data['trip_number']}):
            return jsonify({'error': 'Trip number already exists'}), 400

        trip_doc = {
            'trip_number': data['trip_number'],
            'truck_id': data['truck_id'],
            'driver_id': data['driver_id'],
            'start_date': datetime.fromisoformat(data['start_date']),
            'end_date': datetime.fromisoformat(data['end_date']) if data.get('end_date') else None,
            'distance_km': parse_float(data.get('distance_km', 0)),
            'mileage': parse_float(data.get('mileage', 0)),
            'revenue': parse_float(data.get('revenue', 0)),
            'fuel_consumed': parse_float(data.get('fuel_consumed', 0)),
            'fuel_cost': parse_float(data.get('fuel_cost', 0)),
            'toll': parse_float(data.get('toll', 0)),
            'rto': parse_float(data.get('rto', 0)),
            'adblue': parse_float(data.get('adblue', 0)),
            'driver_salary': parse_float(data.get('driver_salary', 0)),
            'labour_charges': parse_float(data.get('labour_charges', 0)),
            'extra_expense': parse_float(data.get('extra_expense', 0)),
            'other_expenses': parse_float(data.get('other_expenses', 0)),
            'profit': parse_float(data.get('profit', 0)),
            'status': data.get('status', 'planned'),
            'notes': data.get('notes', ''),
        }

        trip_id = Trip.insert_one(trip_doc)
        trip = Trip.find_by_id(trip_id)
        return jsonify({
            'message': 'Trip created successfully',
            'trip': Trip.to_dict_populated(trip)
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips/<trip_id>', methods=['PUT'])
def update_trip(trip_id):
    try:
        trip = Trip.find_by_id(trip_id)
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404

        data = request.get_json()
        collection = Trip.get_collection()

        if 'trip_number' in data and data['trip_number'] != trip.get('trip_number'):
            if collection.find_one({'trip_number': data['trip_number'], '_id': {'$ne': ObjectId(trip_id)}}):
                return jsonify({'error': 'Trip number already exists'}), 400

        updatable_fields = [
            'trip_number', 'truck_id', 'driver_id', 'distance_km', 'mileage', 'revenue', 'fuel_consumed', 'fuel_cost',
            'toll', 'rto', 'adblue', 'driver_salary', 'labour_charges', 'extra_expense',
            'other_expenses', 'profit', 'status', 'notes'
        ]
        update_doc = {}
        for field in updatable_fields:
            if field in data:
                if field in [
                    'distance_km', 'mileage', 'revenue', 'fuel_consumed', 'fuel_cost',
                    'toll', 'rto', 'adblue', 'driver_salary', 'labour_charges', 'extra_expense',
                    'other_expenses', 'profit'
                ]:
                    update_doc[field] = parse_float(data[field], 0)
                else:
                    update_doc[field] = data[field]

        if 'start_date' in data and data['start_date']:
            update_doc['start_date'] = datetime.fromisoformat(data['start_date'])
        if 'end_date' in data and data['end_date']:
            update_doc['end_date'] = datetime.fromisoformat(data['end_date'])

        Trip.update_one(trip_id, update_doc)
        updated_trip = Trip.find_by_id(trip_id)

        return jsonify({
            'message': 'Trip updated successfully',
            'trip': Trip.to_dict_populated(updated_trip)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips/<trip_id>', methods=['DELETE'])
def delete_trip(trip_id):
    try:
        trip = Trip.find_by_id(trip_id)
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404

        Trip.update_one(trip_id, {'status': 'cancelled'})

        return jsonify({
            'message': 'Trip cancelled successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---- SUB TRIP ENDPOINTS ----

@trips_bp.route('/trips/<trip_id>/subtrips', methods=['GET'])
def get_subtrips(trip_id):
    """Get all sub-trips for a parent trip"""
    try:
        subtrips = SubTrip.find_all({'trip_id': trip_id})
        subtrip_list = [SubTrip.to_dict(sub) for sub in subtrips]
        return jsonify({'subtrips': subtrip_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips/<trip_id>/subtrips', methods=['POST'])
def create_subtrip(trip_id):
    """Create a sub-trip linked to a trip"""
    try:
        data = request.get_json()
        required_fields = ['date', 'end_date', 'origin', 'destination', 'client_name', 'cargo_weight', 'cost']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Validation
        date_val = datetime.fromisoformat(data['date'])
        end_date_val = datetime.fromisoformat(data['end_date'])
        if date_val > end_date_val:
            return jsonify({'error': 'Date cannot be after End Date'}), 400     

        subtrip_doc = {
            'trip_id': trip_id,
            'date': data['date'],
            'end_date': data['end_date'],
            'origin': data['origin'],
            'destination': data['destination'],
            'client_name': data['client_name'],
            'cargo_weight': parse_float(data.get('cargo_weight', 0)),
            'cost': parse_float(data.get('cost', 0))
        }
        subtrip_id = SubTrip.insert_one(subtrip_doc)
        update_trip_revenue(trip_id)  # <-- keep revenue in sync
        subtrip = SubTrip.find_by_id(subtrip_id)
        return jsonify({'message': 'Sub Trip added', 'subtrip': SubTrip.to_dict(subtrip)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips/<trip_id>/subtrips/<subtrip_id>', methods=['PUT'])
def update_subtrip(trip_id, subtrip_id):
    """Update a sub-trip"""
    try:
        subtrip = SubTrip.find_by_id(subtrip_id)
        if not subtrip or subtrip.get('trip_id') != trip_id:
            return jsonify({'error': 'Sub Trip not found'}), 404

        data = request.get_json()
        updatable_fields = ['date', 'end_date', 'origin', 'destination', 'client_name', 'cargo_weight', 'cost']
        update_doc = {}
        for field in updatable_fields:
            if field in data:
                if field in ['cargo_weight', 'cost']:
                    parsed = parse_float(data[field], 0)
                    if parsed < 0:
                        return jsonify({'error': f'{field.replace("_", " ").title()} must be ≥ 0'}), 400
                    update_doc[field] = parsed
                else:
                    update_doc[field] = data[field]
        if 'date' in update_doc and 'end_date' in update_doc:
            if update_doc['date'] > update_doc['end_date']:
                return jsonify({'error': 'Date cannot be after End Date'}), 400

        SubTrip.update_one(subtrip_id, update_doc)
        update_trip_revenue(trip_id)  # <-- keep revenue in sync
        updated = SubTrip.find_by_id(subtrip_id)
        return jsonify({'message': 'Sub Trip updated', 'subtrip': SubTrip.to_dict(updated)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips/<trip_id>/subtrips/<subtrip_id>', methods=['DELETE'])
def delete_subtrip(trip_id, subtrip_id):
    """Delete a sub-trip (hard delete)"""
    try:
        subtrip = SubTrip.find_by_id(subtrip_id)
        if not subtrip or subtrip.get('trip_id') != trip_id:
            return jsonify({'error': 'Sub Trip not found'}), 404
        SubTrip.delete_one(subtrip_id)
        update_trip_revenue(trip_id)  # <-- keep revenue in sync
        return jsonify({'message': 'Sub Trip deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500