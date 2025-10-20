from flask import Blueprint, jsonify, request
from datetime import datetime
from src.models.mongo_models import Expense
from bson import ObjectId

expenses_bp = Blueprint('expenses', __name__)

@expenses_bp.route('/expenses', methods=['GET'])
def get_expenses():
    """Get all expenses with optional filtering"""
    try:
        truck_id = request.args.get('truck_id', '')
        category = request.args.get('category', '')
        status = request.args.get('status', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        filter_dict = {}
        if truck_id:
            filter_dict['truck_id'] = truck_id
        if category:
            filter_dict['category'] = category
        if status:
            filter_dict['status'] = status
        
        # Date range filtering
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter['$gte'] = datetime.fromisoformat(start_date)
            if end_date:
                date_filter['$lte'] = datetime.fromisoformat(end_date)
            filter_dict['expense_date'] = date_filter
        
        expenses = Expense.find_all(filter_dict)
        expense_list = []
        for expense in expenses:
            expense_dict = Expense.to_dict_populated(expense)
            expense_list.append(expense_dict)
        
        return jsonify({
            'expenses': expense_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@expenses_bp.route('/expenses/<expense_id>', methods=['GET'])
def get_expense(expense_id):
    """Get a specific expense by ID"""
    try:
        expense = Expense.find_by_id(expense_id)
        if expense:
            return jsonify({
                'expense': Expense.to_dict_populated(expense)
            })
        return jsonify({'error': 'Expense not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@expenses_bp.route('/expenses', methods=['POST'])
def create_expense():
    """Create a new expense"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['expense_number', 'category', 'amount', 'expense_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check for unique expense number
        collection = Expense.get_collection()
        if collection.find_one({'expense_number': data['expense_number']}):
            return jsonify({'error': 'Expense number already exists'}), 400
        
        expense_doc = {
            'expense_number': data['expense_number'],
            'truck_id': data.get('truck_id'),
            'trip_id': data.get('trip_id'),
            'category': data['category'],
            'amount': data['amount'],
            'expense_date': datetime.fromisoformat(data['expense_date']),
            'vendor_name': data.get('vendor_name'),
            'receipt_number': data.get('receipt_number'),
            'payment_method': data.get('payment_method'),
            'location': data.get('location'),
            'description': data.get('description'),
            'status': data.get('status', 'pending')
        }
        
        expense_id = Expense.insert_one(expense_doc)
        expense = Expense.find_by_id(expense_id)
        
        return jsonify({
            'message': 'Expense created successfully',
            'expense': Expense.to_dict_populated(expense)
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@expenses_bp.route('/expenses/<expense_id>', methods=['PUT'])
def update_expense(expense_id):
    """Update an existing expense"""
    try:
        expense = Expense.find_by_id(expense_id)
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404
        
        data = request.get_json()
        collection = Expense.get_collection()
        
        # Check for unique expense number (excluding current expense)
        if 'expense_number' in data and data['expense_number'] != expense.get('expense_number'):
            if collection.find_one({'expense_number': data['expense_number'], '_id': {'$ne': ObjectId(expense_id)}}):
                return jsonify({'error': 'Expense number already exists'}), 400
        
        # Update fields
        updatable_fields = ['expense_number', 'truck_id', 'trip_id', 'category', 'amount', 'vendor_name',
                           'receipt_number', 'payment_method', 'location', 'description', 'status']
        update_doc = {}
        for field in updatable_fields:
            if field in data:
                update_doc[field] = data[field]
        
        # Handle date fields
        if 'expense_date' in data and data['expense_date']:
            update_doc['expense_date'] = datetime.fromisoformat(data['expense_date'])
        if 'submitted_date' in data and data['submitted_date']:
            update_doc['submitted_date'] = datetime.fromisoformat(data['submitted_date'])
        if 'approved_date' in data and data['approved_date']:
            update_doc['approved_date'] = datetime.fromisoformat(data['approved_date'])
        
        Expense.update_one(expense_id, update_doc)
        updated_expense = Expense.find_by_id(expense_id)
        
        return jsonify({
            'message': 'Expense updated successfully',
            'expense': Expense.to_dict_populated(updated_expense)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@expenses_bp.route('/expenses/<expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    """Delete an expense (soft delete by setting status to 'cancelled')"""
    try:
        expense = Expense.find_by_id(expense_id)
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404
        
        Expense.update_one(expense_id, {'status': 'cancelled'})
        
        return jsonify({
            'message': 'Expense cancelled successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500