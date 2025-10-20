from flask import Blueprint, jsonify, request
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient

# --- MongoDB Connection ---
client = MongoClient("mongodb://localhost:27017/")
db = client['fleet_management']
employee_collection = db['employees']

employees_bp = Blueprint('employees', __name__)

def employee_to_dict(emp):
    return {
        "id": str(emp.get("_id")),
        "employee_number": emp.get("employee_number", ""),
        "first_name": emp.get("first_name", ""),
        "last_name": emp.get("last_name", ""),
        "email": emp.get("email", ""),
        "position": emp.get("position", ""),
        "phone": emp.get("phone", ""),
        "hire_date": emp.get("hire_date").strftime("%Y-%m-%d") if emp.get("hire_date") else "",
        "license_number": emp.get("license_number", ""),
        "license_expiry": emp.get("license_expiry").strftime("%Y-%m-%d") if emp.get("license_expiry") else "",
        "emergency_contact_name": emp.get("emergency_contact_name", ""),
        "emergency_contact_phone": emp.get("emergency_contact_phone", ""),
        "salary": emp.get("salary", ""),
        "status": emp.get("status", ""),
        "region": emp.get("region", ""),
        "notes": emp.get("notes", ""),
        "created_at": emp.get("created_at").isoformat() if emp.get("created_at") else "",
        "updated_at": emp.get("updated_at").isoformat() if emp.get("updated_at") else ""
    }

@employees_bp.route('/employees', methods=['GET'])
def get_employees():
    """Get all employees with optional filtering"""
    try:
        position = request.args.get('position', '')
        region = request.args.get('region', '')
        status = request.args.get('status', '')

        filter_dict = {}
        if position:
            filter_dict['position'] = position
        if region:
            filter_dict['region'] = region
        if status:
            filter_dict['status'] = status

        employees = employee_collection.find(filter_dict)
        employee_list = [employee_to_dict(emp) for emp in employees]
        return jsonify({'employees': employee_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@employees_bp.route('/employees/<employee_id>', methods=['GET'])
def get_employee(employee_id):
    try:
        emp = employee_collection.find_one({'_id': ObjectId(employee_id)})
        if emp:
            return jsonify({'employee': employee_to_dict(emp)})
        return jsonify({'error': 'Employee not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@employees_bp.route('/employees', methods=['POST'])
def create_employee():
    """Create a new employee"""
    try:
        data = request.get_json()
        required_fields = ['employee_number', 'first_name', 'last_name', 'position', 'email', 'phone']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Unique constraints
        if employee_collection.find_one({'employee_number': data['employee_number']}):
            return jsonify({'error': 'Employee number already exists'}), 400
        if employee_collection.find_one({'email': data['email']}):
            return jsonify({'error': 'Email already exists'}), 400

        # Parse dates
        hire_date = None
        if data.get('hire_date'):
            try:
                hire_date = datetime.fromisoformat(data['hire_date'])
            except Exception:
                hire_date = datetime.utcnow()
        else:
            hire_date = datetime.utcnow()

        license_expiry = None
        if data.get('license_expiry'):
            try:
                license_expiry = datetime.fromisoformat(data['license_expiry'])
            except Exception:
                license_expiry = None

        now = datetime.utcnow()
        employee_doc = {
            'employee_number': data['employee_number'],
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'position': data['position'],
            'email': data['email'],
            'phone': data['phone'],
            'hire_date': hire_date,
            'license_number': data.get('license_number', ''),
            'license_expiry': license_expiry,
            'emergency_contact_name': data.get('emergency_contact_name', ''),
            'emergency_contact_phone': data.get('emergency_contact_phone', ''),
            'salary': data.get('salary', ''),
            'status': data.get('status', 'active'),
            'region': data.get('region', ''),
            'created_at': now,
            'updated_at': now,
        }
        result = employee_collection.insert_one(employee_doc)
        new_emp = employee_collection.find_one({'_id': result.inserted_id})
        return jsonify({'message': 'Employee created successfully', 'employee': employee_to_dict(new_emp)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@employees_bp.route('/employees/<employee_id>', methods=['PUT'])
def update_employee(employee_id):
    """Update an existing employee (by MongoDB ObjectId)"""
    try:
        emp = employee_collection.find_one({'_id': ObjectId(employee_id)})
        if not emp:
            return jsonify({'error': 'Employee not found'}), 404

        data = request.get_json()
        # Unique constraints, skip if not changing
        if 'employee_number' in data and data['employee_number'] != emp.get('employee_number'):
            if employee_collection.find_one({'employee_number': data['employee_number'], '_id': {'$ne': ObjectId(employee_id)}}):
                return jsonify({'error': 'Employee number already exists'}), 400
        if 'email' in data and data['email'] != emp.get('email'):
            if employee_collection.find_one({'email': data['email'], '_id': {'$ne': ObjectId(employee_id)}}):
                return jsonify({'error': 'Email already exists'}), 400

        # Parse dates
        update_doc = {}
        date_fields = ['hire_date', 'license_expiry']
        for key, value in data.items():
            if key in date_fields and value:
                try:
                    update_doc[key] = datetime.fromisoformat(value)
                except Exception:
                    continue
            else:
                update_doc[key] = value

        update_doc['updated_at'] = datetime.utcnow()
        employee_collection.update_one({'_id': ObjectId(employee_id)}, {'$set': update_doc})
        updated_emp = employee_collection.find_one({'_id': ObjectId(employee_id)})
        return jsonify({'message': 'Employee updated successfully', 'employee': employee_to_dict(updated_emp)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@employees_bp.route('/employees/<employee_id>', methods=['DELETE'])
def delete_employee(employee_id):
    """Soft delete by setting status to 'inactive'"""
    try:
        emp = employee_collection.find_one({'_id': ObjectId(employee_id)})
        if not emp:
            return jsonify({'error': 'Employee not found'}), 404
        employee_collection.update_one({'_id': ObjectId(employee_id)}, {'$set': {'status': 'inactive', 'updated_at': datetime.utcnow()}})
        return jsonify({'message': 'Employee deactivated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500