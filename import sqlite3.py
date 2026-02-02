import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date
from typing import List, Tuple

DB_FILE = "attendance_batch.db"

# Database layer (OOP)
class Database:
    def __init__(self, db_file: str = DB_FILE):
        self.conn = sqlite3.connect(db_file)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.create_tables()

    def create_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll TEXT NOT NULL UNIQUE,
                batch TEXT,
                department TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                att_date TEXT NOT NULL,
                status TEXT NOT NULL,
                UNIQUE(student_id, att_date),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    # CRUD: students
    def add_student(self, name: str, roll: str):
        cur = self.conn.cursor()
        batch = "8th"
        department = "Software Engineering"
        try:
            cur.execute("INSERT INTO students (name, roll, batch, department) VALUES (?, ?, ?, ?)",
                        (name.strip(), roll.strip(), batch, department))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError("Roll No already exists")

    def update_student(self, sid: int, name: str, roll: str):
        cur = self.conn.cursor()
        try:
            cur.execute("UPDATE students SET name=?, roll=? WHERE id=?",
                        (name.strip(), roll.strip(), sid))
            self.conn.commit()
            if cur.rowcount == 0:
                raise ValueError("Student not found")
        except sqlite3.IntegrityError:
            raise ValueError("Roll No already exists")

    def delete_student(self, sid: int):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM students WHERE id=?", (sid,))
        self.conn.commit()

    def get_all_students(self) -> List[Tuple]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, roll, batch, department FROM students ORDER BY roll")
        return cur.fetchall()

    def get_student(self, sid: int):
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, roll FROM students WHERE id=?", (sid,))
        return cur.fetchone()

    # Attendance
    def mark_attendance_bulk(self, pairs: List[Tuple[int, str]], att_date: str):
        cur = self.conn.cursor()
        for sid, status in pairs:
            try:
                cur.execute("INSERT INTO attendance (student_id, att_date, status) VALUES (?, ?, ?)",
                            (sid, att_date, status))
            except sqlite3.IntegrityError:
                cur.execute("UPDATE attendance SET status=? WHERE student_id=? AND att_date=?",
                            (status, sid, att_date))
        self.conn.commit()

    def get_attendance_by_date(self, att_date: str) -> List[Tuple]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT a.id, s.roll, s.name, s.batch, s.department, a.status
            FROM attendance a JOIN students s ON a.student_id = s.id
            WHERE a.att_date = ?
            ORDER BY s.roll
        """, (att_date,))
        return cur.fetchall()


# GUI layer - colourful modernized UI
class AttendanceApp:
    def __init__(self, root: tk.Tk):
        self.db = Database()
        self.root = root
        self.root.title("Attendance System - 8th Batch / Software Engineering")
        self.root.geometry("960x640")
        # use a soft background
        self.root.configure(bg="#f4f7fb")
        self.setup_style()
        self.setup_ui()
        self.load_students()

    def setup_style(self):
        style = ttk.Style(self.root)
        # prefer platform default theme then tweak
        try:
            style.theme_use('clam')
        except Exception:
            pass
        # General fonts
        self.title_font = ("Helvetica", 12, "bold")
        self.text_font = ("Helvetica", 10)
        # Button styles
        style.configure('TButton', font=self.text_font, padding=6)
        style.configure('Accent.TButton', font=self.text_font, padding=6, relief='flat')
        style.map('Accent.TButton', background=[('active', '#5aa0ff'), ('!active', '#3b82f6')])
        # Treeview styles
        style.configure('Treeview', rowheight=28, font=self.text_font, fieldbackground='#ffffff')
        style.configure('Treeview.Heading', font=("Helvetica", 10, "bold"))
        style.map('Treeview', background=[('selected', '#cfe8ff')])

    def setup_ui(self):
        # Top header
        header = tk.Frame(self.root, bg="#3b82f6", pady=10)
        header.pack(fill="x")
        tk.Label(header, text="Attendance System", bg="#3b82f6", fg="white", font=("Helvetica", 16, "bold")).pack(side="left", padx=16)
        tk.Label(header, text="8th Batch — Software Engineering", bg="#3b82f6", fg="white", font=("Helvetica", 10)).pack(side="left", padx=8)

        # Main container
        container = tk.Frame(self.root, bg="#f4f7fb")
        container.pack(fill="both", expand=True, padx=12, pady=12)

        # Left panel - Add student + list
        left = tk.Frame(container, bg="#ffffff", bd=0, relief="flat")
        left.pack(side="left", fill="both", expand=True, padx=(0,8))

        add_frame = tk.Frame(left, bg="#ffffff", pady=8)
        add_frame.pack(fill="x", padx=8, pady=(8,0))
        tk.Label(add_frame, text="Add Student", bg="#ffffff", font=self.title_font).grid(row=0, column=0, sticky="w", padx=6)

        tk.Label(add_frame, text="Name:", bg="#ffffff").grid(row=1, column=0, sticky="e", pady=6)
        self.e_name = ttk.Entry(add_frame, width=30)
        self.e_name.grid(row=1, column=1, padx=8, sticky="w")

        tk.Label(add_frame, text="Roll:", bg="#ffffff").grid(row=1, column=2, sticky="e")
        self.e_roll = ttk.Entry(add_frame, width=12)
        self.e_roll.grid(row=1, column=3, padx=8, sticky="w")

        btn_add = ttk.Button(add_frame, text="➕  Add", style='Accent.TButton', command=self.add_student)
        btn_add.grid(row=1, column=4, padx=6)

        # Student list frame
        frm_list = tk.LabelFrame(left, text="Student List", padx=6, pady=6, bg="#ffffff")
        frm_list.pack(fill="both", expand=True, padx=8, pady=10)

        cols = ("#","roll","name","batch","department")
        self.tree = ttk.Treeview(frm_list, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            if c == "#":
                self.tree.heading(c, text="#")
                self.tree.column(c, width=50, anchor="center")
            elif c == "roll":
                self.tree.heading(c, text="Roll")
                self.tree.column(c, width=80, anchor="center")
            elif c == "name":
                self.tree.heading(c, text="Name")
                self.tree.column(c, width=300, anchor="w")
            elif c == "batch":
                self.tree.heading(c, text="Batch")
                self.tree.column(c, width=90, anchor="center")
            else:
                self.tree.heading(c, text="Department")
                self.tree.column(c, width=160, anchor="w")

        self.tree.pack(fill="both", expand=True, side="left")
        vsb = ttk.Scrollbar(frm_list, orient="vertical", command=self.tree.yview)
        vsb.pack(side="left", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

        # style alternating rows via tags
        self.tree.tag_configure('odd', background='#fbfcff')
        self.tree.tag_configure('even', background='#eef6ff')

        # Buttons under list
        btn_frame = tk.Frame(left, bg="#ffffff", pady=6)
        btn_frame.pack(fill="x", padx=8)
        ttk.Button(btn_frame, text="✏️ Edit Selected", command=self.edit_student).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="🗑️ Delete Selected", command=self.delete_student).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="📋 Mark Attendance", command=self.mark_attendance_bulk).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="👁️ View Attendance", command=self.open_view_attendance).pack(side="left", padx=6)

        # Right panel - quick info & legend
        right = tk.Frame(container, width=300, bg="#ffffff")
        right.pack(side="left", fill="y")

        info = tk.LabelFrame(right, text="Information", bg="#ffffff", padx=8, pady=8)
        info.pack(fill="x", padx=8, pady=(8,6))
        tk.Label(info, text="Batch: 8th", bg="#ffffff").pack(anchor="w")
        tk.Label(info, text="Department: Software Engineering", bg="#ffffff").pack(anchor="w")
        tk.Label(info, text=f"Students: (auto)", bg="#ffffff", name='lbl_count').pack(anchor="w", pady=(6,0))

        legend = tk.LabelFrame(right, text="Legend", bg="#ffffff", padx=8, pady=8)
        legend.pack(fill="x", padx=8, pady=6)
        tk.Label(legend, text="Present: ✅ — Absent: ❌", bg="#ffffff").pack(anchor="w")

        # Status bar
        self.status = tk.Label(self.root, text="Ready", bd=1, relief="sunken", anchor="w", bg="#f0f0f0")
        self.status.pack(side="bottom", fill="x")

    def set_status(self, txt: str):
        self.status.config(text=txt)

    def load_students(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        students = self.db.get_all_students()
        for idx, (sid, name, roll, batch, dept) in enumerate(students, start=1):
            tag = 'even' if idx % 2 == 0 else 'odd'
            self.tree.insert("", "end", iid=str(sid), values=(idx, roll, name, batch, dept), tags=(tag,))
        # update count label
        try:
            lbl = self.root.nametowidget('.!frame.!frame3.!label')
        except Exception:
            lbl = None
        # instead set via status
        self.set_status(f"Loaded {len(students)} students")

    def add_student(self):
        name = self.e_name.get().strip()
        roll = self.e_roll.get().strip()
        if not name or not roll:
            messagebox.showerror("Error", "Name and Roll are required")
            return
        try:
            self.db.add_student(name, roll)
            messagebox.showinfo("Success", "Student added")
            self.e_name.delete(0, tk.END)
            self.e_roll.delete(0, tk.END)
            self.load_students()
        except ValueError as ex:
            messagebox.showerror("Error", str(ex))

    def get_selected_student_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def edit_student(self):
        sid = self.get_selected_student_id()
        if not sid:
            messagebox.showerror("Error", "Please select a student")
            return
        row = self.db.get_student(sid)
        if not row:
            messagebox.showerror("Error", "Student not found")
            return
        _, name, roll = row
        new_name = simpledialog.askstring("Edit Name", "Enter name:", initialvalue=name, parent=self.root)
        if new_name is None:
            return
        new_roll = simpledialog.askstring("Edit Roll", "Enter roll:", initialvalue=roll, parent=self.root)
        if new_roll is None:
            return
        try:
            self.db.update_student(sid, new_name, new_roll)
            messagebox.showinfo("Success", "Student updated")
            self.load_students()
        except ValueError as ex:
            messagebox.showerror("Error", str(ex))

    def delete_student(self):
        sid = self.get_selected_student_id()
        if not sid:
            messagebox.showerror("Error", "Please select a student")
            return
        ok = messagebox.askyesno("Confirm", "Delete selected student? This will also remove related attendance.")
        if not ok:
            return
        self.db.delete_student(sid)
        messagebox.showinfo("Deleted", "Student removed")
        self.load_students()

    # Bulk attendance marking
    def mark_attendance_bulk(self):
        students = self.db.get_all_students()
        if not students:
            messagebox.showinfo("Info", "No students to mark attendance for.")
            return
        win = tk.Toplevel(self.root)
        win.title("Mark Attendance - Bulk")
        win.geometry("560x600")
        win.configure(bg="#f7fbff")

        header = tk.Frame(win, bg="#3b82f6", pady=8)
        header.pack(fill="x")
        tk.Label(header, text="Mark Attendance", bg="#3b82f6", fg="white", font=("Helvetica", 12, "bold")).pack()

        tk.Label(win, text="Enter Date (YYYY-MM-DD):", bg="#f7fbff", font=self.text_font).pack(pady=6)
        entry_date = ttk.Entry(win, width=14)
        entry_date.pack()
        entry_date.insert(0, date.today().isoformat())

        frm = tk.Frame(win, bg="#f7fbff")
        frm.pack(fill="both", expand=True, padx=12, pady=8)

        canvas = tk.Canvas(frm, bg="#f7fbff", highlightthickness=0)
        scroll = ttk.Scrollbar(frm, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg="#f7fbff")

        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0,0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")

        # For each student create a Checkbutton (Present)
        self.present_vars = {}
        for sid, name, roll, batch, dept in students:
            var = tk.IntVar(value=0)
            frm_row = tk.Frame(inner, pady=3, bg="#f7fbff")
            frm_row.pack(fill="x", padx=4)
            tk.Label(frm_row, text=f"{roll}", width=8, anchor="w", bg="#f7fbff").pack(side="left")
            tk.Label(frm_row, text=f"{name}", width=30, anchor="w", bg="#f7fbff").pack(side="left")
            tk.Label(frm_row, text=f"{batch}", width=8, anchor="center", bg="#f7fbff").pack(side="left")
            tk.Label(frm_row, text=f"{dept}", width=18, anchor="w", bg="#f7fbff").pack(side="left")
            cb = ttk.Checkbutton(frm_row, text="Present", variable=var)
            cb.pack(side="left", padx=6)
            self.present_vars[sid] = var

        def save_action():
            att_date = entry_date.get().strip()
            if not att_date:
                messagebox.showerror("Error", "Please enter a date")
                return
            pairs = []
            for sid, var in self.present_vars.items():
                status = "Present" if var.get() == 1 else "Absent"
                pairs.append((sid, status))
            try:
                self.db.mark_attendance_bulk(pairs, att_date)
                messagebox.showinfo("Success", f"Attendance saved for {att_date}")
                win.destroy()
            except Exception as ex:
                messagebox.showerror("Error", str(ex))
        btn_frame = tk.Frame(win, bg="#f7fbff", pady=8)
        btn_frame.pack()
        ttk.Button(btn_frame, text="💾 Save Attendance", command=save_action, style='Accent.TButton').pack(side="left", padx=8)
        ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="left", padx=8)

    def open_view_attendance(self):
        ViewAttendanceWindow(self.root, self.db)

class ViewAttendanceWindow:
    def __init__(self, parent: tk.Tk, db: Database):
        self.db = db
        self.win = tk.Toplevel(parent)
        self.win.title("View Attendance")
        self.win.geometry("820x520")
        self.win.configure(bg="#f4f7fb")
        self.setup_ui()
        self.load_attendance()

    def setup_ui(self):
        top = tk.Frame(self.win, pady=6, bg="#f4f7fb")
        top.pack(fill="x")
        tk.Label(top, text="Date (YYYY-MM-DD):", bg="#f4f7fb").pack(side="left", padx=6)
        self.entry_date = ttk.Entry(top, width=12)
        self.entry_date.pack(side="left")
        self.entry_date.insert(0, date.today().isoformat())

        ttk.Button(top, text="Load", command=self.load_attendance).pack(side="left", padx=6)

        cols = ("roll","name","batch","department","status")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings")
        self.tree.heading("roll", text="Roll")
        self.tree.heading("name", text="Name")
        self.tree.heading("batch", text="Batch")
        self.tree.heading("department", text="Department")
        self.tree.heading("status", text="Status")
        self.tree.column("roll", width=80, anchor="center")
        self.tree.column("name", width=320, anchor="w")
        self.tree.column("batch", width=80, anchor="center")
        self.tree.column("department", width=160, anchor="w")
        self.tree.column("status", width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

    def load_attendance(self):
        dt = self.entry_date.get().strip()
        if not dt:
            messagebox.showerror("Error", "Please enter a date")
            return
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = self.db.get_attendance_by_date(dt)
        if not rows:
            messagebox.showinfo("Info", "No attendance records for this date")
            return
        for _id, roll, name, batch, department, status in rows:
            icon = "✅" if status.lower().startswith('p') else "❌"
            self.tree.insert("", "end", values=(roll, name, batch, department, f"{icon} {status}"))

# Run
if __name__ == "__main__":
    root = tk.Tk()
    app = AttendanceApp(root)
    root.mainloop()
