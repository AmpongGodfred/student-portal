# app.py
# The heart of the application.
# Contains all configuration and route functions (one per page).

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from functools import wraps
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
# Admin login credentials
# In a real app these would be stored securely in environment variables
app.config["ADMIN_USERNAME"] = "admin"
app.config["ADMIN_PASSWORD"] = "portal2024"

app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")

# Automatically create the uploads folder if it doesn't exist
# This is important on Render because the folder isn't in GitHub
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
# exist_ok=True means "don't crash if the folder already exists"

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

# ── Helper: Login Required Decorator ───────────────────────────────
def login_required(f):
    """
    This is a decorator — a function that wraps around other functions.
    Add @login_required above any route to protect it.
    If the user is not logged in, they get redirected to the login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if "admin" key exists in the session
        if "admin" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

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
@login_required
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
@login_required
def students():
    """
    Fetches students from the database with optional search/filter.
    Search values come from the URL query string e.g:
    /students?name=john&status=admitted&gender=male&jamb=280
    request.args is a dictionary of everything in the URL after the ?
    """

    # ── Read filter values from the URL (empty string if not provided) ──
    name   = request.args.get("name", "").strip()
    status = request.args.get("status", "").strip()
    gender = request.args.get("gender", "").strip()
    jamb   = request.args.get("jamb", "").strip()

    # ── Start with all students (we'll narrow it down below) ──
    # query is like saying "SELECT * FROM students" in SQL
    query = Student.query

    # ── Apply filters only if the user provided a value ──

    if name:
        # ilike() is case-insensitive "contains" search
        # % means "anything before or after" the search term
        # e.g. searching "john" matches "John Amadi", "Johnny", etc.
        query = query.filter(
            (Student.first_name.ilike(f"%{name}%")) |
            (Student.last_name.ilike(f"%{name}%"))
            # | means OR — match first name OR last name
        )

    if status:
        # Exact match for status ("admitted", "undecided", "not admitted")
        query = query.filter(Student.status == status)

    if gender:
        # Exact match for gender
        query = query.filter(Student.gender == gender)

    if jamb:
        # Match exact JAMB score (convert string to integer first)
        query = query.filter(Student.jamb_score == int(jamb))

    # ── Execute the query and get the results ──
    # .all() runs the final query and returns a list of matching students
    all_students = query.all()

    # Pass both the students AND the filter values back to the template
    # so the search fields stay filled after searching
    return render_template(
        "students.html",
        students=all_students,
        name=name,
        status=status,
        gender=gender,
        jamb=jamb
    )


# ── ROUTE 4: Student Detail Page ───────────────────────────────────
@app.route("/student/<int:student_id>")
@login_required
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
@login_required
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

# ── ROUTE 6: Edit Student ───────────────────────────────────────────
@app.route("/edit-student/<int:student_id>", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    """
    GET  → fetch the student from database and show a pre-filled form
    POST → receive the updated form data and save changes to database
    """

    # Fetch the student or return 404 if not found
    student = Student.query.get_or_404(student_id)

    if request.method == "POST":
        # ── Update all text fields with new values from the form ──
        student.first_name  = request.form.get("first_name")
        student.middle_name = request.form.get("middle_name")
        student.last_name   = request.form.get("last_name")
        student.email       = request.form.get("email")
        student.dob         = request.form.get("dob")
        student.gender      = request.form.get("gender")
        student.phone       = request.form.get("phone")
        student.address     = request.form.get("address")
        student.state       = request.form.get("state")
        student.lga         = request.form.get("local-govt-area")
        student.next_of_kin = request.form.get("next_of_kin")
        student.jamb_score  = int(request.form.get("jamb_score"))

        # ── Handle image update (only if a new image was uploaded) ──
        image = request.files.get("image")

        if image and image.filename != "" and allowed_file(image.filename):
            # A new image was uploaded — save it and update the filename
            filename = secure_filename(image.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image.save(save_path)
            student.image = filename
        # If no new image uploaded, keep the existing one (do nothing)

        # ── Save the changes to the database ──
        # No need for db.session.add() here because the student object
        # is already in the database — we just modified it directly
        db.session.commit()

        flash("Student record updated successfully!", "success")
        return redirect(url_for("students"))

    # GET request — just show the pre-filled edit form
    return render_template("edit.html", student=student)


# ── ROUTE 7: Delete Student ─────────────────────────────────────────
@app.route("/delete-student/<int:student_id>", methods=["POST"])
@login_required
def delete_student(student_id):
    """
    Deletes a student record from the database.
    Only accepts POST requests for security —
    you don't want someone deleting records just by visiting a URL!
    """

    # Fetch the student or return 404 if not found
    student = Student.query.get_or_404(student_id)

    # Delete the student record from the database
    db.session.delete(student)
    db.session.commit()

    flash("Student record deleted successfully!", "success")
    return redirect(url_for("students"))



# ── ROUTE 8: Login Page ─────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    GET  → show the login form
    POST → check credentials, create session if correct
    """

    # If already logged in, go straight to students table
    if "admin" in session:
        return redirect(url_for("students"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Check if credentials match what we set in config
        if (username == app.config["ADMIN_USERNAME"] and
                password == app.config["ADMIN_PASSWORD"]):

            # Create a session — this is like giving the user a pass
            # session is a dictionary that persists across requests
            session["admin"] = username
            flash("Welcome back, Admin!", "success")
            return redirect(url_for("students"))
        else:
            # Wrong credentials
            flash("Invalid username or password. Try again.", "error")

    return render_template("login.html")


# ── ROUTE 9: Logout ─────────────────────────────────────────────────
@app.route("/logout")
def logout():
    """
    Clears the session (removes the pass) and redirects to login page.
    """
    session.pop("admin", None)
    # pop() removes the "admin" key from the session
    # None means don't crash if "admin" isn't in the session
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ── Run the app ────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)