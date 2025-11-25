# Import the necessary components from your application
# Using absolute imports to be runnable from the project root
from fastapi_app.database import engine, SessionLocal, Base
from fastapi_app import crud, models, schema

print("Connecting to the database to create tables...")

try:
    # This command inspects all the classes that inherit from Base (your User and Subscription models)
    # and creates the corresponding tables in the database if they don't already exist.
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully or already exist.")
except Exception as e:
    print(f"An error occurred while creating tables: {e}")
    # Exit if we can't even create tables
    exit()

def seed_database():
    """
    Populates the database with initial demo data, such as a default user and admin.
    This function is idempotent, meaning it can be run multiple times without creating duplicates.
    """
    db = SessionLocal()
    print("\nSeeding database with demo users...")
    try:
        # --- Check for and create the standard user ---
        user_exists = crud.get_user_by_email(db, "user@example.com")
        if not user_exists:
            print("Creating standard user...")
            user_in = schema.UserCreate(
                email="user@example.com",
                full_name="Demo User",
                password="password"
            )
            crud.create_user(db=db, user=user_in, role=models.UserRole.USER)
            print("- Standard user created: user@example.com")
        else:
            print("- Standard user already exists.")

        # --- Check for and create the admin user ---
        admin_exists = crud.get_user_by_email(db, "admin@example.com")
        if not admin_exists:
            print("Creating admin user...")
            admin_in = schema.UserCreate(
                email="admin@example.com",
                full_name="Demo Admin",
                password="adminpassword"
            )
            crud.create_user(db=db, user=admin_in, role=models.UserRole.ADMIN)
            print("- Admin user created: admin@example.com")
        else:
            print("- Admin user already exists.")
            
        print("\n-------------------------------------------")
        print("Database seeding complete.")
        print("You can now start the main application.")
        print("-------------------------------------------")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

