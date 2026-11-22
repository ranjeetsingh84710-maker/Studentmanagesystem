from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "student_management_secret_key"

# Database connection
def get_db():
    conn = sqlite3.connect(
        "students.db",
        timeout=30,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn
def enable_wal():
    conn = get_db()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.close()

# Create database table

def init_db():
    conn = get_db()

    # Students Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Attendance Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    # Marks Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            total_marks INTEGER NOT NULL,
            obtained_marks INTEGER NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)
        # Courses Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT NOT NULL,
            course_code TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            duration TEXT NOT NULL
        )
    """)
        # Fees Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            total_fee REAL NOT NULL,
            paid_amount REAL NOT NULL DEFAULT 0,
            due_date TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)
        # Library Books Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE,
            quantity INTEGER NOT NULL DEFAULT 1
        )
    """)

    # Book Issue Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS book_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT DEFAULT 'Issued',
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
        # Admin and Faculty Users Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS staff_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'faculty')),
            UNIQUE(role, user_id),
            UNIQUE(role, email)
        )
    """)

    # Create Default Admin Account
    admin = conn.execute(
        "SELECT id FROM staff_users WHERE role = 'admin'"
    ).fetchone()

    if not admin:
        conn.execute("""
            INSERT INTO staff_users
            (user_id, name, email, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "admin",
            "Administrator",
            "admin@edumanage.com",
            generate_password_hash("Admin@123"),
            "admin"
        ))

    # Create Default Faculty Account
    faculty_user = conn.execute(
        "SELECT id FROM staff_users WHERE role = 'faculty'"
    ).fetchone()

    if not faculty_user:
        conn.execute("""
            INSERT INTO staff_users
            (user_id, name, email, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "faculty",
            "Faculty Member",
            "faculty@edumanage.com",
            generate_password_hash("Faculty@123"),
            "faculty"
        ))

    conn.commit()
    conn.close()



@app.route('/')
def home():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    role = request.args.get('role', 'student')

    if role not in ['student', 'admin', 'faculty']:
        return "Invalid login role", 400

    if request.method == 'POST':

        user_id = request.form.get('roll_number', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        conn = get_db()

        if role == 'student':

            user = conn.execute("""
                SELECT * FROM students
                WHERE roll_number = ? AND email = ?
            """, (user_id, email)).fetchone()

        else:

            user = conn.execute("""
                SELECT * FROM staff_users
                WHERE user_id = ? AND email = ? AND role = ?
            """, (user_id, email, role)).fetchone()

        conn.close()

        if user and check_password_hash(user['password'], password):

            session.clear()

            if role == 'student':
                session['student_id'] = user['id']

                flash("Student login successful!")
                return redirect(url_for('dashboard'))

            elif role == 'admin':
                session['staff_id'] = user['id']
                session['role'] = 'admin'

                flash("Admin login successful!")
                return redirect(url_for('admin'))

            elif role == 'faculty':
                session['staff_id'] = user['id']
                session['role'] = 'faculty'

                flash("Faculty login successful!")
                return redirect(url_for('faculty'))

        flash("Invalid ID, Email or Password.")
        return redirect(url_for('login', role=role))

    return render_template('login.html', role=role)



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        roll = request.form.get('roll_number')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        hashed_password = generate_password_hash(password)

        conn = get_db()

        try:
            conn.execute(
                """INSERT INTO students
                (roll_number, name, email, password)
                VALUES (?, ?, ?, ?)""",
                (roll, name, email, hashed_password)
            )
            conn.commit()
            flash("Registration successful!")
            return redirect(url_for('login', role='student'))

        except sqlite3.IntegrityError:
            flash("Roll Number or Email already exists.")

        finally:
            conn.close()

    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login', role='student'))

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (session['student_id'],)
    ).fetchone()
    conn.close()

    return render_template('dashboard.html', student=student)

@app.route('/profile')
def profile():
    if 'student_id' not in session:
        return redirect(url_for('login', role='student'))

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (session['student_id'],)
    ).fetchone()
    conn.close()

    return render_template('profile.html', student=student)

@app.route('/marks')
def marks():
    if 'student_id' not in session:
        return redirect(url_for('login', role='student'))

    conn = get_db()
    records = conn.execute(
        "SELECT * FROM marks WHERE student_id = ?",
        (session['student_id'],)
    ).fetchall()
    conn.close()

    return render_template('marks.html', records=records)
@app.route('/admin')
def admin():

    if session.get('role') != 'admin':
        return redirect(url_for('login', role='admin'))

    conn = get_db()

    students = conn.execute(
        "SELECT id, name, roll_number, email FROM students"
    ).fetchall()

    conn.close()

    return render_template('admin.html', students=students)
@app.route('/delete-student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM students WHERE id = ?",
        (student_id,)
    )
    conn.commit()
    conn.close()

    flash("Student deleted successfully!")
    return redirect(url_for('admin'))
@app.route('/edit-student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    conn = get_db()

    student = conn.execute(
        "SELECT * FROM students WHERE id = ?", (student_id,)
    ).fetchone()

    if not student:
        conn.close()
        return "Student not found", 404

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')

        conn.execute(
            "UPDATE students SET name = ?, email = ? WHERE id = ?",
            (name, email, student_id)
        )
        conn.commit()
        conn.close()

        flash("Student updated successfully!")
        return redirect(url_for('admin'))

    conn.close()
    return render_template('edit_student.html', student=student)
@app.route('/faculty')
def faculty():

    if session.get('role') != 'faculty':
        return redirect(url_for('login', role='faculty'))

    return render_template('faculty.html')
@app.route('/fees', methods=['GET', 'POST'])
def fees():
    conn = get_db()

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        total_fee = request.form.get('total_fee')
        paid_amount = request.form.get('paid_amount')
        due_date = request.form.get('due_date')

        if student_id and total_fee and paid_amount:
            total = float(total_fee)
            paid = float(paid_amount)

            if total > 0 and 0 <= paid <= total:
                conn.execute("""
                    INSERT INTO fees
                    (student_id, total_fee, paid_amount, due_date)
                    VALUES (?, ?, ?, ?)
                """, (student_id, total, paid, due_date))

                conn.commit()
                flash("Fees record added successfully!")

    students = conn.execute(
        "SELECT id, name, roll_number FROM students"
    ).fetchall()

    records = conn.execute("""
        SELECT fees.*, students.name, students.roll_number
        FROM fees
        JOIN students ON fees.student_id = students.id
        ORDER BY fees.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        'fees.html', students=students, records=records
    )

