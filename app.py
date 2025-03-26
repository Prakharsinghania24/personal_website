from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3  # Import SQLite

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Enables flash messages

# Function to connect to SQLite database
def get_db_connection():
    conn = sqlite3.connect("personal_site.db")
    conn.row_factory = sqlite3.Row  # Enables column access by name
    return conn

# Create a table for blog posts (Run once)
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
    conn.commit()
    conn.close()

# Call this function when app starts
create_table()

# Home route with Blog Preview
@app.route("/")
def home():
    conn = get_db_connection()
    posts = conn.execute("SELECT * FROM posts ORDER BY created DESC LIMIT 3").fetchall()  # Fetch latest 3 posts
    conn.close()
    return render_template("index.html", posts=posts)

# Blog route - Display all blog posts
@app.route("/blog")
def blog():
    conn = get_db_connection()
    posts = conn.execute("SELECT * FROM posts ORDER BY created DESC").fetchall()
    conn.close()
    return render_template("blog.html", posts=posts)

# Route to add a new blog post via a form
@app.route("/new_post", methods=["GET", "POST"])
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

# Route to edit a blog post
@app.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
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

# Route to delete a blog post
@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    flash("Post deleted successfully!", "success")
    return redirect(url_for("blog"))

if __name__ == "__main__":
    app.run(debug=True)
