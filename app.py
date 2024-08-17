import os
import psycopg2
import json

from dotenv import load_dotenv


from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session


from models.User import User
from models.Conversation import Conversation

app = Flask(__name__)

app.secret_key = 'the random string'


load_dotenv()

connection = psycopg2.connect(
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432')
)

@app.route('/')
def index():
    return 'index'


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists
        
        
        user = User.create(connection=connection,
                        username=username, password=password)
        if user:
            session['user_id'] = user.user_id
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        else:
            flash('Registration failed. Please try again.')


    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists

        user = User.authenticate(
            connection=connection, username=username, password=password)

        if user:
            session['user_id'] = user.user_id
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')


@ app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))


@ app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Fetch user conversations from the database

    conversations = Conversation.get_user_conversations(
        connection=connection, user_id=session['user_id'])

    return render_template('dashboard.html', conversations=conversations, user = {"user_id": session['user_id'], "username": session['username']})




@app.route('/conversations/new', methods=['GET', 'POST'])
def create_conversation():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        recepient_id = request.form['recepient']
        message = request.form['message']
       
        # Create a new conversation
        conversation = Conversation.create(connection=connection)
        
        # Add participants
        print(session['user_id'])
        conversation.add_participant(connection=connection, user_id=session['user_id'])
        conversation.add_participant(connection=connection, user_id=recepient_id)

        # Add message
        conversation.add_message(connection=connection, sender_id=session['user_id'], message_text=message)
    
        if conversation:
            return redirect(url_for('view_conversation', conversation_id=conversation.id))
        else:
            flash('Failed to create conversation, Possibly recepient does not exist')

    return render_template('create_conversation.html')


@app.route('/conversations/<int:conversation_id>', methods=['GET', 'POST', 'DELETE'])
def view_conversation(conversation_id):
    conversation = Conversation.get_conversation_by_id(connection=connection, conversation_id=conversation_id)
    if conversation:
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if request.method == 'POST':
            if request.form.get('_method') == 'DELETE':
                conversation = Conversation.get_conversation_by_id(connection=connection, conversation_id=conversation_id)
                if conversation:
                    conversation.delete_conversation(connection=connection)
                    flash('Conversation successfully deleted.', 'success')
                    return redirect(url_for('dashboard'))
                
            message = request.form['message']
            
            # Add message to the conversation
            conversation = Conversation.get_conversation_by_id(connection=connection, conversation_id=conversation_id)
            conversation.add_message(connection=connection, sender_id=session['user_id'], message_text=message)

            return redirect(url_for('view_conversation', conversation_id=conversation_id))

        #conversation = Conversation.get_conversation_by_id(connection=connection, conversation_id=conversation_id)
        messages = conversation.messages        
        return render_template('conversation.html', conversation=conversation, messages=messages, user={"user_id": session['user_id'], "username": session['username']})
    flash('Conversation not found.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/conversations/<int:conversation_id>/add_participant', methods=['POST'])
def add_participant(conversation_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    data = request.get_json()
    participant_id = data.get('participant_id')

    if not participant_id:
        return {"message": "Participant ID is required"}, 400
    
    conversation = Conversation.get_conversation_by_id(connection=connection, conversation_id=conversation_id)
    
    if not conversation:
        return {"message": "Conversation not found"}, 404
    
    response = conversation.add_participant(connection=connection, user_id=participant_id)
    
    if response is not None:
        return {"message": "Participant added successfully", "participants": response}, 201
    else:
        return {"message": "Failed to add participant or participant already exists"}, 400


@app.route('/conversations/<int:conversation_id>/edit', methods=['POST'])
def edit_conversation(conversation_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    
    if request.method == 'POST':
        # Update conversation title
        data = request.get_json()

        if data.get('title'):
            conversation = Conversation.get_conversation_by_id(
                connection=connection, conversation_id=conversation_id)
            conversation.update_title(connection=connection, new_title=data['title'])
            return jsonify({'message': 'Conversation title updated successfully'})
        
        return(data)
        
