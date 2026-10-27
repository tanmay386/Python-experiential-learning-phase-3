import os, sqlite3, csv, io
from datetime import date, timedelta, datetime
from flask import Flask, request, redirect, url_for, flash, render_template_string, Response

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me")
DB_PATH = os.environ.get("DB_PATH", "attendance.db")

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    folder = os.path.dirname(DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL COLLATE NOCASE UNIQUE)")
        c.execute("CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, attendance_date TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('Present','Absent','Late')), UNIQUE(student_id, attendance_date))")

def valid_date(s):
    try: return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError): return None

def dates10():
    return [(date.today()-timedelta(days=i)).isoformat() for i in range(10)]

def report_rows(start, end):
    with db() as c:
        students = c.execute("SELECT id,name FROM students ORDER BY name").fetchall()
        out = []
        for s in students:
            records = c.execute("SELECT status FROM attendance WHERE student_id=? AND attendance_date BETWEEN ? AND ?", (s["id"],start,end)).fetchall()
            p=sum(r["status"]=="Present" for r in records)
            a=sum(r["status"]=="Absent" for r in records)
            l=sum(r["status"]=="Late" for r in records)
            total=p+a+l
            pct=((p+l)/total*100) if total else 0
            status="No Data" if not total else ("DEFAULTER" if pct<70 else "Regular")
            out.append(dict(id=s["id"],name=s["name"],present=p,absent=a,late=l,total=total,pct=pct,status=status))
        return out

BASE = '''
<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Student Attendance Tracker</title>
<style>
body{margin:0;background:#f2f5f9;color:#202938;font-family:Arial,sans-serif}header{background:#1f4e78;color:white;text-align:center;padding:22px 10px}nav{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;background:white;padding:12px}nav a{padding:9px;color:#1f4e78;text-decoration:none;font-weight:bold}main{max-width:1200px;margin:20px auto;padding:0 12px}.card{background:white;border-radius:10px;padding:16px;margin-bottom:16px;box-shadow:0 2px 8px #0001}h2{color:#1f4e78;margin-top:0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.stat{text-align:center}.stat b{display:block;font-size:28px;color:#1f4e78;margin-top:8px}input,select,button{padding:9px;border:1px solid #cbd5e1;border-radius:6px;font:inherit}button,.btn{background:#1f4e78;color:white;border:0;padding:10px 13px;border-radius:6px;cursor:pointer;text-decoration:none;display:inline-block}.danger{background:#a52828}.tablewrap{overflow:auto}table{border-collapse:collapse;width:100%;min-width:600px;background:white}th,td{padding:9px;border-bottom:1px solid #e5e7eb;text-align:left;white-space:nowrap}th{background:#eaf1f8;color:#1f4e78}.flash{background:#e4f6e8;padding:10px;margin-bottom:10px;border-radius:6px}.muted{color:#64748b;font-size:14px}.bad{color:#b42318;font-weight:bold}.good{color:#15803d;font-weight:bold}
</style></head><body><header><h1>STUDENT ATTENDANCE TRACKER</h1><p>Attendance Management System · Python + Flask + SQLite</p></header>
<nav><a href="/">Dashboard</a><a href="/students">Students</a><a href="/attendance">Mark Attendance</a><a href="/reports">Semester Report</a><a href="/history">History</a></nav>
<main>{% for m in get_flashed_messages() %}<div class="flash">{{m}}</div>{% endfor %}{{body|safe}}</main></body></html>
'''

@app.route("/")
def home():
    today=date.today().isoformat()
    with db() as c:
        total=c.execute("SELECT COUNT(*) n FROM students").fetchone()["n"]
        present=c.execute("SELECT COUNT(*) n FROM attendance WHERE attendance_date=? AND status IN ('Present','Late')",(today,)).fetchone()["n"]
        absent=c.execute("SELECT COUNT(*) n FROM attendance WHERE attendance_date=? AND status='Absent'",(today,)).fetchone()["n"]
    rows=report_rows("0001-01-01","9999-12-31")
    body=render_template_string('''<div class="card"><h2>Dashboard</h2><p>Today: <b>{{today}}</b></p><div class="cards">
    <div class="card stat">Total Students<b>{{total}}</b></div><div class="card stat">Present / Late Today<b>{{present}}</b></div>
    <div class="card stat">Absent Today<b>{{absent}}</b></div><div class="card stat">Defaulters<b>{{defaulters}}</b></div></div></div>
    <div class="card"><h2>Quick start</h2><p>Add students, select a date from the last 10 days, mark attendance, then open Semester Report.</p><p class="muted">Present + Late count as attended. Below 70% = DEFAULTER.</p></div>''',
    today=today,total=total,present=present,absent=absent,defaulters=sum(r["status"]=="DEFAULTER" for r in rows))
    return render_template_string(BASE,body=body)

