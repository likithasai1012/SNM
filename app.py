from flask import Flask, request, render_template, redirect, url_for, flash, session
from otp import genotp
from stoken import entoken, dntoken
import psycopg
import os

app = Flask(__name__)
app.secret_key = 'zoro@123'

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

            print("OTP:", otp)
            flash(f"Your OTP is {otp}")

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
        return redirect(url_for('viewallnotes'))

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


# UPDATE NOTE
@app.route('/updatenotes/<int:nid>', methods=['GET','POST'])
def updatenotes(nid):
    if session.get('user'):
        cursor = conn.cursor()

        if request.method == 'POST':
            title = request.form['title']
            desc = request.form['description']

            cursor.execute(
                "UPDATE notes SET title=%s, discription=%s WHERE nid=%s",
                (title, desc, nid)
            )
            conn.commit()
            flash("Note updated successfully")
            return redirect(url_for('viewallnotes'))

        cursor.execute("SELECT * FROM notes WHERE nid=%s", (nid,))
        data = cursor.fetchone()

        return render_template('update.html', notes_data=data)

    return redirect(url_for('userlogin'))


# DELETE NOTE
@app.route('/deletenotes/<int:nid>')
def deletenotes(nid):
    if session.get('user'):
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE nid=%s", (nid,))
        conn.commit()
        flash("Note deleted successfully")
        return redirect(url_for('viewallnotes'))

    return redirect(url_for('userlogin'))


# LOGOUT
@app.route('/userlogout')
def logout():
    session.pop('user', None)
    return redirect(url_for('userlogin'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))