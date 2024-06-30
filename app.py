import os
import csv
from lyzr import ChatBot
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import imaplib
import email
import time
import nest_asyncio
import streamlit as st

nest_asyncio.apply()

def extract_info_from_csv(csv_file):
    companies_info = []
    file = csv_file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(file)
    for row in reader:
        companies_info.append({
            'website': row['website'],
            'email': row['email']
        })
    return companies_info

def generate_email(website, product_info):
    chatbot = ChatBot.webpage_chat(url=website)
    user_question = f"Write an email to the company to sell our new product more convincingly. Here are the details about our product: {product_info}"
    response = chatbot.chat(user_question)
    return response.response

def generate_reply(website, reply):
    chatbot = ChatBot.webpage_chat(url=website)
    user_question = f"Write an email reply to the company to whom you already sent an email to sell our new product to clarify and all the queries more convincingly. Here are the details of the reply: {reply}"
    response = chatbot.chat(user_question)
    return response.response

def send_email(sender_email, smtp_config, receiver_email, subject, content):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(content, 'plain'))

    try:
        server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'])
        server.starttls()
        server.login(sender_email, smtp_config['smtp_password'])
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        st.write(f"Successfully sent email to {receiver_email}")
    except Exception as e:
        st.write(f"Failed to send email to {receiver_email}: {e}")

def decode_payload(payload):
    try:
        return payload.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return payload.decode('iso-8859-1')
        except UnicodeDecodeError:
            return payload.decode('utf-8', errors='replace')

def check_for_replies(imap_server, email_user, email_pass, specific_email):
    mail = imaplib.IMAP4_SSL(imap_server)
    mail.login(email_user, email_pass)
    mail.select('inbox')

    result, data = mail.search(None, '(UNSEEN)')
    mail_ids = data[0].split()

    replies = []
    for mail_id in mail_ids:
        result, data = mail.fetch(mail_id, '(RFC822)')
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        from_address = email.utils.parseaddr(msg['From'])[1]
        if from_address.lower() == specific_email.lower():
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            message_text = decode_payload(payload)
                            replies.append(message_text)
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    message_text = decode_payload(payload)
                    replies.append(message_text)
                else:
                    st.write("Warning: Email has no payload to decode.")

    mail.close()
    mail.logout()
    return replies

def monitor_process(companies_info, smtp_config, sender_email, product_info, subject):
    ending_phrases = ["subscribe", "thank you", "interested", "I'm in", "sign me up"]

    for company in companies_info:
        email_content = generate_email(company['website'], product_info)
        send_email(sender_email, smtp_config, company['email'], subject, email_content)

    while True:
        for company in companies_info:
            replies = check_for_replies(smtp_config['imap_server'], sender_email, smtp_config['smtp_password'], company['email'])
            if replies:
                for reply in replies:
                    st.write(f"Reply from {company['email']}: {reply}")
                    reply_content = generate_reply(company['website'], reply)
                    send_email(sender_email, smtp_config, company['email'], f"RE: {subject}", reply_content)
            else:
                st.write("No replies found.")
        time.sleep(30)

st.title("Sales Development Representative Automation by Shafi")

st.sidebar.header("Configuration")
openai_api_key = st.sidebar.text_input("OpenAI API Key")
sender_email = st.sidebar.text_input("Sender Email")
sender_password = st.sidebar.text_input("Sender Password", type="password")
product_info = st.sidebar.text_area("Product Information")
subject = st.sidebar.text_input("Email Subject")
csv_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

if st.sidebar.button("Run"):
    if openai_api_key and sender_email and sender_password and product_info and subject and csv_file:
        os.environ['OPENAI_API_KEY'] = openai_api_key

        smtp_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_username': sender_email,
            'smtp_password': sender_password,
            'imap_server': 'imap.gmail.com'
        }

        companies_info = extract_info_from_csv(csv_file)
        monitor_process(companies_info, smtp_config, sender_email, product_info, subject)
    else:
        st.error("Please fill in all fields.")