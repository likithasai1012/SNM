from flask import Flask, request, render_template, redirect, url_for, flash, send_file, session 
from otp import genotp
from cmail import send_mail
from io import BytesIO
from stoken import entoken, dntoken
import mysql.connector
import mimetypes
import flask_excel as excel
from mimetypes import guess_type
import re
# Set up the database connection
mydb = mysql.connector.connect(user='root', host='localhost', password='101121', database='snmproject')
app = Flask(__name__)
app.secret_key = 'zoro@123'
excel.init_excel(app)

@app.route('/')
def home():
    return render_template('welcome.html')

# --- User Authentication Routes ---
''' register '''
@app.route('/userregister',methods=['GET','POST'])
def userregister():
    if request.method=='POST':
        print(request.form)
        username=request.form['username']
        useremail=request.form['email']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(useremail) from users where useremail=%s',[useremail])
        email_count=cursor.fetchone()
        if email_count[0]==0:
            gotp=genotp()
            userdata={'useremail':useremail,'username':username,'password':password,'gotp':gotp}
            subject='OTP for SNM Application'
            body=f'Use the given otp{gotp}'
            send_mail(to=useremail,body=body,subject=subject)
            flash(f'Otp has sent to given mail {useremail}')
            return redirect(url_for('otpverify',endata=entoken(data=userdata)))  #passing encrypted otp   
        elif email_count[0]==1:
            flash(f'{useremail}already existed please login')
            return redirect(url_for('userregister'))
        else:
            flash('something went wrong')
            
    return render_template('register.html')

''' OTP Verification '''
@app.route('/otpverify/<endata>',methods=['GET','POST'])
def otpverify(endata):
    if request.method=="POST":
        user_otp=request.form['otp']
        dndata=dntoken(data=endata)   
        if dndata['gotp']==user_otp:
            cursor=mydb.cursor()
            cursor.execute('insert into users(username,useremail,password) values(%s,%s,%s)',[dndata['username'],dndata['useremail'],dndata['password']])
            mydb.commit()
            flash (f'details registered successfully')
            return 'Success'
        else:
            flash('otp was incorect')
    return render_template('otp.html')

''' login '''
@app.route('/userlogin',methods=['GET','POST'])
def userlogin():
    if not session.get('user'):
        if request.method=='POST':
            login_useremail=request.form['useremail']
            login_password=request.form['password']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from users where useremail=%s',[login_useremail])
            email_count=cursor.fetchone()
            if email_count[0]==1:
                cursor.execute('select password from users where useremail=%s',[login_useremail])
                stored_password=cursor.fetchone()
                if stored_password[0]==login_password:
                    session['user']=login_useremail
                    return redirect(url_for('dashboard'))
                else:
                    flash('password was incorrect')
                    return redirect(url_for('userlogin'))
            elif email_count[0]==0:
                flash(f'{login_useremail} not found')
                return redirect(url_for('userlogin'))
        return render_template('userlogin.html')
    else:
        return redirect(url_for('dashboard'))
    
# --- Dashboard and Notes Routes ---
@app.route('/dashboard')
def dashboard():
    if session.get('user'):
        return render_template('dashboard.html', viewing_notes=True)
    else:
        flash('please login first')
        return redirect(url_for('userlogin'))

''' Add Notes '''
@app.route('/showaddnotes')
def showaddnotes():
    if session.get('user'):
        return render_template('dashboard.html', viewing_addnotes=True)
    else:
        flash('please login first')
        return redirect(url_for('userlogin'))

''' Add Notes '''
@app.route('/addnotes', methods=['POST'])
def addnotes():
    if session.get('user'):
        if request.method == 'POST':
            title = request.form['note-title']
            description = request.form['note-description']
            cursor = mydb.cursor(buffered=True)
            cursor.execute('select user_id from users where useremail=%s', [session.get('user')])
            user_id = cursor.fetchone()
            if user_id:
                cursor.execute('insert into notes(title, discription, added_by) values(%s, %s, %s)', [title, description, user_id[0]])
                mydb.commit()
                flash('notes added successfully')
                return redirect(url_for('viewallnotes'))
            else:
                flash('user id not found')
                return redirect(url_for('addnotes'))
        else:
            flash('could not store data')
            return redirect(url_for('dashboard'))
    else:
        flash('please login first to add notes')
        return redirect(url_for('userlogin'))