@app.route("/students",methods=["GET","POST"])
def students():
    if request.method=="POST":
        name=request.form.get("name","").strip()
        if not name: flash("Enter a student name.")
        else:
            try:
                with db() as c: c.execute("INSERT INTO students(name) VALUES (?)",(name,))
                flash("Student added.")
            except sqlite3.IntegrityError: flash("Student already exists.")
        return redirect(url_for("students"))
    with db() as c: rows=c.execute("SELECT id,name FROM students ORDER BY name").fetchall()
    body=render_template_string('''<div class="card"><h2>Student Management</h2><form method="post"><input name="name" placeholder="Student name" required><button>Add Student</button></form></div>
    <div class="card"><h2>Students</h2><div class="tablewrap"><table><tr><th>ID</th><th>Name</th><th>Action</th></tr>{% for s in rows %}<tr><td>{{s.id}}</td><td>{{s.name}}</td><td><form method="post" action="/delete/{{s.id}}" onsubmit="return confirm('Delete student and records?')"><button class="danger">Delete</button></form></td></tr>{% else %}<tr><td colspan="3">No students yet.</td></tr>{% endfor %}</table></div></div>''',rows=rows)
    return render_template_string(BASE,body=body)

@app.route("/delete/<int:sid>",methods=["POST"])
def delete_student(sid):
    with db() as c:
        c.execute("DELETE FROM attendance WHERE student_id=?",(sid,))
        c.execute("DELETE FROM students WHERE id=?",(sid,))
    flash("Student and attendance records deleted.")
    return redirect(url_for("students"))

@app.route("/attendance",methods=["GET","POST"])
def attendance():
    days=dates10()
    selected=request.values.get("day",date.today().isoformat())
    if selected not in days:
        flash("Please select one of the last 10 days.")
        selected=date.today().isoformat()
    if request.method=="POST":
        with db() as c:
            people=c.execute("SELECT id FROM students").fetchall()
            for p in people:
                status=request.form.get("status_"+str(p["id"]),"")
                if status in ("Present","Absent","Late"):
                    c.execute("INSERT INTO attendance(student_id,attendance_date,status) VALUES (?,?,?) ON CONFLICT(student_id,attendance_date) DO UPDATE SET status=excluded.status",(p["id"],selected,status))
        flash("Attendance saved for "+selected)
        return redirect(url_for("attendance",day=selected))
    with db() as c:
        people=c.execute("SELECT s.id,s.name,a.status FROM students s LEFT JOIN attendance a ON a.student_id=s.id AND a.attendance_date=? ORDER BY s.name",(selected,)).fetchall()
    body=render_template_string('''<div class="card"><h2>Mark Attendance — Last 10 Days</h2><form method="get"><label>Select date: <select name="day" onchange="this.form.submit()">{% for d in days %}<option value="{{d}}" {% if d==selected %}selected{% endif %}>{{d}}{% if d==today %} (Today){% endif %}</option>{% endfor %}</select></label><button>Load</button></form><p class="muted">Choose each student's status, then save. Existing records can be edited.</p></div>
    <div class="card"><form method="post"><input type="hidden" name="day" value="{{selected}}"><div class="tablewrap"><table><tr><th>ID</th><th>Student</th><th>Status</th></tr>
    {% for s in people %}<tr><td>{{s.id}}</td><td>{{s.name}}</td><td><select name="status_{{s.id}}"><option value="" {% if not s.status %}selected{% endif %}>Not Marked</option>{% for st in ['Present','Absent','Late'] %}<option value="{{st}}" {% if s.status==st %}selected{% endif %}>{{st}}</option>{% endfor %}</select></td></tr>{% else %}<tr><td colspan="3">Add students first.</td></tr>{% endfor %}</table></div><p><button>Save Attendance</button></p></form></div>''',days=days,selected=selected,today=date.today().isoformat(),people=people)
    return render_template_string(BASE,body=body)

