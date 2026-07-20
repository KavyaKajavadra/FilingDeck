"""
FilingDeck — Main Flask Application
MSME Compliance & Freelancer Financial Checkup Platform
"""

import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from twilio.twiml.messaging_response import MessagingResponse

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

from compliance import (
    BUSINESS_TYPES,
    calculate_upcoming_deadlines,
    get_compliance_summary,
)
from chatbot import get_ai_response

# ── App Configuration ────────────────────────────────────────────────────────

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "filingdeck-dev-key-change-in-production")

# Vercel filesystem is read-only except for /tmp.
if os.environ.get("VERCEL"):
    db_path = "sqlite:////tmp/filingdeck.db"
else:
    db_path = "sqlite:///filingdeck.db"
    
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", db_path)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ── WhatsApp Config ──────────────────────────────────────────────────────────
# Replace with your actual WhatsApp Business number
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "919999999999")
WHATSAPP_MESSAGE = "Hi FilingDeck! I'm interested in your compliance services."

# ── Email Notifications ──────────────────────────────────────────────────────
def send_email_async(subject, body):
    """Sends an email asynchronously."""
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    admin_email = os.environ.get("ADMIN_EMAIL")

    if not all([smtp_user, smtp_pass, admin_email]):
        print("Email credentials not fully configured. Skipping email notification.")
        return

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = admin_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print("Lead notification email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def notify_new_lead(lead):
    """Formats the lead details and sends an email in the background."""
    subject = f"New Lead: {lead.name} ({lead.source})"
    body = f"""
    <h2>New Lead Received from FilingDeck</h2>
    <p><strong>Name:</strong> {lead.name}</p>
    <p><strong>Phone:</strong> {lead.phone}</p>
    <p><strong>Email:</strong> {lead.email}</p>
    <p><strong>Business Name:</strong> {lead.business_name}</p>
    <p><strong>Business Type:</strong> {lead.business_type}</p>
    <p><strong>Service Interested:</strong> {lead.service_interested}</p>
    <p><strong>Message:</strong></p>
    <blockquote style="background: #f9f9f9; padding: 10px; border-left: 4px solid #ccc;">
        {lead.message or 'No message provided.'}
    </blockquote>
    <p><strong>Source:</strong> {lead.source}</p>
    """
    thread = threading.Thread(target=send_email_async, args=(subject, body))
    thread.start()


# ── Database Models ──────────────────────────────────────────────────────────

class Lead(db.Model):
    """Stores contact form submissions and compliance calendar users."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(15), nullable=False)
    business_name = db.Column(db.String(150))
    business_type = db.Column(db.String(50))
    service_interested = db.Column(db.String(100))
    message = db.Column(db.Text)
    source = db.Column(db.String(50), default="contact_form")  # contact_form, compliance_calendar
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Lead {self.name} — {self.phone}>"

import json

class WhatsAppSession(db.Model):
    """Stores active WhatsApp conversations to track history and human handoff state."""
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    history = db.Column(db.Text, default="[]")  # Stored as JSON string
    needs_human = db.Column(db.Boolean, default=False)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_history(self):
        return json.loads(self.history)

    def set_history(self, history_list):
        self.history = json.dumps(history_list)


class User(db.Model):
    """Stores user accounts for the dashboard."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    decks = db.relationship('Deck', backref='owner', lazy=True)

class Deck(db.Model):
    """Stores a user's compliance decks."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    file_count = db.Column(db.Integer, default=0)
    last_modified = db.Column(db.String(50)) # Storing as string for display purposes, e.g. '2 mins ago'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ── Service Data ─────────────────────────────────────────────────────────────

PLANS = [
    {
        "name": "Starter",
        "price": "999",
        "period": "/month",
        "description": "Perfect for small businesses just getting started with compliance",
        "features": [
            "GST Filing (Monthly GSTR-1 & GSTR-3B)",
            "Compliance Calendar with Reminders",
            "WhatsApp Support",
            "Deadline Alerts via SMS",
        ],
        "highlight": False,
        "cta": "Get Started",
    },
    {
        "name": "Growth",
        "price": "2,499",
        "period": "/month",
        "description": "Complete tax compliance for growing businesses",
        "features": [
            "Everything in Starter",
            "TDS Filing (Quarterly)",
            "Professional Tax Returns",
            "Income Tax Return (Annual)",
            "Dedicated WhatsApp Group",
            "Priority Support",
        ],
        "highlight": True,
        "cta": "Most Popular",
    },
]

ONE_TIME_SERVICES = [
    {"name": "Accounting & Bookkeeping", "price": "Custom", "icon": "📊"},
    {"name": "ITR Filing", "price": "1,499", "icon": "📄"},
    {"name": "GST Filing", "price": "999", "icon": "🧾"},
    {"name": "TDS Filing", "price": "999", "icon": "💰"},
    {"name": "PAN Application (Individual / Business)", "price": "499", "icon": "🪪"},
    {"name": "TAN Application", "price": "499", "icon": "📋"},
    {"name": "GST Registration", "price": "1,499", "icon": "📦"},
    {"name": "PTEC (Professional Tax — Individuals)", "price": "799", "icon": "💼"},
    {"name": "PTRC (Professional Tax — Employers)", "price": "999", "icon": "🏭"},
    {"name": "Freelancer Financial Checkup", "price": "999", "icon": "🩺"},
    {"name": "Udyam Registration (MSME)", "price": "499", "icon": "🏗️"},
]

SERVICE_DETAILS = [
    {
        "id": "gst",
        "icon": "📦",
        "name": "GST Filing",
        "tagline": "Stay compliant with monthly & quarterly GST returns",
        "meta_title": "GST Filing Services | GSTR-1 & GSTR-3B Returns | FilingDeck",
        "meta_description": "Affordable monthly GST filing services for MSMEs. GSTR-1 & GSTR-3B returns filed accurately and on time. Avoid penalties. Starting at ₹999/month.",
        "what": "Goods and Services Tax (GST) is a unified indirect tax levied on the supply of goods and services across India. Every registered business must file periodic returns (GSTR-1 for outward supplies and GSTR-3B for summary) declaring their sales, purchases, and tax liability.",
        "benefits": [
            "Avoid late-filing penalties of ₹50–₹200 per day",
            "Claim Input Tax Credit (ITC) to reduce your tax outflow",
            "Build a strong compliance record for business loans",
            "Seamless inter-state trade and e-commerce selling",
            "Maintain your GST registration (can be cancelled for non-filing)",
        ],
        "requirements": [
            "GST Registration Number (GSTIN)",
            "Sales & purchase invoices for the period",
            "Bank statement for the filing month",
            "HSN/SAC codes for goods or services supplied",
            "Previous return acknowledgements (if applicable)",
        ],
        "process_steps": [
            {"title": "Share Your Invoices", "desc": "Send us your sales and purchase invoices for the month via WhatsApp or email."},
            {"title": "We Reconcile & Prepare", "desc": "Our team reconciles your data, calculates ITC, and prepares GSTR-1 and GSTR-3B."},
            {"title": "Review & Approve", "desc": "We share a summary for your approval before filing. You confirm with a single message."},
            {"title": "Filed & Acknowledged", "desc": "We file on the GST portal and share the ARN (Acknowledgement Reference Number) with you."},
        ],
        "faqs": [
            {"q": "Who needs to file GST returns?", "a": "Any business with a GST registration must file returns, even if there is no business activity in that period (NIL return)."},
            {"q": "What is the due date for GSTR-3B?", "a": "For monthly filers, GSTR-3B is due by the 20th of the following month. For QRMP scheme (quarterly), it's the 22nd or 24th depending on your state."},
            {"q": "Can I claim ITC if I file late?", "a": "Yes, but you will incur a late fee and interest. Continuous late filing can also lead to GST registration cancellation."},
            {"q": "What happens if I don't file GST at all?", "a": "Your GST registration can be suspended or cancelled by the department. You will also face penalties of ₹50/day for GSTR-3B and ₹200/day for GSTR-1."},
        ],
        "penalty": "Late fee of ₹50/day (₹20 for NIL returns). Interest at 18% p.a. on outstanding tax. Continuous non-filing can lead to GST registration cancellation.",
        "color": "#6366f1",
    },
    {
        "id": "tds",
        "icon": "💰",
        "name": "TDS Returns",
        "tagline": "Quarterly deduction reporting — filed correctly, on time",
        "meta_title": "TDS Return Filing Services | Form 24Q, 26Q, 27Q | FilingDeck",
        "meta_description": "Expert TDS return filing for businesses. Quarterly Form 24Q, 26Q, 27Q filed accurately. Avoid ₹200/day penalties. Get Form 16/16A generated.",
        "what": "Tax Deducted at Source (TDS) requires businesses to deduct tax at prescribed rates when making payments like salaries, rent, professional fees, or contractor charges, and deposit it with the government. Quarterly TDS returns (Form 24Q, 26Q, 27Q) must be filed reporting all deductions.",
        "benefits": [
            "Avoid penalty of ₹200/day for late filing (u/s 234E)",
            "Ensure employees and vendors can claim their TDS credits",
            "Prevent notices from the Income Tax Department",
            "Maintain clean compliance for business audits",
            "Correct TDS certificates (Form 16/16A) for your team",
        ],
        "requirements": [
            "TAN (Tax Deduction Account Number)",
            "PAN of all deductees (employees, vendors, landlords)",
            "Details of payments made and tax deducted",
            "Challan details of TDS deposited with the government",
            "Previous quarter's return acknowledgement",
        ],
        "process_steps": [
            {"title": "Share Payment Details", "desc": "Send us details of all payments made during the quarter — salaries, rent, professional fees, etc."},
            {"title": "We Calculate & Prepare", "desc": "We calculate TDS liability for each deductee, match challan payments, and prepare the return."},
            {"title": "Filing on TRACES Portal", "desc": "We file the TDS return (24Q/26Q/27Q) on the TRACES portal and generate Form 16/16A for your employees and vendors."},
            {"title": "Acknowledgement & Certificates", "desc": "You receive the filing acknowledgement and TDS certificates to distribute to your team."},
        ],
        "faqs": [
            {"q": "When are TDS returns due?", "a": "TDS returns are filed quarterly. Q1 (Apr–Jun) by 31 Jul, Q2 (Jul–Sep) by 31 Oct, Q3 (Oct–Dec) by 31 Jan, Q4 (Jan–Mar) by 31 May."},
            {"q": "What is the penalty for late TDS filing?", "a": "A late fee of ₹200 per day is levied under Section 234E, capped at the total TDS amount. Additional penalty up to ₹1,00,000 under Section 271H."},
            {"q": "Do I need TAN to deduct TDS?", "a": "Yes. TAN (Tax Deduction Account Number) is mandatory for anyone who deducts or collects tax at source."},
            {"q": "What is Form 16 and who issues it?", "a": "Form 16 is a TDS certificate issued by employers to employees, summarizing salary paid and tax deducted during the financial year. FilingDeck generates this for you."},
        ],
        "penalty": "₹200/day late fee until the return is filed (capped at the TDS amount). Additional penalty up to ₹1,00,000 under Section 271H for incorrect filing.",
        "color": "#10b981",
    },
    {
        "id": "itr",
        "icon": "📊",
        "name": "Income Tax Return (ITR)",
        "tagline": "Annual income declaration — filed accurately for individuals & businesses",
        "meta_title": "Income Tax Return Filing | ITR-1 to ITR-7 | FilingDeck",
        "meta_description": "Professional ITR filing services for individuals, freelancers, and businesses. Maximize deductions, claim refunds. Avoid penalties up to ₹10,000.",
        "what": "Every individual, HUF, partnership firm, and company earning above the basic exemption limit must file an annual Income Tax Return declaring their total income, deductions, and tax payable. The correct ITR form (ITR-1 through ITR-7) depends on the nature and source of income.",
        "benefits": [
            "Claim refunds on excess tax paid or TDS deducted",
            "Essential document for loan applications and visa processing",
            "Carry forward business losses to offset future profits",
            "Avoid penalties of up to ₹10,000 for late filing",
            "Build a financial track record for your business",
        ],
        "requirements": [
            "PAN Card",
            "Form 16 (for salaried individuals) / Form 16A",
            "Bank statements and interest certificates",
            "Investment proofs (80C, 80D, HRA receipts, etc.)",
            "Capital gains statements (if any shares/property sold)",
            "Business P&L statement and Balance Sheet (for businesses)",
        ],
        "process_steps": [
            {"title": "Gather Documents", "desc": "Share your Form 16, bank statements, investment proofs, and any other income documents with us."},
            {"title": "Tax Computation", "desc": "We calculate your total income, apply all eligible deductions (80C, 80D, HRA, etc.), and compute your final tax liability."},
            {"title": "Select Correct ITR Form", "desc": "Based on your income sources, we select the appropriate form — ITR-1 for salaried, ITR-3 for business, ITR-4 for presumptive, etc."},
            {"title": "File & Get Acknowledgement", "desc": "We file on the Income Tax portal, e-verify using Aadhaar OTP, and share the ITR-V acknowledgement with you."},
        ],
        "faqs": [
            {"q": "What is the ITR filing deadline?", "a": "For individuals and non-audit cases, the deadline is usually 31st July. For businesses requiring audit, it's 31st October."},
            {"q": "Which ITR form should I use?", "a": "ITR-1 (Sahaj) for salaried individuals, ITR-3 for business/profession income, ITR-4 (Sugam) for presumptive taxation. We select the right one for you."},
            {"q": "Can I file ITR if I have no income?", "a": "Yes! Filing a NIL return builds your financial history and is useful for loan applications and visa processing."},
            {"q": "What deductions can I claim?", "a": "Common deductions include Section 80C (PPF, ELSS, LIC — up to ₹1.5L), 80D (health insurance), 80TTA (savings interest), HRA, and more."},
        ],
        "penalty": "Late filing fee of ₹5,000 (₹1,000 if income is below ₹5 lakh). Interest at 1% per month on unpaid tax under Section 234A.",
        "color": "#f59e0b",
    },
    {
        "id": "pt",
        "icon": "💼",
        "name": "Professional Tax",
        "tagline": "State-level employment tax — mandatory in Maharashtra",
        "meta_title": "Professional Tax Filing | PTEC & PTRC Registration | FilingDeck",
        "meta_description": "Professional Tax registration and return filing in Maharashtra. PTEC for individuals, PTRC for employers. Stay compliant with state tax laws.",
        "what": "Professional Tax is a state government tax levied on all salaried employees, professionals, and business owners in Maharashtra. Employers must register for PTRC (to deduct from employee salaries) and individuals must register for PTEC (for self-employment). Monthly or annual returns must be filed depending on the liability.",
        "benefits": [
            "Stay compliant with Maharashtra state tax laws",
            "Avoid penalties and interest on late payments",
            "PT paid is deductible from income tax (reduces your ITR liability)",
            "Mandatory for shop & establishment license renewals",
            "Clean compliance record for government tenders",
        ],
        "requirements": [
            "PAN of the business / individual",
            "Certificate of Incorporation or Shop License",
            "Employee salary details and headcount",
            "Previous PT payment challans",
            "PTEC / PTRC registration number",
        ],
        "process_steps": [
            {"title": "Registration Check", "desc": "We verify if you have PTEC (individual) and/or PTRC (employer) registration. If not, we register you first."},
            {"title": "Calculate Liability", "desc": "Based on employee salaries and headcount, we calculate the monthly/annual PT liability."},
            {"title": "Payment & Challan", "desc": "We generate the challan and facilitate payment to the Maharashtra government portal."},
            {"title": "File Return", "desc": "We file the periodic PT return and share the acknowledgement with you."},
        ],
        "faqs": [
            {"q": "What is the Professional Tax rate in Maharashtra?", "a": "For salaried individuals earning above ₹10,000/month, the PT is ₹200/month (₹300 in February). For self-employed professionals, it's ₹2,500/year."},
            {"q": "What is the difference between PTEC and PTRC?", "a": "PTEC (Professional Tax Enrollment Certificate) is for individuals/self-employed. PTRC (Professional Tax Registration Certificate) is for employers who deduct PT from employee salaries."},
            {"q": "Is Professional Tax deductible from income tax?", "a": "Yes. PT paid is allowed as a deduction from your gross salary income when computing income tax."},
            {"q": "What is the penalty for not paying Professional Tax?", "a": "Interest of 1.25% per month on delayed payment, plus an additional penalty of 10% of the amount due."},
        ],
        "penalty": "Interest at 1.25% per month on delayed payment. Additional penalty of 10% of the amount due.",
        "color": "#8b5cf6",
    },
    {
        "id": "udyam",
        "icon": "🏗️",
        "name": "Udyam Registration (MSME)",
        "tagline": "Official government recognition as a Micro, Small, or Medium Enterprise",
        "meta_title": "Udyam Registration | MSME Certificate Online | FilingDeck",
        "meta_description": "Get your Udyam (MSME) Registration certificate. Unlock priority bank loans, government subsidies, and tender preferences. Quick and hassle-free.",
        "what": "Udyam Registration is the government's official process to classify and certify a business as an MSME (Micro, Small, or Medium Enterprise) based on investment in plant/machinery and annual turnover. It replaced the old Udyog Aadhaar system and is completely free on the government portal, but the process requires accurate classification.",
        "benefits": [
            "Priority sector lending — easier and cheaper bank loans",
            "Collateral-free loans under CGTMSE scheme",
            "Protection against delayed payments (MSMED Act)",
            "50% subsidy on patent and trademark registration",
            "Preference in government tenders and procurement",
            "Lower electricity bills in some states",
            "Exemption from direct tax in initial years (for manufacturing)",
        ],
        "requirements": [
            "Aadhaar number of the proprietor / managing partner / director",
            "PAN and GSTIN of the business (if registered)",
            "Business bank account details",
            "Details of investment in plant & machinery / equipment",
            "Annual turnover details",
            "NIC Code (National Industrial Classification) for the activity",
        ],
        "process_steps": [
            {"title": "Share Business Details", "desc": "Provide your Aadhaar, PAN, GSTIN, and details about your business activity, investment, and turnover."},
            {"title": "Classification", "desc": "We determine your MSME category (Micro, Small, or Medium) based on government criteria for investment and turnover."},
            {"title": "Portal Registration", "desc": "We complete the Udyam Registration form on the official government portal with all your verified details."},
            {"title": "Certificate Issued", "desc": "You receive your official Udyam Registration Certificate with a permanent Udyam Registration Number (URN)."},
        ],
        "faqs": [
            {"q": "What is the difference between Micro, Small, and Medium?", "a": "Micro: Investment up to ₹1 Cr & Turnover up to ₹5 Cr. Small: Investment up to ₹10 Cr & Turnover up to ₹50 Cr. Medium: Investment up to ₹50 Cr & Turnover up to ₹250 Cr."},
            {"q": "Is Udyam Registration free?", "a": "Yes, registration on the government portal is completely free. FilingDeck charges a small service fee for handling the process and ensuring accurate classification."},
            {"q": "Can service businesses register as MSME?", "a": "Yes! Both manufacturing and service enterprises are eligible for Udyam Registration under the same criteria."},
            {"q": "Does Udyam Registration expire?", "a": "No. Udyam Registration is permanent and does not need to be renewed. However, you should update details if your turnover or investment changes significantly."},
        ],
        "penalty": "No penalty for not registering, but the business misses out on subsidies, easier loans, and government scheme benefits worth lakhs.",
        "color": "#f472b6",
    },
    {
        "id": "pan",
        "icon": "🪪",
        "name": "PAN Application",
        "tagline": "Apply for a new Permanent Account Number for Individuals or Businesses",
        "meta_title": "PAN Card Application | Individual & Business | FilingDeck",
        "meta_description": "Apply for a new PAN card online. Fast processing for individuals, companies, and partnership firms. Starting at ₹499.",
        "what": "A Permanent Account Number (PAN) is a ten-character alphanumeric identifier issued by the Income Tax Department. It is mandatory for all taxpayers, businesses, and entities conducting high-value financial transactions in India.",
        "benefits": [
            "Mandatory for filing Income Tax Returns",
            "Required to open a business or personal bank account",
            "Needed for GST registration and company incorporation",
            "Prevents higher TDS deduction (20%) on your income",
            "Serves as a universally accepted identity proof",
        ],
        "requirements": [
            "Aadhaar Card (for individuals)",
            "Certificate of Incorporation / Partnership Deed (for businesses)",
            "Passport-size photographs (for individuals)",
            "Proof of Address and Identity",
        ],
        "process_steps": [
            {"title": "Submit Documents", "desc": "Send us your identity and address proof documents."},
            {"title": "Application Filing", "desc": "We prepare and file the Form 49A/49AA on the NSDL/UTIITSL portal."},
            {"title": "Verification", "desc": "We assist with Aadhaar e-KYC or digital signature verification."},
            {"title": "PAN Allotment", "desc": "You receive the e-PAN via email within a few days, followed by the physical card."},
        ],
        "faqs": [
            {"q": "How long does it take to get a PAN?", "a": "An e-PAN is typically generated within 2-4 working days. The physical card is delivered in 10-15 days."},
            {"q": "Do I need a separate PAN for my business?", "a": "Yes, if you have a Private Limited Company, LLP, or Partnership Firm, it must have its own PAN. Proprietorships use the owner's individual PAN."},
        ],
        "penalty": "A penalty of ₹10,000 can be levied under Section 272B for not having a PAN when required, or for possessing more than one PAN.",
        "color": "#3b82f6",
    },
    {
        "id": "tan",
        "icon": "📋",
        "name": "TAN Application",
        "tagline": "Tax Deduction and Collection Account Number for Businesses",
        "meta_title": "TAN Registration Services | FilingDeck",
        "meta_description": "Get your TAN (Tax Deduction Account Number) registered. Mandatory for businesses deducting TDS. Fast processing at ₹499.",
        "what": "TAN is a 10-digit alphanumeric number issued by the Income Tax Department. It is mandatory for all persons (including businesses) who are responsible for deducting or collecting tax at source (TDS/TCS) on behalf of the government.",
        "benefits": [
            "Legal compliance for deducting TDS on salaries and vendor payments",
            "Allows you to file quarterly TDS returns",
            "Enables issuance of Form 16 and Form 16A to your team",
            "Prevents heavy penalties for non-deduction of TDS",
        ],
        "requirements": [
            "PAN Card of the business or individual",
            "Incorporation Certificate (for companies)",
            "Address proof of the business location",
            "Digital Signature Certificate (for online verification)",
        ],
        "process_steps": [
            {"title": "Document Collection", "desc": "Provide your business PAN and address details."},
            {"title": "Form 49B Filing", "desc": "We prepare and submit Form 49B to the Income Tax Department."},
            {"title": "Verification & Processing", "desc": "We track the application status and resolve any discrepancies."},
            {"title": "TAN Allotment", "desc": "You receive your official TAN allotment letter from the department."},
        ],
        "faqs": [
            {"q": "Is TAN different from PAN?", "a": "Yes. PAN is for paying your own taxes. TAN is specifically for deducting taxes from payments made to others and depositing it with the government."},
            {"q": "Who needs to apply for TAN?", "a": "Any business or individual (liable for tax audit) making payments like salary, rent, or professional fees that exceed the TDS threshold must get a TAN."},
        ],
        "penalty": "Failure to apply for a TAN or not quoting it in TDS documents attracts a penalty of ₹10,000 under Section 272BB.",
        "color": "#8b5cf6",
    },
    {
        "id": "gst-reg",
        "icon": "🏢",
        "name": "GST Registration",
        "tagline": "Get your business officially registered under GST",
        "meta_title": "GST Registration Online | Fast & Hassle-Free | FilingDeck",
        "meta_description": "Register your business for GST online. Get your GSTIN quickly with expert assistance. Mandatory for businesses crossing turnover limits.",
        "what": "GST Registration is the process by which a taxpayer gets themselves registered under GST. Once a business is successfully registered, a unique 15-digit Goods and Services Tax Identification Number (GSTIN) is assigned to them.",
        "benefits": [
            "Legally recognized as a supplier of goods or services",
            "Ability to legally collect taxes from buyers",
            "Claim Input Tax Credit (ITC) on purchases",
            "Seamless inter-state sales and e-commerce selling",
            "Enhances business credibility and trust",
        ],
        "requirements": [
            "PAN and Aadhaar of the applicant",
            "Proof of business registration (Incorporation Certificate, etc.)",
            "Identity and Address proof of Promoters/Director with Photographs",
            "Address proof of the place of business (Rent agreement + NOC + Electricity bill)",
            "Bank Account Statement or Cancelled Cheque",
        ],
        "process_steps": [
            {"title": "Document Verification", "desc": "We collect and verify all required documents for accuracy."},
            {"title": "Application Filing", "desc": "We submit the GST registration application on the official GST portal."},
            {"title": "ARN Generation", "desc": "An Application Reference Number (ARN) is generated to track status."},
            {"title": "GSTIN Allotment", "desc": "Upon approval, the department issues your GST Registration Certificate and GSTIN."},
        ],
        "faqs": [
            {"q": "When is GST registration mandatory?", "a": "It is mandatory if your annual turnover exceeds ₹40 Lakhs (for goods) or ₹20 Lakhs (for services). It's also mandatory for inter-state sales and e-commerce operators."},
            {"q": "Can I voluntarily register for GST?", "a": "Yes, even if your turnover is below the limit, you can register voluntarily to claim ITC or sell on platforms like Amazon/Flipkart."},
        ],
        "penalty": "Operating without GST registration when liable attracts a penalty of 10% of the tax due (minimum ₹10,000) or up to 100% of tax evaded.",
        "color": "#f59e0b",
    },
    {
        "id": "freelance-check",
        "icon": "🩺",
        "name": "Freelancer Financial Checkup",
        "tagline": "A complete review of your tax structure and compliance health",
        "meta_title": "Freelancer Financial & Tax Checkup | FilingDeck",
        "meta_description": "Get a comprehensive financial checkup for your freelance business. Optimize taxes, review compliance, and plan for growth.",
        "what": "A comprehensive review designed specifically for freelancers, consultants, and gig workers. We analyze your income streams, current tax structure, deductions, and compliance status to identify risks and opportunities for saving money.",
        "benefits": [
            "Identify missed tax deductions and saving opportunities",
            "Ensure you are fully compliant with current tax laws",
            "Get advice on whether to opt for the Presumptive Taxation Scheme (Section 44ADA)",
            "Plan your advance tax payments to avoid interest penalties",
            "Gain peace of mind regarding your financial health",
        ],
        "requirements": [
            "Details of your income sources and clients",
            "Bank statements for the current financial year",
            "Previous year's ITR acknowledgement (if applicable)",
            "List of business expenses and investments",
        ],
        "process_steps": [
            {"title": "Information Gathering", "desc": "You share a quick overview of your freelance income and expenses."},
            {"title": "Detailed Analysis", "desc": "Our CA experts analyze your financial data and tax structure."},
            {"title": "1-on-1 Consultation", "desc": "We get on a call with you to discuss our findings and recommendations."},
            {"title": "Action Plan", "desc": "We provide a tailored action plan to optimize your taxes and compliance."},
        ],
        "faqs": [
            {"q": "What is Section 44ADA?", "a": "It's a presumptive taxation scheme for freelancers/professionals where you can declare 50% of your gross receipts as profit, saving you from maintaining detailed books of accounts."},
            {"q": "Is this checkup necessary if I earn less than 5 lakhs?", "a": "Yes, even with lower income, structuring it correctly can prevent future notices and build a strong financial record for loans or visas."},
        ],
        "penalty": "No specific penalty, but ignoring financial health can lead to missed savings, incorrect filings, and unexpected tax liabilities.",
        "color": "#10b981",
    },
    {
        "id": "accounting",
        "icon": "📊",
        "name": "Accounting & Bookkeeping",
        "tagline": "Ongoing, year-round maintenance of your books, tailored to your business volume",
        "meta_title": "Accounting & Bookkeeping Services | FilingDeck",
        "meta_description": "Professional accounting and bookkeeping services for MSMEs and freelancers. Clean books, accurate P&L, and seamless tax prep.",
        "what": "Accounting and bookkeeping is a continuous, year-round service—not a one-time task. We maintain the daily recording of all your financial transactions throughout the year, generating accurate financial statements (P&L, Balance Sheet) to give you constant insights into your business health.",
        "benefits": [
            "Clear visibility into your business profitability",
            "Easier and faster GST and Income Tax filings",
            "Better cash flow management and tracking of receivables",
            "Ready financials for bank loans or investor pitching",
            "Audit-ready books at all times",
        ],
        "requirements": [
            "Bank statements for the period",
            "Sales and purchase invoices",
            "Details of expenses (receipts/bills)",
            "Loan statements (if any)",
            "Previous year's audited financials (if applicable)",
        ],
        "process_steps": [
            {"title": "Data Collection", "desc": "Share your monthly bank statements and invoices with us securely."},
            {"title": "Recording & Categorization", "desc": "Our team records transactions and categorizes income and expenses accurately."},
            {"title": "Reconciliation", "desc": "We reconcile your books with bank statements to ensure zero discrepancies."},
            {"title": "Reporting", "desc": "Receive monthly or quarterly financial summaries of your business health."},
        ],
        "faqs": [
            {"q": "Is this a one-time service?", "a": "No, accounting and bookkeeping is an ongoing, year-round engagement. We continuously maintain your books to ensure your financials are always up-to-date."},
            {"q": "How much does it cost?", "a": "Our monthly pricing is custom because it depends entirely on the volume of transactions you have per month. Reach out for a quick quote."},
        ],
        "penalty": "Poor accounting leads to missed tax deductions, incorrect tax filings resulting in notices, and cash flow crises.",
        "color": "#3b82f6",
    },
]

TEAM_MEMBERS = [
    {
        "name": "Kavya Kajavadra",
        "role": "Tech Lead",
        "credential": "Web Developer",
        "description": "Builds the platform, automates workflows, and ensures a seamless digital experience for every client.",
        "initials": "K",
        "color": "#6366f1",
    },
    {
        "name": "Parth Mehta",
        "role": "Tax & Compliance",
        "credential": "CA Finalist",
        "description": "Handles GST filing, TDS returns, income tax, and ensures your tax compliance is always on track.",
        "initials": "P",
        "color": "#10b981",
    },
    {
        "name": "Yug Jain",
        "role": "Tax Advisory",
        "credential": "CA Aspirant",
        "description": "Specializes in tax planning, financial advisory, and helping businesses optimize their tax structure.",
        "initials": "Y",
        "color": "#f59e0b",
    },
    {
        "name": "Deep Patel",
        "role": "Accounting Operations",
        "credential": "BAF | Taxation & Tally",
        "description": "Handles cloud bookkeeping, GST data prep, e-Way bills, and in-depth research and analysis to keep client operations smooth.",
        "initials": "D",
        "color": "#8b5cf6",
    },
    {
        "name": "Nilkanth Saliya",
        "role": "Financial Planning",
        "credential": "BFM Student",
        "description": "Provides financial market insights, investment guidance, and helps clients with banking and loan advisory.",
        "initials": "N",
        "color": "#8b5cf6",
    },
    {
        "name": "Bhavyy Jain",
        "role": "Legal & Compliance Advisory",
        "credential": "CS Executive",
        "description": "Specializes in MSME registrations, business licensing, trademark filing, and drafting rock-solid contracts for freelancers and partnerships.",
        "initials": "B",
        "color": "#ef4444",
    },
]

FAQ_ITEMS = [
    {
        "question": "Who is FilingDeck for?",
        "answer": "FilingDeck is for small business owners, freelancers, startups, and MSMEs in Mumbai, Thane, and Navi Mumbai who need affordable, reliable compliance and tax filing services.",
    },
    {
        "question": "How is FilingDeck different from a traditional CA firm?",
        "answer": "We combine professional CA/CS expertise with technology. You get automated reminders, a compliance calendar, digital communication via WhatsApp, and transparent pricing — all at a fraction of what traditional firms charge.",
    },
    {
        "question": "What if I miss a filing deadline?",
        "answer": "That's exactly what we prevent! Our compliance calendar tracks every deadline and sends you reminders well in advance. If you're already late, we'll help you file and minimize penalties.",
    },
    {
        "question": "Can I start with just one service?",
        "answer": "Absolutely. You can start with a single GST filing or a one-time service like GST Registration. No lock-in contracts — upgrade anytime.",
    },
    {
        "question": "Is my financial data safe with FilingDeck?",
        "answer": "Yes. We follow strict data confidentiality practices. Your financial information is only used for filing purposes and is never shared with third parties.",
    },
    {
        "question": "Do you serve businesses outside Mumbai/Thane?",
        "answer": "Yes! While our core team is based in Mumbai/Thane, all our services are delivered digitally. We can serve businesses across Maharashtra and India.",
    },
]


# ── Template Context Processor ───────────────────────────────────────────────

@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    return {
        "whatsapp_link": f"https://wa.me/{WHATSAPP_NUMBER}?text={WHATSAPP_MESSAGE.replace(' ', '%20')}",
        "current_year": datetime.now().year,
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Homepage — hero, pain points, services, how it works, team, compliance tool, FAQ."""
    return render_template(
        "index.html",
        plans=PLANS,
        team=TEAM_MEMBERS,
        faqs=FAQ_ITEMS,
        business_types=BUSINESS_TYPES,
        page_title="Affordable GST, Tax & Compliance Services | Mumbai & Thane",
        page_description="FilingDeck offers affordable GST filing, ROC compliance, tax advisory, and company incorporation services for MSMEs and freelancers in Mumbai & Thane. Starting at ₹999/month.",
    )

# ── Admin Auth ───────────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Please log in to access the admin dashboard.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Simple admin login page."""
    if request.method == "POST":
        password = request.form.get("password", "")
        admin_password = os.environ.get("ADMIN_PASSWORD", "Kaivabhai")
        
        if password == admin_password:
            session["is_admin"] = True
            flash("Welcome to the Admin Dashboard.", "success")
            return redirect(url_for("admin_leads"))
        else:
            flash("Invalid password.", "error")
            
    return render_template("admin_login.html", page_title="Admin Login")

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/admin/leads")
@admin_required
def admin_leads():
    """Hidden dashboard to view all incoming leads."""
    leads = Lead.query.order_by(Lead.id.desc()).all()
    return render_template("leads.html", leads=leads, page_title="Lead Dashboard")


@app.route("/services")
def services():
    """Detailed services page with pricing."""
    return render_template(
        "services.html",
        plans=PLANS,
        one_time_services=ONE_TIME_SERVICES,
        service_details=SERVICE_DETAILS,
        page_title="Services & Pricing",
        page_description="Explore FilingDeck's compliance packages and one-time services. GST filing, TDS, ROC, company incorporation, and more — all at transparent, affordable prices.",
    )


@app.route("/services/<service_id>")
def service_detail(service_id):
    """Dedicated detail page for a specific service."""
    svc = next((s for s in SERVICE_DETAILS if s["id"] == service_id), None)
    if not svc:
        return redirect(url_for("services"))
    # Get other services for the sidebar / "More Services" section
    other_services = [s for s in SERVICE_DETAILS if s["id"] != service_id]
    return render_template(
        "service_detail.html",
        svc=svc,
        other_services=other_services,
        page_title=svc.get("meta_title", svc["name"] + " | FilingDeck"),
        page_description=svc.get("meta_description", svc["tagline"]),
    )


@app.route("/dashboard")
def dashboard():
    """Render the logged-in dashboard view."""
    # Fetch the first user (mock logged-in user)
    user = User.query.first()
    if user:
        decks = Deck.query.filter_by(user_id=user.id).all()
    else:
        decks = []
    
    return render_template("dashboard.html", user=user, decks=decks)


@app.route("/deck/<deck_id>")
def deck_detail(deck_id):
    """Render the detail view for a specific deck."""
    deck = Deck.query.get_or_404(deck_id)
    # Fetch user for the sidebar
    user = User.query.get(deck.user_id)
    return render_template("deck_detail.html", deck=deck, user=user)


@app.route("/about")
def about():
    """About page with team profiles."""
    return render_template(
        "about.html",
        team=TEAM_MEMBERS,
        page_title="About Us — Meet the FilingDeck Team",
        page_description="Meet the FilingDeck team — young CA, CS, and tech professionals making compliance affordable and hassle-free for MSMEs in Mumbai and Thane.",
    )


@app.route("/contact", methods=["GET", "POST"])
def contact():
    """Contact page with form handling."""
    if request.method == "POST":
        lead = Lead(
            name=request.form.get("name", "").strip(),
            email=request.form.get("email", "").strip(),
            phone=request.form.get("phone", "").strip(),
            business_name=request.form.get("business_name", "").strip(),
            business_type=request.form.get("business_type", "").strip(),
            service_interested=", ".join(request.form.getlist("service_interested")),
            message=request.form.get("message", "").strip(),
            source="contact_form",
        )
        db.session.add(lead)
        db.session.commit()
        
        # Send background email notification
        notify_new_lead(lead)
        
        flash("Thank you! We'll reach out to you within 24 hours.", "success")
        return redirect(url_for("contact"))

    return render_template(
        "contact.html",
        business_types=BUSINESS_TYPES,
        plans=PLANS,
        one_time_services=ONE_TIME_SERVICES,
        page_title="Contact Us",
        page_description="Get in touch with FilingDeck for GST filing, tax advisory, company incorporation, and compliance services in Mumbai and Thane.",
    )


@app.route("/compliance-calendar", methods=["POST"])
def compliance_calendar():
    """Process compliance calendar form and show results."""
    business_type = request.form.get("business_type", "proprietorship")
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()

    # Save as lead
    if name and phone:
        lead = Lead(
            name=name,
            phone=phone,
            business_type=business_type,
            source="compliance_calendar",
        )
        db.session.add(lead)
        db.session.commit()
        
        # Send background email notification
        notify_new_lead(lead)

    # Calculate deadlines
    deadlines = calculate_upcoming_deadlines(business_type)
    summary = get_compliance_summary(business_type)
    business_label = BUSINESS_TYPES.get(business_type, business_type)

    return render_template(
        "calendar_results.html",
        deadlines=deadlines,
        summary=summary,
        business_type=business_label,
        page_title=f"Compliance Calendar — {business_label}",
        page_description=f"Your personalized compliance calendar for {business_label}. See all upcoming GST, TDS, ROC, and tax filing deadlines.",
    )


# ── WhatsApp AI Webhook ──────────────────────────────────────────────────────

@app.route("/whatsapp/webhook", methods=["POST"])
def whatsapp_webhook():
    """Endpoint for Twilio to send incoming WhatsApp messages."""
    incoming_msg = request.values.get("Body", "").strip()
    sender_phone = request.values.get("From", "")

    # Retrieve or create session
    session = WhatsAppSession.query.filter_by(phone_number=sender_phone).first()
    if not session:
        session = WhatsAppSession(phone_number=sender_phone)
        db.session.add(session)
        db.session.commit()
        
    session.last_message_at = datetime.utcnow()
    
    twiml_response = MessagingResponse()

    # If already handed off, do not let AI respond
    if session.needs_human:
        db.session.commit()
        return str(twiml_response) # Send empty response (human will reply)

    # Get conversation history
    history = session.get_history()
    
    # Generate AI response
    ai_result = get_ai_response(incoming_msg, history)
    reply_text = ai_result["text"]
    
    # Update history
    history.append({"role": "user", "parts": [incoming_msg]})
    history.append({"role": "model", "parts": [reply_text]})
    
    # Keep history manageable (last 10 turns = 20 messages)
    if len(history) > 20:
        history = history[-20:]
        
    session.set_history(history)
    
    # Check if handoff was triggered
    if ai_result["handoff"]:
        session.needs_human = True
        
    db.session.commit()
    
    # Send reply via Twilio
    msg = twiml_response.message()
    msg.body(reply_text)
    
    return str(twiml_response)


# ── SEO & Indexing ───────────────────────────────────────────────────────────

@app.route("/robots.txt")
def robots_txt():
    """Tells search engines what they can index."""
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {request.url_root.rstrip('/')}/sitemap.xml"
    ]
    response = make_response("\n".join(lines))
    response.headers["Content-Type"] = "text/plain"
    return response

