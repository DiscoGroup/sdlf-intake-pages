#!/usr/bin/env python3
import csv
import io
import json
import os
import smtplib
import sqlite3
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.environ.get("DATABASE_PATH", DATA_DIR / "submissions.sqlite"))
DATABASE_URL = os.environ.get("DATABASE_URL", "")
EXPORT_EMAILS = [email.strip() for email in os.environ.get("EXPORT_EMAILS", "chaz@vnsfirm.com").split(",") if email.strip()]

FIELDS = [
    "id",
    "created_at",
    "caseCategory",
    "leadStatus",
    "leadScore",
    "qualificationSummary",
    "fullName",
    "phone",
    "email",
    "injuryType",
    "injured",
    "accidentDate",
    "medicalBills",
    "lostWages",
    "propertyDamage",
    "fault",
    "treatment",
    "bestTime",
    "estimateLow",
    "estimateHigh",
    "caseSummary",
    "qualificationData",
    "page",
]

EXPORT_SELECT = """
SELECT
    id,
    created_at,
    caseCategory AS "caseCategory",
    leadStatus AS "leadStatus",
    leadScore AS "leadScore",
    qualificationSummary AS "qualificationSummary",
    fullName AS "fullName",
    phone,
    email,
    injuryType AS "injuryType",
    injured,
    accidentDate AS "accidentDate",
    medicalBills AS "medicalBills",
    lostWages AS "lostWages",
    propertyDamage AS "propertyDamage",
    fault,
    treatment,
    bestTime AS "bestTime",
    estimateLow AS "estimateLow",
    estimateHigh AS "estimateHigh",
    caseSummary AS "caseSummary",
    qualificationData AS "qualificationData",
    page
FROM submissions
ORDER BY id DESC
"""


def db():
    DATA_DIR.mkdir(exist_ok=True)
    if DATABASE_URL:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as error:
            raise RuntimeError("DATABASE_URL is set, but psycopg is not installed.") from error
        connection = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        ensure_schema(connection, "postgres")
        return connection
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    ensure_schema(connection, "sqlite")
    return connection


def ensure_schema(connection, dialect):
    id_definition = "SERIAL PRIMARY KEY" if dialect == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS submissions (
            id {id_definition},
            created_at TEXT NOT NULL,
            caseCategory TEXT,
            leadStatus TEXT,
            leadScore REAL DEFAULT 0,
            qualificationSummary TEXT,
            fullName TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            injuryType TEXT,
            injured TEXT,
            accidentDate TEXT,
            medicalBills REAL DEFAULT 0,
            lostWages REAL DEFAULT 0,
            propertyDamage REAL DEFAULT 0,
            fault TEXT,
            treatment TEXT,
            bestTime TEXT,
            estimateLow REAL DEFAULT 0,
            estimateHigh REAL DEFAULT 0,
            caseSummary TEXT,
            qualificationData TEXT,
            page TEXT
        )
        """
    )
    if dialect == "postgres":
        existing_columns = {
            row["column_name"]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'submissions'
                """
            )
        }
    else:
        existing_columns = {row["name"] for row in connection.execute("PRAGMA table_info(submissions)")}
    column_defaults = {
        "caseCategory": "TEXT",
        "leadStatus": "TEXT",
        "leadScore": "REAL DEFAULT 0",
        "qualificationSummary": "TEXT",
        "qualificationData": "TEXT",
    }
    for column, column_type in column_defaults.items():
        if column not in existing_columns:
            connection.execute(f"ALTER TABLE submissions ADD COLUMN {column} {column_type}")
    connection.commit()


def as_number(value):
    try:
      return float(value or 0)
    except (TypeError, ValueError):
      return 0


