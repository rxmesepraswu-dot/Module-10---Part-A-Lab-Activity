import csv
import os
from contextlib import asynccontextmanager
from io import StringIO
from urllib.parse import quote_plus
import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import Response

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    raise RuntimeError("Database configuration is incomplete. Please check your .env file.")

DATABASE_URL = (
    f"postgresql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# MODIFY THE SQL QUERY BELOW TO RETURN THE REQUIRED SUMMARY DATA ----------------------------------
SUMMARY_SQL = """

"""
# END OF MODIFICATION ---------------------------------

# !!!!!!!!!!!!DO NOT CHANGE THE CODES BELOW. They are used in the grading script to verify your work.!!!!!!!!!!!!!!!!
CSV_COLUMNS = ["course_code", "course_title", "total_students"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=2,
        statement_cache_size=0
    )
    yield
    await app.state.pool.close()

app = FastAPI(title="Course Enrollment Report", lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "ok", "csv": "/courses/export/csv"}

async def fetch_all(sql: str):
    async with app.state.pool.acquire() as conn:
        rows = await conn.fetch(sql)
    return [dict(row) for row in rows]

@app.get("/students")
async def list_students():
    return await fetch_all(
        """
        SELECT student_id, first_name, middle_name, last_name, email
        FROM students
        ORDER BY student_id
        """
    )

@app.get("/courses")
async def list_courses():
    return await fetch_all(
        """
        SELECT course_id, course_code, course_title, units
        FROM courses
        ORDER BY course_id
        """
    )

@app.get("/enrollments")
async def list_enrollments():
    return await fetch_all(
        """
        SELECT e.enrollment_id,
               e.student_id,
               s.first_name || ' ' || s.last_name AS student_name,
               e.course_id,
               c.course_code,
               e.school_year,
               e.semester,
               e.status
        FROM enrollments e
        JOIN students s ON s.student_id = e.student_id
        JOIN courses  c ON c.course_id  = e.course_id
        ORDER BY e.enrollment_id
        """
    )

async def fetch_summary():
    async with app.state.pool.acquire() as conn:
        return await conn.fetch(SUMMARY_SQL)

@app.get("/courses/summary")
async def courses_summary():
    # For Debugging: returns the summary as JSON instead of CSV
    rows = await fetch_summary()
    return [dict(row) for row in rows]

@app.get("/courses/export/csv")
async def export_courses_csv():
    rows = await fetch_summary()
    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow(CSV_COLUMNS)

    for row in rows:
        writer.writerow([
            row["course_code"],
            row["course_title"],   
            row["total_students"],
        ])

    buffer.seek(0)

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=courses_summary.csv"},
    )