@app.route('/delete-course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    conn = get_db()

    conn.execute(
        "DELETE FROM courses WHERE id = ?",
        (course_id,)
    )

    conn.commit()
    conn.close()

    flash("Course deleted successfully!")
    return redirect(url_for('courses'))
@app.route('/edit-course/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    conn = get_db()

    course = conn.execute(
        "SELECT * FROM courses WHERE id = ?", (course_id,)
    ).fetchone()

    if not course:
        conn.close()
        return "Course not found", 404

    if request.method == 'POST':
        course_name = request.form.get('course_name')
        course_code = request.form.get('course_code')
        department = request.form.get('department')
        duration = request.form.get('duration')

        try:
            conn.execute("""
                UPDATE courses
                SET course_name = ?, course_code = ?,
                    department = ?, duration = ?
                WHERE id = ?
            """, (course_name, course_code, department, duration, course_id))

            conn.commit()
            flash("Course updated successfully!")
        except sqlite3.IntegrityError:
            flash("Course code already exists!")
        finally:
            conn.close()

        return redirect(url_for('courses'))

    conn.close()
    return render_template('edit_course.html', course=course)
@app.route('/add-marks', methods=['GET', 'POST'])
def add_marks():
    if 'student_id' not in session:
        return redirect(url_for('login', role='student'))

    if request.method == 'POST':
        subject = request.form.get('subject')
        total_marks = request.form.get('total_marks')
        obtained_marks = request.form.get('obtained_marks')

        if subject and total_marks and obtained_marks:
            total = int(total_marks)
            obtained = int(obtained_marks)

            if total > 0 and 0 <= obtained <= total:
                conn = get_db()
                conn.execute(
                    """INSERT INTO marks
                    (student_id, subject, total_marks, obtained_marks)
                    VALUES (?, ?, ?, ?)""",
                    (session['student_id'], subject, total, obtained)
                )
                conn.commit()
                conn.close()

                flash("Marks added successfully!")
                return redirect(url_for('marks'))

    return render_template('add_marks.html')

@app.route('/attendance')

def attendance():
    if 'student_id' not in session:
        return redirect(url_for('login', role='student'))

    conn = get_db()

    records = conn.execute(
        """SELECT * FROM attendance
        WHERE student_id = ?
        ORDER BY attendance_date DESC""",
        (session['student_id'],)
    ).fetchall()

    conn.close()

    return render_template('attendance.html', records=records)


@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():

    if 'student_id' not in session:
        return redirect(url_for('login', role='student'))

    subject = request.form.get('subject')
    attendance_date = request.form.get('attendance_date')
    status = request.form.get('status')

    if not subject or not attendance_date or status not in ['Present', 'Absent']:
        flash("Please fill all attendance fields.")
        return redirect(url_for('attendance'))

    conn = get_db()

    try:
        conn.execute(
            """INSERT INTO attendance
            (student_id, subject, attendance_date, status)
            VALUES (?, ?, ?, ?)""",
            (session['student_id'], subject, attendance_date, status)
        )

        conn.commit()
        flash("Attendance saved successfully!")

    except sqlite3.Error as e:
        conn.rollback()
        print("Attendance Error:", e)
        flash("Attendance could not be saved.")

    finally:
        conn.close()

    return redirect(url_for('attendance'))


@app.route('/add-attendance', methods=['GET', 'POST'])
def add_attendance():

    if 'student_id' not in session:
        return redirect(url_for('login', role='student'))

    if request.method == 'POST':

        subject = request.form.get('subject')
        attendance_date = request.form.get('attendance_date')
        status = request.form.get('status')

        if subject and attendance_date and status in ['Present', 'Absent']:

            conn = get_db()

            try:
                conn.execute(
                    """INSERT INTO attendance
                    (student_id, subject, attendance_date, status)
                    VALUES (?, ?, ?, ?)""",
                    (session['student_id'], subject, attendance_date, status)
                )

                conn.commit()
                flash("Attendance saved successfully!")

            finally:
                conn.close()

            return redirect(url_for('attendance'))

    return render_template('add_attendance.html')
@app.route('/logout')
def logout():

    session.clear()

    flash("You have been logged out successfully.")

    return redirect(url_for('home'))
if __name__ == '__main__':
    init_db()
    app.run(debug=True)