def insert_submission(payload):
    created_at = datetime.now(timezone.utc).isoformat()
    row = {
        "created_at": created_at,
        "caseCategory": payload.get("caseCategory", ""),
        "leadStatus": payload.get("leadStatus", ""),
        "leadScore": as_number(payload.get("leadScore")),
        "qualificationSummary": payload.get("qualificationSummary", ""),
        "fullName": str(payload.get("fullName", "")).strip(),
        "phone": str(payload.get("phone", "")).strip(),
        "email": str(payload.get("email", "")).strip(),
        "injuryType": payload.get("injuryType", ""),
        "injured": payload.get("injured", ""),
        "accidentDate": payload.get("accidentDate", ""),
        "medicalBills": as_number(payload.get("medicalBills")),
        "lostWages": as_number(payload.get("lostWages")),
        "propertyDamage": as_number(payload.get("propertyDamage")),
        "fault": payload.get("fault", ""),
        "treatment": payload.get("treatment", ""),
        "bestTime": payload.get("bestTime", ""),
        "estimateLow": as_number(payload.get("estimateLow")),
        "estimateHigh": as_number(payload.get("estimateHigh")),
        "caseSummary": payload.get("caseSummary", ""),
        "qualificationData": json.dumps(payload.get("qualificationData", {}), ensure_ascii=True),
        "page": payload.get("page", ""),
    }

    if not row["fullName"] or not row["phone"] or not row["email"]:
        raise ValueError("Name, phone, and email are required.")

    insert_columns = """
        created_at, caseCategory, leadStatus, leadScore, qualificationSummary,
        fullName, phone, email, injuryType, injured, accidentDate,
        medicalBills, lostWages, propertyDamage, fault, treatment, bestTime,
        estimateLow, estimateHigh, caseSummary, qualificationData, page
    """
    if DATABASE_URL:
        values = """
            %(created_at)s, %(caseCategory)s, %(leadStatus)s, %(leadScore)s, %(qualificationSummary)s,
            %(fullName)s, %(phone)s, %(email)s, %(injuryType)s, %(injured)s, %(accidentDate)s,
            %(medicalBills)s, %(lostWages)s, %(propertyDamage)s, %(fault)s, %(treatment)s, %(bestTime)s,
            %(estimateLow)s, %(estimateHigh)s, %(caseSummary)s, %(qualificationData)s, %(page)s
        """
        sql = f"INSERT INTO submissions ({insert_columns}) VALUES ({values}) RETURNING id"
    else:
        values = """
            :created_at, :caseCategory, :leadStatus, :leadScore, :qualificationSummary,
            :fullName, :phone, :email, :injuryType, :injured, :accidentDate,
            :medicalBills, :lostWages, :propertyDamage, :fault, :treatment, :bestTime,
            :estimateLow, :estimateHigh, :caseSummary, :qualificationData, :page
        """
        sql = f"INSERT INTO submissions ({insert_columns}) VALUES ({values})"

    with db() as connection:
        cursor = connection.execute(sql, row)
        if DATABASE_URL:
            row["id"] = cursor.fetchone()["id"]
        else:
            row["id"] = cursor.lastrowid
        connection.commit()
    return row


def export_csv(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in FIELDS})
    return output.getvalue()


def send_export_email(row):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_from = os.environ.get("SMTP_FROM") or os.environ.get("SMTP_USER")
    if not smtp_host or not smtp_from or not EXPORT_EMAILS:
        return False

    csv_body = export_csv([row])
    message = EmailMessage()
    message["Subject"] = f"New SDLF claim calculator submission: {row['fullName']}"
    message["From"] = smtp_from
    message["To"] = ", ".join(EXPORT_EMAILS)
    message.set_content(
        "\n".join(
            [
                "A new injury claim calculator submission was saved.",
                "",
                f"Name: {row['fullName']}",
                f"Phone: {row['phone']}",
                f"Email: {row['email']}",
                f"Category: {row.get('caseCategory', '')}",
                f"Lead status: {row.get('leadStatus', '')} ({row.get('leadScore', 0):.0f})",
                f"Qualification: {row.get('qualificationSummary', '')}",
                f"Estimate: ${row['estimateLow']:,.0f} - ${row['estimateHigh']:,.0f}",
                "",
                "A CSV export for this submission is attached.",
            ]
        )
    )
    message.add_attachment(csv_body, subtype="csv", filename=f"claim-submission-{row['id']}.csv")

    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")

    with smtplib.SMTP(smtp_host, port, timeout=15) as smtp:
        if os.environ.get("SMTP_STARTTLS", "true").lower() != "false":
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)
    return True


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def send_json(self, status, payload):
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/export":
            with db() as connection:
                rows = [dict(row) for row in connection.execute(EXPORT_SELECT)]
            body = export_csv(rows).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition", "attachment; filename=claim-submissions.csv")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/submissions":
            self.send_json(404, {"error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            row = insert_submission(payload)
            try:
                email_sent = send_export_email(row)
                email_error = None
            except Exception as error:
                email_sent = False
                email_error = str(error)
                print(f"Email export failed for submission {row['id']}: {error}", file=sys.stderr)
            self.send_json(201, {"ok": True, "id": row["id"], "emailSent": email_sent, "emailError": email_error})
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
        except Exception as error:
            self.send_json(500, {"error": f"Submission saved or export failed: {error}"})


def main():
    db().close()
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Serving SDLF calculator at http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