@app.route("/sitemap.xml")
def sitemap():
    """Generates a dynamic XML sitemap for search engines."""
    base_url = request.url_root.rstrip('/')
    
    # Static pages
    pages = [
        {"loc": f"{base_url}/", "priority": "1.0"},
        {"loc": f"{base_url}/about", "priority": "0.8"},
        {"loc": f"{base_url}/services", "priority": "0.9"},
        {"loc": f"{base_url}/contact", "priority": "0.8"},
    ]
    
    # Dynamic service pages
    for service in SERVICE_DETAILS:
        pages.append({
            "loc": f"{base_url}/services/{service['id']}",
            "priority": "0.7"
        })
        
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for page in pages:
        xml_content += "  <url>\n"
        xml_content += f"    <loc>{page['loc']}</loc>\n"
        xml_content += f"    <priority>{page['priority']}</priority>\n"
        xml_content += "  </url>\n"
        
    xml_content += "</urlset>"
    
    response = make_response(xml_content)
    response.headers["Content-Type"] = "application/xml"
    return response


# ── Database Initialization ──────────────────────────────────────────────────

with app.app_context():
    try:
        db.create_all()
        # Seed the database with a user and some decks if it's empty
        if not User.query.first():
            demo_user = User(name="Kavya", email="kavya@example.com")
            db.session.add(demo_user)
            db.session.commit()
            
            deck1 = Deck(user_id=demo_user.id, name="Q1 Tax Documents", file_count=12, last_modified="2 hours ago")
            deck2 = Deck(user_id=demo_user.id, name="Company Incorporation", file_count=5, last_modified="1 day ago")
            deck3 = Deck(user_id=demo_user.id, name="GST Returns 2025", file_count=24, last_modified="Just now")
            db.session.add_all([deck1, deck2, deck3])
            db.session.commit()
    except Exception as e:
        print(f"Warning: Could not create database tables (expected on read-only serverless platforms): {e}")


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)
