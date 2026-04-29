"""Create the first admin user. Run with: python -m scripts.create_admin"""
import sys
from getpass import getpass

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import Role, User

Base.metadata.create_all(bind=engine)


def main():
    email = input("Admin email: ").strip()
    password = getpass("Password: ")
    full_name = input("Full name (optional): ").strip() or None

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print(f"User {email} already exists.")
            sys.exit(1)
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=Role.admin,
        )
        db.add(user)
        db.commit()
        print(f"Admin user {email} created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
