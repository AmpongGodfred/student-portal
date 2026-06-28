# app.py
# The heart of the application.
# Contains all configuration and route functions (one per page).

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Student
from werkzeug.utils import secure_filename  # helps sanitize uploaded filenames

# ── App configuration ──────────────────────────────────────────────
app = Flask(__name__)



# Use environment variable for database URL in production (Render),
# fall back to local SQLite for development on your PC
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///students.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your-secret-key-here"
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")

# Only allow image file types to be uploaded
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# ── Connect database to app ────────────────────────────────────────
db.init_app(app)

with app.app_context():
    db.create_all()


# ── Helper function ────────────────────────────────────────────────
def allowed_file(filename):
    """
    Checks if the uploaded file has an allowed image extension.
    e.g. "photo.jpg" → True | "document.pdf" → False
    """
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── ROUTE 1: Landing Page ──────────────────────────────────────────
@app.route("/")
def index():
    """
    Renders the landing page (index.html).
    No data needed — just display the page.
    """
    return render_template("index.html")


# ── ROUTE 2: Portal Form Page ──────────────────────────────────────
@app.route("/form", methods=["GET", "POST"])
def form():
    """
    GET  → just show the empty form
    POST → receive the form data, save to database, redirect to students page

    methods=["GET", "POST"] means this route handles both:
    - GET:  browser is just visiting the page (show the form)
    - POST: browser is submitting the form (process the data)
    """

    if request.method == "POST":
        # ── Step 1: Grab all text fields from the submitted form ──
        # request.form is a dictionary of everything the user typed
        first_name  = request.form.get("first_name")
        middle_name = request.form.get("middle_name")
        last_name   = request.form.get("last_name")
        email       = request.form.get("email")
        dob         = request.form.get("dob")
        gender      = request.form.get("gender")
        phone       = request.form.get("phone")
        address     = request.form.get("address")
        state       = request.form.get("state")
        lga         = request.form.get("local-govt-area")
        next_of_kin = request.form.get("next_of_kin")
        jamb_score  = request.form.get("jamb_score")

        # ── Step 2: Handle the uploaded image ────────────────────
        # request.files holds any uploaded files
        image = request.files.get("image")

        # Basic validation: make sure an image was actually uploaded
        if not image or image.filename == "":
            flash("Please upload a profile image.", "error")
            return redirect(url_for("form"))

        # Check the file type is an allowed image format
        if not allowed_file(image.filename):
            flash("Only image files (jpg, png, gif) are allowed.", "error")
            return redirect(url_for("form"))

        # secure_filename() cleans up the filename to prevent any
        # security issues (e.g. someone uploading a file called "../../hack.py")
        filename = secure_filename(image.filename)

        # Build the full path where the image will be saved on disk
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # Actually save the image file into static/uploads/
        image.save(save_path)

        # ── Step 3: Save all the data into the database ───────────
        # Create a new Student object with all the form values
        new_student = Student(
            image       = filename,       # just the filename, not the full path
            first_name  = first_name,
            middle_name = middle_name,
            last_name   = last_name,
            email       = email,
            dob         = dob,
            gender      = gender,
            phone       = phone,
            address     = address,
            state       = state,
            lga         = lga,
            next_of_kin = next_of_kin,
            jamb_score  = int(jamb_score),  # convert string to integer
            status      = "undecided"        # default status for every new student
        )

        # Add the new student to the database session (like a staging area)
        db.session.add(new_student)

        # Commit = actually write it to the database permanently
        db.session.commit()

        # ── Step 4: Redirect to the students table page ───────────
        # redirect() sends the user to a different URL
        # url_for("students") generates the URL for the students() function
        return redirect(url_for("students"))

    # If it's a GET request (just visiting the page), show the empty form
    return render_template("form.html")


# ── ROUTE 3: Students Table Page ───────────────────────────────────
@app.route("/students")
def students():
    """
    Fetches ALL students from the database and
    passes them to the template to be displayed in a table.
    """

    # Query the database for every row in the students table
    # .all() returns a Python list of Student objects
    all_students = Student.query.all()

    # render_template() fills students.html with the data
    # The variable name on the LEFT is what the template uses: {{ students }}
    # The variable on the RIGHT is the Python variable we just created
    return render_template("students.html", students=all_students)


# ── ROUTE 4: Student Detail Page ───────────────────────────────────
@app.route("/student/<int:student_id>")
def detail(student_id):
    """
    Fetches ONE specific student by their ID and displays their full profile.

    <int:student_id> in the URL is a variable — Flask captures whatever
    number is in the URL and passes it into the function.
    e.g. visiting /student/3 → student_id = 3
    """

    # Fetch the student with this ID, or show a 404 page if not found
    student = Student.query.get_or_404(student_id)

    return render_template("detail.html", student=student)


# ── ROUTE 5: Update Admission Status (Async/AJAX) ──────────────────
@app.route("/update-status/<int:student_id>", methods=["POST"])
def update_status(student_id):
    """
    This route is NOT a visible page — it's called invisibly by JavaScript.
    When the user changes the status dropdown on the detail page,
    JavaScript sends a request here to update the database WITHOUT
    reloading the whole page. This is the "async" part of the project.

    It returns JSON (a simple data format) instead of HTML.
    """

    # Get the student from the database
    student = Student.query.get_or_404(student_id)

    # request.json contains the data JavaScript sent us
    new_status = request.json.get("status")

    # Update the student's status in the database
    student.status = new_status
    db.session.commit()

    # Send back a JSON response so JavaScript knows it worked
    return jsonify({"message": "Status updated successfully", "status": new_status})


# ── Run the app ────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)