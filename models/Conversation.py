import psycopg2
from datetime import datetime


class Conversation:
    def __init__(self, id=None, title=None, created_at=None, participants=None, messages=None):
        self.id = id
        self.title = title
        self.created_at = created_at
        self.participants = participants or []
        self.messages = messages or []

    class Message:
        def __init__(self, id=None, conversation_id=None, sender_id=None, sender_username=None, message_text=None, created_at=None):
            self.id = id
            self.conversation_id = conversation_id
            self.sender_id = sender_id
            self.sender_username = sender_username
            self.message_text = message_text
            self.created_at = created_at

        @staticmethod
        def create(connection, conversation_id, sender_id, message_text):
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO messages (conversation_id, sender_id, message_text) VALUES (%s, %s, %s) RETURNING id, created_at",
                    (conversation_id, sender_id, message_text))
                row = cursor.fetchone()

                cursor.execute(
                    "SELECT username FROM users WHERE id = %s", (sender_id,))
                sender_username = cursor.fetchone()[0]
                print(sender_username)
                connection.commit()
                return Conversation.Message(id=row[0], conversation_id=conversation_id, sender_id=sender_id,sender_username=sender_username, message_text=message_text, created_at=row[1])

        @staticmethod
        def get_messages_by_conversation_id(connection, conversation_id):
            with connection.cursor() as cursor:
                # Fetch all messages for the conversation
                cursor.execute("""
                    SELECT id, conversation_id, sender_id, message_text, created_at
                    FROM messages
                    WHERE conversation_id = %s
                    ORDER BY created_at ASC;
                """, (conversation_id,))
                rows = cursor.fetchall()

                messages = []

                for row in rows:
                    id = row[0]
                    conversation_id = row[1]
                    sender_id = row[2]
                    message_text = row[3]
                    created_at = row[4]

                    # Fetch the sender's username
                    cursor.execute("SELECT username FROM users WHERE id = %s", (sender_id,))
                    sender_username = cursor.fetchone()[0]

                    # Create a Message object for each row
                    message = Conversation.Message(
                        id=id,
                        conversation_id=conversation_id,
                        sender_id=sender_id,
                        sender_username=sender_username,
                        message_text=message_text,
                        created_at=created_at
                    )
                    messages.append(message)

                return messages


        def to_dict(self):
            return {
                "id": self.id,
                "conversation_id": self.conversation_id,
                "sender": {
                    "id": self.sender_id,
                    "username": self.sender_username
                },
                "message_text": self.message_text,
                "created_at": self.created_at
            }

    @staticmethod
    def create(connection, title=None):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO conversations (id, title) VALUES (DEFAULT, NULL) RETURNING id, created_at")
            row = cursor.fetchone()
            connection.commit()
            return Conversation(id=row[0], title=title, created_at=row[1])

    @staticmethod
    def get_conversation_by_id(connection, conversation_id):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, title, created_at
                FROM conversations
                WHERE id = %s;
            """, (conversation_id,))
            row = cursor.fetchone()
            if not row:
                return None

            # Get participants
            cursor.execute("""
                SELECT u.id, u.username
                FROM conversation_participants cp
                JOIN users u ON cp.user_id = u.id
                WHERE cp.conversation_id = %s;
            """, (conversation_id,))
            participants = cursor.fetchall()

            # Get messages
            messages = Conversation.Message.get_messages_by_conversation_id(
                connection, conversation_id)

            return Conversation(id=row[0], title=row[1], created_at=row[2], participants=[{"user_id": p[0], "username": p[1]} for p in participants], messages=messages)

    

    @staticmethod
    def get_user_conversations(connection, user_id):
        try:
            with connection.cursor() as cursor:
                # First, fetch all the conversations the user is a part of
                cursor.execute("""
                    SELECT c.id, c.created_at , c.title
                    FROM conversations c 
                    JOIN conversation_participants cp ON c.id = cp.conversation_id 
                    WHERE cp.user_id = %s
                """, (user_id,))
                conversations = cursor.fetchall()

                # Now, fetch participants for each conversation
                conversation_list = []
                for conversation in conversations:
                    conversation_id, created_at, title = conversation

                    cursor.execute("""
                        SELECT u.id, u.username 
                        FROM conversation_participants cp 
                        JOIN users u ON cp.user_id = u.id 
                        WHERE cp.conversation_id = %s
                    """, (conversation_id,))
                    participants = cursor.fetchall()

                    # Format each conversation with participants
                    conversation_list.append({
                        "id": conversation_id,
                        "created_at": created_at,
                        "participants": [{"user_id": p[0], "username": p[1]} for p in participants],
                        "title": title
                    })

                # Return the conversation list as a JSON-serializable list
                return (conversation_list)

        except Exception as e:
            print(f"An error occurred while fetching user conversations: {e}")
            return None

    def add_participant(self, connection, user_id):
        try:
            with connection.cursor() as cursor:
                # Check if the user is already a participant
                cursor.execute("""
                    SELECT 1 FROM conversation_participants 
                    WHERE conversation_id = %s AND user_id = %s
                """, (self.id, user_id))
                
                if cursor.fetchone():
                    return None  # Participant already exists
                
                # Add the participant
                cursor.execute("""
                    INSERT INTO conversation_participants (conversation_id, user_id)
                    VALUES (%s, %s);
                """, (self.id, user_id))
                connection.commit()

                # Update the participants list in the object
                self.participants.append(user_id)
                return self.participants  # Return updated list of participants

        except Exception as e:
            connection.rollback()  # Rollback on error
            print(f"Error adding participant: {e}")
            return None  # Indicate failure


    def add_message(self, connection, sender_id, message_text):
        message = Conversation.Message.create(
            connection, self.id, sender_id, message_text)
        self.messages.append(message)
        return message
    
    def update_title(self, connection, new_title):
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE conversations
                SET title = %s
                WHERE id = %s;
            """, (new_title, self.id))
            connection.commit()
            self.title = new_title

    def delete_conversation(self, connection):
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM conversations
                WHERE id = %s;
            """, (self.id,))
            connection.commit()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "participants": self.participants,
            "messages": [message.to_dict() for message in self.messages]
        }