@app.route("/reports")
def reports():
    start=request.args.get("start",(date.today()-timedelta(days=120)).isoformat())
    end=request.args.get("end",date.today().isoformat())
    if not valid_date(start) or not valid_date(end) or start>end:
        flash("Invalid date range.")
        start=(date.today()-timedelta(days=120)).isoformat(); end=date.today().isoformat()
    rows=report_rows(start,end)
    with db() as c:
        people=c.execute("SELECT id,name FROM students ORDER BY name").fetchall()
        ds=[]; cur=valid_date(start); finish=valid_date(end)
        while cur and cur<=finish:
            ds.append(cur.isoformat()); cur+=timedelta(days=1)
        matrix=[]
        for s in people:
            recs=c.execute("SELECT attendance_date,status FROM attendance WHERE student_id=? AND attendance_date BETWEEN ? AND ?",(s["id"],start,end)).fetchall()
            lookup={r["attendance_date"]:r["status"] for r in recs}
            matrix.append((s["name"],[{"Present":"P","Absent":"A","Late":"L"}.get(lookup.get(d),"-") for d in ds]))
    body=render_template_string('''<div class="card"><h2>Semester Report</h2><form method="get">Start <input type="date" name="start" value="{{start}}" required> End <input type="date" name="end" value="{{end}}" required> <button>Generate</button> <a class="btn" href="/export.csv?start={{start}}&end={{end}}">Export CSV</a></form><p class="muted">Attendance % = (Present + Late) / Total marked days × 100. Unmarked days are excluded.</p></div>
    <div class="card"><h2>Student Summary</h2><div class="tablewrap"><table><tr><th>Student</th><th>Present</th><th>Absent</th><th>Late</th><th>Total</th><th>%</th><th>Status</th></tr>{% for r in rows %}<tr><td>{{r.name}}</td><td>{{r.present}}</td><td>{{r.absent}}</td><td>{{r.late}}</td><td>{{r.total}}</td><td>{{"%.2f"|format(r.pct)}}%</td><td class="{% if r.status=='DEFAULTER' %}bad{% elif r.status=='Regular' %}good{% endif %}">{{r.status}}</td></tr>{% else %}<tr><td colspan="7">No students.</td></tr>{% endfor %}</table></div></div>
    <div class="card"><h2>Date-wise Semester Matrix</h2><p class="muted">P = Present · A = Absent · L = Late · - = Not Marked</p><div class="tablewrap"><table><tr><th>Student</th>{% for d in ds %}<th>{{d[5:]}}</th>{% endfor %}</tr>{% for name,vals in matrix %}<tr><td>{{name}}</td>{% for v in vals %}<td>{{v}}</td>{% endfor %}</tr>{% endfor %}</table></div></div>''',start=start,end=end,rows=rows,ds=ds,matrix=matrix)
    return render_template_string(BASE,body=body)

@app.route("/export.csv")
def export_csv():
    start=request.args.get("start",(date.today()-timedelta(days=120)).isoformat())
    end=request.args.get("end",date.today().isoformat())
    if not valid_date(start) or not valid_date(end) or start>end: return redirect(url_for("reports"))
    output=io.StringIO(); w=csv.writer(output)
    w.writerow(["ID","Student","Present","Absent","Late","Total Marked","Attendance %","Status"])
    for r in report_rows(start,end): w.writerow([r["id"],r["name"],r["present"],r["absent"],r["late"],r["total"],f'{r["pct"]:.2f}%',r["status"]])
    return Response(output.getvalue(),mimetype="text/csv",headers={"Content-Disposition":f"attachment; filename=attendance_{start}_to_{end}.csv"})

@app.route("/history")
def history():
    with db() as c:
        rows=c.execute("SELECT attendance_date, SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) present, SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) absent, SUM(CASE WHEN status='Late' THEN 1 ELSE 0 END) late FROM attendance GROUP BY attendance_date ORDER BY attendance_date DESC").fetchall()
    body=render_template_string('''<div class="card"><h2>Attendance History</h2><div class="tablewrap"><table><tr><th>Date</th><th>Present</th><th>Absent</th><th>Late</th></tr>{% for r in rows %}<tr><td>{{r.attendance_date}}</td><td>{{r.present}}</td><td>{{r.absent}}</td><td>{{r.late}}</td></tr>{% else %}<tr><td colspan="4">No records yet.</td></tr>{% endfor %}</table></div></div>''',rows=rows)
    return render_template_string(BASE,body=body)

init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
