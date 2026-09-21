import sqlite3

from app import create_app


SAMPLE_APPLICATIONS = [
    ("Northstar Labs", "Software Engineer", "Applied", "2026-09-18", "Remote", "Follow up next week."),
    ("BrightPath", "Python Developer", "Interview", "2026-09-12", "Austin, TX", "Technical interview scheduled."),
    ("CloudArc", "Junior Backend Engineer", "Offer", "2026-09-05", "Chicago, IL", "Review offer details."),
]


app = create_app()
with sqlite3.connect(app.config["DATABASE"]) as db:
    db.executemany(
        """
        INSERT INTO applications
        (company, position, status, application_date, location, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        SAMPLE_APPLICATIONS,
    )
    db.commit()
    print(f"Added {len(SAMPLE_APPLICATIONS)} sample applications.")
