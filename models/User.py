class User:
    def __init__(self, user_id, username, password=None):
        self.user_id = user_id
        self.username = username
        self.password = password

    @staticmethod
    def create_table(connection):
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()

    @staticmethod
    def create(connection, username, password):
        with connection.cursor() as cursor:

            # Check if the username already exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return None

            cursor.execute("""
                INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id
            """, (username, password))
            user_id = cursor.fetchone()[0]
            connection.commit()
            return User(user_id, username, password)

    @staticmethod
    def get_by_id(connection, user_id):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM users WHERE id = %s
            """, (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                return User(*user_data)
            return None
    
    @staticmethod
    def get_all_users(connection):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, username FROM users
            """)
            users = cursor.fetchall()            
            return [User(*user) for user in users]

    @staticmethod
    def authenticate(connection, username, password):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM users WHERE username = %s AND password = %s
            """, (username, password))
            user_data = cursor.fetchone()
            if user_data:
                return User(user_id=user_data[0], username=user_data[1], password=user_data[2])
            return None
