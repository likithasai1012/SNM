import smtplib
from email.message import EmailMessage
def send_mail(to,subject,body):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465)
    server.login('akshaynandancheedaraboyina21@gmail.com','sqpv gvvq uodi lmqs')
    msg=EmailMessage()
    msg['FROM']='akshaynandancheedaraboyina21@gmail.com'
    msg['TO']=to
    msg['SUBJECT']=subject
    msg.set_content(body)
    server.send_message(msg) #mail sending
    server.close() #closing the server ojb