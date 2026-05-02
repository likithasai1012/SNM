import smtplib
from email.message import EmailMessage
import os

def send_mail(to,subject,body):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465)
    server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))

    msg=EmailMessage()
    msg['FROM']=os.getenv("EMAIL_USER")
    msg['TO']=to
    msg['SUBJECT']=subject
    msg.set_content(body)

    server.send_message(msg)
    server.close()