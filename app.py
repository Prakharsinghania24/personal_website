from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key"

DATABASE = "personal_site.db"
ABOUT_FILE = "about_me.txt"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "pass123"

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/investing")
def investing():
    return render_template("investing.html")

@app.route("/article")
def article():
    return render_template("article.html")

def create_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            link TEXT NOT NULL,
            image_filename TEXT
        )
    """)
    conn.commit()
    conn.close()

create_table()

@app.route("/resume")
def resume():
    return render_template("resume.html")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Admin access required.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def home():
    conn = get_db_connection()
    posts = conn.execute("SELECT * FROM posts ORDER BY created DESC LIMIT 3").fetchall()
    conn.close()

    if os.path.exists(ABOUT_FILE):
        with open(ABOUT_FILE, "r", encoding="utf-8") as f:
            about_text = f.read()
    else:
        about_text = "About Me content not found."

    return render_template("index.html", posts=posts, about_text=about_text)

@app.route("/blog")
def blog():
    conn = get_db_connection()
    posts = conn.execute("SELECT * FROM posts ORDER BY created DESC").fetchall()
    conn.close()
    return render_template("blog.html", posts=posts)

@app.route("/new_post", methods=["GET", "POST"])
@login_required
def new_post():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        if not title or not content:
            flash("Title and Content are required!", "danger")
        else:
            conn = get_db_connection()
            conn.execute("INSERT INTO posts (title, content) VALUES (?, ?)", (title, content))
            conn.commit()
            conn.close()
            flash("New post added successfully!", "success")
            return redirect(url_for("blog"))
    return render_template("new_post.html")

@app.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    conn = get_db_connection()
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        conn.execute("UPDATE posts SET title = ?, content = ? WHERE id = ?", (title, content, post_id))
        conn.commit()
        conn.close()
        flash("Post updated successfully!", "success")
        return redirect(url_for("blog"))
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    if post is None:
        flash("Post not found!", "danger")
        return redirect(url_for("blog"))
    return render_template("edit_post.html", post=post)

@app.route("/delete_post/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    flash("Post deleted successfully!", "success")
    return redirect(url_for("blog"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            flash("Logged in successfully!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials.", "danger")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Logged out.", "info")
    return redirect(url_for("home"))

@app.route("/admin")
@login_required
def admin_dashboard():
    return render_template("admin_dashboard.html")

@app.route("/admin/edit_about", methods=["GET", "POST"])
@login_required
def edit_about():
    if request.method == "POST":
        new_content = request.form["about_content"]
        with open(ABOUT_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        flash("About Me updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))
    if os.path.exists(ABOUT_FILE):
        with open(ABOUT_FILE, "r", encoding="utf-8") as f:
            about_text = f.read()
    else:
        about_text = ""
    return render_template("edit_about.html", about_content=about_text)

@app.route("/admin/achievements")
@login_required
def admin_achievements():
    conn = get_db_connection()
    achievements = conn.execute("SELECT * FROM achievements ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_achievements.html", achievements=achievements)

@app.route("/admin/achievements/new", methods=["GET", "POST"])
@login_required
def new_achievement():
    if request.method == "POST":
        title = request.form["title"]
        summary = request.form["summary"]
        link = request.form["link"]
        image = request.files["image"]
        filename = None

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db_connection()
        conn.execute("INSERT INTO achievements (title, summary, link, image_filename) VALUES (?, ?, ?, ?)",
                     (title, summary, link, filename))
        conn.commit()
        conn.close()
        flash("Achievement added successfully!", "success")
        return redirect(url_for("admin_achievements"))

    return render_template("new_achievement.html")

@app.route("/admin/achievements/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_achievement(id):
    conn = get_db_connection()
    achievement = conn.execute("SELECT * FROM achievements WHERE id = ?", (id,)).fetchone()

    if not achievement:
        conn.close()
        flash("Achievement not found.", "danger")
        return redirect(url_for("admin_achievements"))

    if request.method == "POST":
        title = request.form["title"]
        summary = request.form["summary"]
        link = request.form["link"]

        image = request.files["image"]
        filename = achievement["image_filename"]

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn.execute(
            "UPDATE achievements SET title = ?, summary = ?, link = ?, image_filename = ? WHERE id = ?",
            (title, summary, link, filename, id)
        )
        conn.commit()
        conn.close()
        flash("Achievement updated!", "success")
        return redirect(url_for("admin_achievements"))

    conn.close()
    return render_template("edit_achievement.html", achievement=achievement)

@app.route("/admin/achievements/delete/<int:id>", methods=["POST"])
@login_required
def delete_achievement(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM achievements WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Achievement deleted.", "info")
    return redirect(url_for("admin_achievements"))

@app.route("/achievements")
def achievements():
    conn = get_db_connection()
    achievements = conn.execute("SELECT * FROM achievements ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("achievements.html", achievements=achievements)

if __name__ == "__main__":
    app.run(debug=True)
