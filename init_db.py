from app import db, User

def init_database():
    print("Initializing database...")
    db.drop_all()
    db.create_all()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()
