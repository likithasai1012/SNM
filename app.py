from flask import Flask, request, render_template, redirect, url_for, flash, send_file, session 
from otp import genotp
from cmail import send_mail
from io import BytesIO
from stoken import entoken, dntoken
import flask_excel as excel
from mimetypes import guess_type
import re
import psycopg
import os

app = Flask(__name__)
app.secret_key = 'zoro@123'
excel.init_excel(app)

# DB CONNECTION
conn = psycopg.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    dbname=os.getenv("DB_NAME"),
    port=os.getenv("DB_PORT")
)

@app.route('/')
def home():
    return render_template('welcome.html')


# REGISTER
@app.route('/userregister', methods=['GET','POST'])
def userregister():
    if request.method == 'POST':
        username = request.form['username']
        useremail = request.form['email']
        password = request.form['password']

        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE useremail=%s', (useremail,))
        email_count = cursor.fetchone()

        if email_count[0] == 0:
            otp = genotp()
            userdata = {'useremail':useremail,'username':username,'password':password,'gotp':otp}
            send_mail(to=useremail, body=f"Your OTP is {otp}", subject="OTP Verification")
            flash("OTP sent to email")
            return redirect(url_for('otpverify', endata=entoken(userdata)))
        else:
            flash("Email already exists")
            return redirect(url_for('userregister'))

    return render_template('register.html')


# OTP VERIFY
@app.route('/otpverify/<endata>', methods=['GET','POST'])
def otpverify(endata):
    if request.method == "POST":
        user_otp = request.form['otp']
        data = dntoken(endata)

        if data['gotp'] == user_otp:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users(username,useremail,password) VALUES(%s,%s,%s)",
                (data['username'], data['useremail'], data['password'])
            )
            conn.commit()
            flash("Registered successfully")
            return redirect(url_for('userlogin'))
        else:
            flash("Invalid OTP")

    return render_template('otp.html')


# LOGIN
@app.route('/userlogin', methods=['GET','POST'])
def userlogin():
    if request.method == 'POST':
        email = request.form['useremail']
        password = request.form['password']

        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE useremail=%s", (email,))
        data = cursor.fetchone()

        if data and data[0] == password:
            session['user'] = email
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials")

    return render_template('userlogin.html')


# DASHBOARD
@app.route('/dashboard')
def dashboard():
    if session.get('user'):
        return render_template('dashboard.html')
    return redirect(url_for('userlogin'))


# ADD NOTES
@app.route('/addnotes', methods=['POST'])
def addnotes():
    if session.get('user'):
        title = request.form['note-title']
        desc = request.form['note-description']

        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE useremail=%s", (session['user'],))
        uid = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO notes(title,discription,added_by) VALUES(%s,%s,%s)",
            (title, desc, uid)
        )
        conn.commit()
        return redirect(url_for('dashboard'))

    return redirect(url_for('userlogin'))


# VIEW NOTES
@app.route('/viewallnotes')
def viewallnotes():
    if session.get('user'):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM notes WHERE added_by=(SELECT user_id FROM users WHERE useremail=%s)",
            (session['user'],)
        )
        data = cursor.fetchall()
        return render_template('dashboard.html', all_notesdata=data)

    return redirect(url_for('userlogin'))


# LOGOUT
@app.route('/userlogout')
def logout():
    session.pop('user', None)
    return redirect(url_for('userlogin'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))