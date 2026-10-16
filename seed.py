"""Load dummy (fake) students for testing. Run: python seed.py"""
from app import crud, database

DUMMY = [
    ("Aarav Sharma", "2004-05-17", "aarav@example.com", "+91 98765 43210", "Computer Science", "Delhi", "2022-08-01"),
    ("Diya Patel", "2005-11-02", "diya@example.com", None, "Data Science", "Ahmedabad", "2023-08-01"),
    ("Rohan Gupta", "2003-01-25", "rohan@example.com", "+91 91234 56789", "Computer Science", "Noida", "2021-08-01"),
    ("Ananya Singh", "2006-03-14", "ananya@example.com", None, "Electronics", "Lucknow", "2024-08-01"),
    ("Kabir Mehta", "2005-07-30", None, "+91 99887 76655", "Data Science", "Mumbai", "2023-08-01"),
    ("Isha Verma", "2002-12-09", "isha@example.com", None, "Mechanical", "Jaipur", "2020-08-01"),
    ("Vikram Rao", "2006-09-21", "vikram@example.com", "+91 90000 11122", "Computer Science", "Pune", "2024-08-01"),
    ("Meera Nair", "2004-02-11", "meera@example.com", None, "Electronics", "Kochi", "2022-08-01"),
]

if __name__ == "__main__":
    database.init_db()
    db = database.get_connection()
    if crud.count_students(db):
        print("Table already has data - skipping seed.")
    else:
        keys = ["name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date"]
        for row in DUMMY:
            crud.create_student(db, dict(zip(keys, row)))
        print(f"Inserted {len(DUMMY)} dummy students.")
    db.close()