''' View all notes '''
@app.route('/viewallnotes')
def viewallnotes():
    if session.get('user'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('select * from notes where added_by=(select user_id from users where useremail=%s)', [session.get('user')])
        all_notesdata = cursor.fetchall()
        if all_notesdata:
            return render_template('dashboard.html', all_notesdata=all_notesdata, viewing_notes=True)
        else:
            flash('could not fetch notes data')
            return redirect(url_for('dashboard'))
    else: 
        flash('please login first to view notes')
        return redirect(url_for('userlogin'))

''' View notes '''
@app.route('/viewnotes/<nid>')
def viewnotes(nid):
    if session.get('user'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('select * from notes where nid=%s',[nid])
        notes_data = cursor.fetchone()
        if notes_data:
            return render_template('viewnotes.html', notes_data=notes_data)
        else:
            flash('could not fetch note data')
            return redirect(url_for('viewallnotes'))
    else:
        flash('please login first to view notes')
        return redirect(url_for('userlogin'))
    
''' Delete Notes '''
@app.route('/deletenotes/<nid>')
def deletenotes(nid):
    if session.get('user'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('delete from notes where nid=%s and added_by=(select user_id from users where useremail=%s)', [nid, session.get('user')])
        mydb.commit()
        flash('note deleted successfully')
        return redirect(url_for('viewallnotes'))
    else:
        flash('please login first to delete notes')
        return redirect(url_for('userlogin'))
    
''' Update Notes '''
@app.route('/updatenotes/<nid>', methods=['GET', 'POST'])
def updatenotes(nid):
    if session.get('user'):
        cursor = mydb.cursor(buffered=True)
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            cursor.execute('update notes set title=%s, discription=%s where nid=%s and added_by=(select user_id from users where useremail=%s)', [title, description, nid, session.get('user')])
            mydb.commit()
            flash('note updated successfully')
            return redirect(url_for('viewallnotes'))
        else:
            cursor.execute('select * from notes where nid=%s and added_by=(select user_id from users where useremail=%s)', [nid, session.get('user')])
            notes_data = cursor.fetchone()
            if notes_data:
                return render_template('updatenotes.html', notes_data=notes_data)
            else:
                flash('could not fetch note data')
                return redirect(url_for('viewallnotes'))
    else:
        flash('please login first to update notes')
        return redirect(url_for('userlogin'))

# --- File Management Routes ---
@app.route('/showuploadfiles')
def showuploadfiles():
    if session.get('user'):
        return render_template('dashboard.html', viewing_uploadfiles=True)
    else:
        flash('please login first')
        return redirect(url_for('userlogin'))

''' Upload File '''
@app.route('/uploadfile', methods=['GET', 'POST'])
def uploadfile():
    if session.get('user'):
        if request.method == 'POST':
            file_data=request.files['file-upload']
            fname=file_data.filename
            f_data=file_data.read()
            cursor=mydb.cursor(buffered=True)
            cursor.execute('Select user_id from users where useremail=%s',[session.get('user')])
            user_id = cursor.fetchone()
            cursor.execute('insert into filesdata(fname,fdata,added_by) values(%s,%s,%s)',[fname,f_data,user_id[0]])
            mydb.commit()   
            cursor.close()
            flash('file uploaded successfully')
        return redirect(url_for('viewallfiles'))
    else:
        flash('please login first to upload files')
        return redirect(url_for('userlogin'))

''' View all files '''
@app.route('/viewallfiles')
def viewallfiles():
    if session.get('user'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('select fid,fname,created_at from filesdata where added_by=(select user_id from users where useremail=%s)', [session.get('user')])
        all_filesdata = cursor.fetchall()
        if all_filesdata:
            return render_template('dashboard.html', all_filesdata=all_filesdata, viewing_files=True)
        else:
            flash('could not fetch files data')
            return redirect(url_for('dashboard'))
    else:
        flash('please login first to view files')
        return redirect(url_for('userlogin'))

''' View a single file '''
@app.route('/viewfile/<fid>')
def viewfile(fid):
    if session.get('user'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('select fname,fdata from filesdata where fid=%s and added_by=(select user_id from users where useremail=%s)', [fid, session.get('user')])
        file_data = cursor.fetchone()
        if not file_data:
            flash('File not found or you do not have permission to view it.')
            return redirect(url_for('viewallfiles'))
        file_name = file_data[0]
        mime_type = guess_type(file_name)
        file_stream = BytesIO(file_data[1])
        return send_file(file_stream, download_name=file_name,as_attachment=False)
    else:
        flash('Please log in to view files.')
        return redirect(url_for('userlogin'))
    
''' Download a file '''
@app.route('/downloadfile/<fid>')
def downloadfile(fid):
    if session.get('user'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('select fname, fdata from filesdata where fid=%s and added_by=(select user_id from users where useremail=%s)', [fid, session.get('user')])
        file_data = cursor.fetchone()
        if file_data:
            file_name, file_content = file_data
            file_stream = BytesIO(file_content)
            return send_file(file_stream, download_name=file_name, as_attachment=True)
        else:
            flash('File not found or you do not have permission to download it.')
            return redirect(url_for('viewallfiles'))
    else:
        flash('Please log in to download files.')
        return redirect(url_for('userlogin'))

''' Delete a file '''
@app.route('/deletefile/<fid>')
def deletefile(fid):
    if session.get('user'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('delete from filesdata where fid=%s and added_by=(select user_id from users where useremail=%s)', [fid, session.get('user')])
        mydb.commit()
        flash('File deleted successfully')
        return redirect(url_for('viewallfiles'))
    else:
        flash('Please log in to delete files.')
        return redirect(url_for('userlogin'))
@app.route('/getexceldata')
def getexceldata():
    if session.get('user'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('select user_id from users where useremail=%s',[session.get('user')])
        user_id=cursor.fetchone()
        cursor.execute('select * from notes where added_by=%s',[user_id[0]])  
        notes_data=cursor.fetchall()
        data=[list(i) for i in notes_data]
        column_heading=['Notes_id','title','Description','Notes_created_time']
        data.insert(0,column_heading)
        return excel.make_response_from_array(data,'xlsx',file_name='mynotes.xlsx')
    else:
        flash('to get excel data pls login first')
        return redirect(url_for('userlogin'))
@app.route('/search',methods=['POST'])
def search():
    if request.method=='POST':
        searchdata=request.form['sdata']
        strng=['A-Za-z0-9']
        pattern=re.compile(f'^{strng}',re.IGNORECASE)
        if re.match(pattern,searchdata):
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select * from notes where title like %s or discription like %s or created_at like %s or nid like %s',[searchdata+'%', searchdata+'%', searchdata+'%', searchdata])
            search_result=cursor.fetchall()
            cursor.execute('select * from filesdata where fname like %s or created_at like %s',[searchdata+'%', searchdata+'%'])
            search_result2=cursor.fetchall()
            if search_result or search_result2:
                return render_template('dashboard.html',search_result=search_result, search_result2=search_result2)
            else:
                flash('no matching results found')
                return redirect(url_for('dashboard'))
        else:
            flash('invalid search string')
            return redirect(url_for('dashboard'))
    else:
        flash('to search data pls login first')
        return redirect(url_for('dashboard'))
@app.route('/userlogout')
def userlogout():
    if session.get('user'):
        session.pop('user')
        flash('logged out successfully')
        return redirect(url_for('userlogin'))   
    else:
        flash('please login first')
        return redirect(url_for('userlogin'))            
app.run(debug=True, use_reloader=True)