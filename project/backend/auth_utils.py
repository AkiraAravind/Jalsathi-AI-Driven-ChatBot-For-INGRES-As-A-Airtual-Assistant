import pyotp
import logging
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr, BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict
import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# Mail Configuration
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM=os.getenv("MAIL_FROM", "support@ingres.ai"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "INGRES JalSathi"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "True") == "True",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "False") == "True",
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

fm = FastMail(conf)

# In-memory store for OTPs (In production, use Redis or DB with TTL)
otp_store = {}

async def send_otp_email(email: str, otp: str):
    try:
        message = MessageSchema(
            subject="INGRES JalSathi Authorization Code",
            recipients=[email],
            body=f"Your secure authorization code is: {otp}. This code will expire in 5 minutes.",
            subtype="plain"
        )

        # Only send if credentials are provided, otherwise log to terminal
        if os.getenv("MAIL_PASSWORD"):
            await fm.send_message(message)
            logging.info(f"OTP sent to {email}")
        else:
            logging.warning(f"!!! [MOCK MAIL] OTP for {email}: {otp} !!!")
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        logging.warning(f"!!! [MOCK MAIL] OTP for {email}: {otp} !!!")

async def send_feedback_email(user_email: str, message_content: str):
    admin_email = "1akiraaravind1@gmail.com"
    try:
        message = MessageSchema(
            subject=f"INGRES User Feedback from {user_email}",
            recipients=[admin_email],
            body=f"User Email: {user_email}\n\nMessage:\n{message_content}",
            subtype="plain"
        )

        if os.getenv("MAIL_PASSWORD"):
            await fm.send_message(message)
            logging.info(f"Feedback from {user_email} relayed to admin.")
        else:
            logging.warning(f"!!! [MOCK MAIL] Feedback from {user_email}: {message_content} !!!")
    except Exception as e:
        logging.error(f"Failed to relay feedback: {str(e)}")

async def send_pdf_email(user_email: str, pdf_path: str):
    try:
        message = MessageSchema(
            subject="Your INGRES AI Chat Transcript",
            recipients=[user_email],
            body="Attached is the PDF transcript of your recent chat session.",
            subtype="plain",
            attachments=[pdf_path]
        )

        if os.getenv("MAIL_PASSWORD"):
            await fm.send_message(message)
            logging.info(f"PDF Transcript sent to {user_email}")
        else:
            logging.warning(f"!!! [MOCK MAIL] PDF Transcript for {user_email} generated at {pdf_path} !!!")
    except Exception as e:
        logging.error(f"Failed to send PDF email: {str(e)}")
        raise e

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "ingres_super_secret_key_change_me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def generate_otp():
    totp = pyotp.TOTP(pyotp.random_base32(), interval=300)
    return totp.now()
