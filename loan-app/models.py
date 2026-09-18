from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    loans = db.relationship("LoanApplication", backref="user", lazy=True)


class LoanApplication(db.Model):
    __tablename__ = "loan_applications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    term_months = db.Column(db.Integer, nullable=False)
    purpose = db.Column(db.String(300), nullable=False)
    monthly_rate = db.Column(db.Float, default=4.0)  # porcentaje mensual
    handling_fee = db.Column(db.Float, default=30000)  # cuota de manejo mensual
    status = db.Column(db.String(20), default="pending")  # pending / approved / rejected
    admin_note = db.Column(db.String(500))
    monthly_payment = db.Column(db.Float)
    total_payment = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    installments = db.relationship("LoanInstallment", backref="loan", lazy=True, order_by="LoanInstallment.number")


class LoanInstallment(db.Model):
    __tablename__ = "loan_installments"
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey("loan_applications.id"), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)       # cuota total
    principal = db.Column(db.Float, nullable=False)    # capital
    interest = db.Column(db.Float, nullable=False)     # interés
    fee = db.Column(db.Float, nullable=False, default=0)  # cuota de manejo
    balance = db.Column(db.Float, nullable=False)      # saldo tras pago
    paid = db.Column(db.Boolean, default=False)
    paid_at = db.Column(db.DateTime)
