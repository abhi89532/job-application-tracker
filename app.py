import os
import sqlite3
from datetime import date
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "applications.db"
STATUSES = ["Applied", "Interview", "Offer", "Rejected", "Withdrawn"]


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        DATABASE=str(DATABASE),
    )

    if test_config:
        app.config.update(test_config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                position TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Applied',
                application_date TEXT NOT NULL,
                job_url TEXT,
                location TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.commit()

    def validate_form(form):
        data = {
            "company": form.get("company", "").strip(),
            "position": form.get("position", "").strip(),
            "status": form.get("status", "Applied").strip(),
            "application_date": form.get("application_date", "").strip(),
            "job_url": form.get("job_url", "").strip(),
            "location": form.get("location", "").strip(),
            "notes": form.get("notes", "").strip(),
        }
        errors = []
        if not data["company"]:
            errors.append("Company is required.")
        if not data["position"]:
            errors.append("Position is required.")
        if data["status"] not in STATUSES:
            errors.append("Choose a valid status.")
        try:
            date.fromisoformat(data["application_date"])
        except ValueError:
            errors.append("Choose a valid application date.")
        if data["job_url"] and not data["job_url"].startswith(("http://", "https://")):
            errors.append("Job URL must begin with http:// or https://.")
        return data, errors

    @app.route("/")
    def index():
        query = request.args.get("q", "").strip()
        status = request.args.get("status", "").strip()
        sql = "SELECT * FROM applications WHERE 1 = 1"
        params = []

        if query:
            sql += " AND (company LIKE ? OR position LIKE ? OR location LIKE ?)"
            term = f"%{query}%"
            params.extend([term, term, term])
        if status in STATUSES:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY application_date DESC, id DESC"

        db = get_db()
        applications = db.execute(sql, params).fetchall()
        counts = {
            row["status"]: row["count"]
            for row in db.execute(
                "SELECT status, COUNT(*) AS count FROM applications GROUP BY status"
            ).fetchall()
        }
        return render_template(
            "index.html",
            applications=applications,
            counts=counts,
            statuses=STATUSES,
            selected_status=status,
            query=query,
        )

    @app.route("/applications/new", methods=("GET", "POST"))
    def add_application():
        if request.method == "POST":
            data, errors = validate_form(request.form)
            if not errors:
                db = get_db()
                db.execute(
                    """
                    INSERT INTO applications
                    (company, position, status, application_date, job_url, location, notes)
                    VALUES (:company, :position, :status, :application_date, :job_url, :location, :notes)
                    """,
                    data,
                )
                db.commit()
                flash("Application added successfully.", "success")
                return redirect(url_for("index"))
            for error in errors:
                flash(error, "error")
        return render_template(
            "form.html",
            application=request.form if request.method == "POST" else None,
            statuses=STATUSES,
            today=date.today().isoformat(),
            title="Add application",
        )

    @app.route("/applications/<int:application_id>/edit", methods=("GET", "POST"))
    def edit_application(application_id):
        db = get_db()
        application = db.execute(
            "SELECT * FROM applications WHERE id = ?", (application_id,)
        ).fetchone()
        if application is None:
            return ("Application not found", 404)

        if request.method == "POST":
            data, errors = validate_form(request.form)
            if not errors:
                data["id"] = application_id
                db.execute(
                    """
                    UPDATE applications
                    SET company = :company, position = :position, status = :status,
                        application_date = :application_date, job_url = :job_url,
                        location = :location, notes = :notes
                    WHERE id = :id
                    """,
                    data,
                )
                db.commit()
                flash("Application updated successfully.", "success")
                return redirect(url_for("index"))
            for error in errors:
                flash(error, "error")
            application = request.form

        return render_template(
            "form.html",
            application=application,
            statuses=STATUSES,
            today=date.today().isoformat(),
            title="Edit application",
        )

    @app.post("/applications/<int:application_id>/delete")
    def delete_application(application_id):
        db = get_db()
        cursor = db.execute("DELETE FROM applications WHERE id = ?", (application_id,))
        db.commit()
        if cursor.rowcount:
            flash("Application deleted.", "success")
        else:
            flash("Application not found.", "error")
        return redirect(url_for("index"))

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Database initialized.")

    with app.app_context():
        init_db()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
