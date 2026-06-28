# models.py
# This file defines the structure of our database.
# Think of each class here as a table in the database,
# and each variable inside it as a column in that table.

from flask_sqlalchemy import SQLAlchemy

# Create the SQLAlchemy object.
# We'll connect it to the Flask app later in app.py.
db = SQLAlchemy()

# This class represents the "students" table in our database.
class Student(db.Model):
    __tablename__ = "students"  # The actual table name in the database

    # Each line below is a column in the table.
    # db.Column() defines the column, and we specify the data type.

    id           = db.Column(db.Integer, primary_key=True)
    # primary_key=True means this is the unique ID for each student (auto-increments)

    image        = db.Column(db.String(200))           # stores the filename of the photo
    first_name   = db.Column(db.String(100), nullable=False)  # nullable=False = required
    middle_name  = db.Column(db.String(100))
    last_name    = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(150), nullable=False)
    dob          = db.Column(db.String(20),  nullable=False)   # date of birth
    gender       = db.Column(db.String(10),  nullable=False)
    phone        = db.Column(db.String(20),  nullable=False)
    address      = db.Column(db.Text,        nullable=False)
    state        = db.Column(db.String(100), nullable=False)
    lga          = db.Column(db.String(100), nullable=False)   # local govt area
    next_of_kin  = db.Column(db.String(150), nullable=False)
    jamb_score   = db.Column(db.Integer,     nullable=False)
    status       = db.Column(db.String(20),  default="undecided")
    # status starts as "undecided" for every new student