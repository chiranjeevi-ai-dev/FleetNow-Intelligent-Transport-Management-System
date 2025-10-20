from flask import Blueprint, jsonify, request
from datetime import datetime
from src.models.mongo_models import ClientPayment, SubTrip
from bson import ObjectId

clientpayment_bp = Blueprint('clientpayment', __name__)

def parse_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

@clientpayment_bp.route('/client-payments', methods=['GET'])
def get_client_payments():
    try:
        payments = ClientPayment.find_all({})
        payment_list = []
        for pmt in payments:
            doc = dict(pmt)
            doc['id'] = str(doc.get('_id'))
            doc.pop('_id', None)
            payment_list.append(doc)
        return jsonify({'payments': payment_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clientpayment_bp.route('/client-payments', methods=['POST'])
def create_client_payment():
    try:
        data = request.get_json()
        required_fields = ['client_name', 'cost', 'advance_payment', 'balance', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Optionally, check if payment already exists for this client (for a given period, etc)
        collection = ClientPayment.get_collection()
        if collection.find_one({'client_name': data['client_name']}):
            return jsonify({'error': 'Payment for this client already exists'}), 400

        payment_doc = {
            'client_name': data['client_name'],
            'cost': parse_float(data['cost']),
            'advance_payment': parse_float(data['advance_payment']),
            'balance': parse_float(data['balance']),
            'status': data['status'],
            'created_at': datetime.utcnow()
        }
        payment_id = ClientPayment.insert_one(payment_doc)
        payment = ClientPayment.find_by_id(payment_id)
        doc = dict(payment)
        doc['id'] = str(doc.get('_id'))
        doc.pop('_id', None)
        return jsonify({'message': 'Client payment saved', 'payment': doc}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint: Get all unique client names for dropdown
@clientpayment_bp.route('/client-names', methods=['GET'])
def get_client_names():
    try:
        collection = SubTrip.get_collection()
        names = collection.distinct('client_name')
        return jsonify({'client_names': names})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint: Get all subtrips, or filter by client_name for JS sum
@clientpayment_bp.route('/subtrips', methods=['GET'])
def get_all_subtrips():
    try:
        client_name = request.args.get('client_name')
        if client_name:
            subtrips = SubTrip.find_all({'client_name': client_name})
        else:
            subtrips = SubTrip.find_all({})
        subtrip_list = []
        for sub in subtrips:
            doc = dict(sub)
            doc['id'] = str(doc.get('_id'))
            doc.pop('_id', None)
            subtrip_list.append(doc)
        return jsonify({'subtrips': subtrip_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get, update, delete endpoints: update to use client_name as needed, or keep as payment_id

@clientpayment_bp.route('/client-payments/<payment_id>', methods=['GET'])
def get_client_payment(payment_id):
    try:
        payment = ClientPayment.find_by_id(payment_id)
        if not payment:
            return jsonify({'error': 'Client payment not found'}), 404
        doc = dict(payment)
        doc['id'] = str(doc.get('_id'))
        doc.pop('_id', None)
        return jsonify({'payment': doc})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clientpayment_bp.route('/client-payments/<payment_id>', methods=['PUT'])
def update_client_payment(payment_id):
    try:
        payment = ClientPayment.find_by_id(payment_id)
        if not payment:
            return jsonify({'error': 'Client payment not found'}), 404
        data = request.get_json()
        update_doc = {}
        for field in ['advance_payment', 'balance', 'status']:
            if field in data:
                if field in ['advance_payment', 'balance']:
                    update_doc[field] = parse_float(data[field])
                else:
                    update_doc[field] = data[field]
        ClientPayment.update_one(payment_id, update_doc)
        updated = ClientPayment.find_by_id(payment_id)
        doc = dict(updated)
        doc['id'] = str(doc.get('_id'))
        doc.pop('_id', None)
        return jsonify({'message': 'Client payment updated', 'payment': doc})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clientpayment_bp.route('/client-payments/<payment_id>', methods=['DELETE'])
def delete_client_payment(payment_id):
    try:
        payment = ClientPayment.find_by_id(payment_id)
        if not payment:
            return jsonify({'error': 'Client payment not found'}), 404
        ClientPayment.delete_one(payment_id)
        return jsonify({'message': 'Client payment deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500