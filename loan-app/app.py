import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, User, LoanApplication, LoanInstallment
from utils import calculate_amortization

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

# Base de datos: PostgreSQL en Railway, SQLite en local
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///loans.db")
# Railway usa postgres://, SQLAlchemy necesita postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


@app.template_filter("cop")
def format_cop(value):
    """Formato de pesos colombianos: 1500000 -> $1.500.000"""
    return "$" + f"{value:,.0f}".replace(",", ".")

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Debes iniciar sesión para acceder."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Acceso restringido a administradores.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


# ── Inicializar DB y admin por defecto ──────────────────────────────────────

@app.before_request
def create_tables():
    db.create_all()
    # Crear admin por defecto si no existe
    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            name="Administrador",
            email=os.environ.get("ADMIN_EMAIL", "admin@loans.com"),
            password_hash=generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123")),
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()


# ── Rutas públicas ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not name or not email or not password:
            flash("Todos los campos son obligatorios.", "danger")
        elif password != confirm:
            flash("Las contraseñas no coinciden.", "danger")
        elif len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("Ya existe una cuenta con ese correo.", "danger")
        else:
            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash(f"¡Bienvenido, {name}!", "success")
            return redirect(url_for("dashboard"))

    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f"¡Bienvenido de vuelta, {user.name}!", "success")
            return redirect(url_for("admin_dashboard") if user.is_admin else url_for("dashboard"))
        flash("Correo o contraseña incorrectos.", "danger")
    return render_template("auth/login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("index"))


# ── Cliente ──────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))
    loans = LoanApplication.query.filter_by(user_id=current_user.id).order_by(LoanApplication.created_at.desc()).all()
    return render_template("client/dashboard.html", loans=loans)


@app.route("/apply", methods=["GET", "POST"])
@login_required
def apply():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0))
            term = int(request.form.get("term_months", 0))
            purpose = request.form.get("purpose", "").strip()

            if amount < 300000 or amount > 3000000:
                flash("El monto debe estar entre $300.000 y $3.000.000.", "danger")
            elif term < 1 or term > 60:
                flash("El plazo debe estar entre 1 y 60 meses.", "danger")
            elif not purpose:
                flash("Debes indicar el propósito del préstamo.", "danger")
            else:
                loan = LoanApplication(
                    user_id=current_user.id,
                    amount=amount,
                    term_months=term,
                    purpose=purpose,
                    annual_rate=18.0,
                )
                db.session.add(loan)
                db.session.commit()
                flash("Solicitud enviada con éxito. Te notificaremos cuando sea revisada.", "success")
                return redirect(url_for("dashboard"))
        except ValueError:
            flash("Datos inválidos. Verifica el monto y el plazo.", "danger")

    return render_template("client/apply.html")


@app.route("/loan/<int:loan_id>")
@login_required
def loan_detail(loan_id):
    loan = LoanApplication.query.get_or_404(loan_id)
    if not current_user.is_admin and loan.user_id != current_user.id:
        flash("No tienes permiso para ver este préstamo.", "danger")
        return redirect(url_for("dashboard"))
    return render_template("client/loan_detail.html", loan=loan)


# ── Admin ────────────────────────────────────────────────────────────────────

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    status_filter = request.args.get("status", "all")
    query = LoanApplication.query
    if status_filter != "all":
        query = query.filter_by(status=status_filter)
    loans = query.order_by(LoanApplication.created_at.desc()).all()

    stats = {
        "total": LoanApplication.query.count(),
        "pending": LoanApplication.query.filter_by(status="pending").count(),
        "approved": LoanApplication.query.filter_by(status="approved").count(),
        "rejected": LoanApplication.query.filter_by(status="rejected").count(),
    }
    return render_template("admin/dashboard.html", loans=loans, stats=stats, status_filter=status_filter)


@app.route("/admin/loan/<int:loan_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_loan_detail(loan_id):
    loan = LoanApplication.query.get_or_404(loan_id)

    if request.method == "POST":
        action = request.form.get("action")
        note = request.form.get("admin_note", "").strip()
        rate = request.form.get("annual_rate")

        if action not in ("approve", "reject"):
            flash("Acción inválida.", "danger")
        elif loan.status != "pending":
            flash("Esta solicitud ya fue procesada.", "warning")
        else:
            loan.admin_note = note
            loan.reviewed_at = datetime.utcnow()

            if action == "approve":
                try:
                    loan.annual_rate = float(rate) if rate else 18.0
                except ValueError:
                    loan.annual_rate = 18.0

                monthly, total, plan = calculate_amortization(
                    loan.amount, loan.annual_rate, loan.term_months
                )
                loan.monthly_payment = monthly
                loan.total_payment = total
                loan.status = "approved"

                for inst in plan:
                    installment = LoanInstallment(
                        loan_id=loan.id,
                        number=inst["number"],
                        due_date=inst["due_date"],
                        amount=inst["amount"],
                        principal=inst["principal"],
                        interest=inst["interest"],
                        balance=inst["balance"],
                    )
                    db.session.add(installment)

                flash("Préstamo aprobado y plan de cuotas generado.", "success")
            else:
                loan.status = "rejected"
                flash("Solicitud rechazada.", "info")

            db.session.commit()
            return redirect(url_for("admin_loan_detail", loan_id=loan.id))

    return render_template("admin/loan_detail.html", loan=loan)


@app.route("/admin/installment/<int:inst_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_installment(inst_id):
    inst = LoanInstallment.query.get_or_404(inst_id)
    inst.paid = not inst.paid
    inst.paid_at = datetime.utcnow() if inst.paid else None
    db.session.commit()
    flash(f"Cuota #{inst.number} marcada como {'pagada' if inst.paid else 'pendiente'}.", "success")
    return redirect(url_for("admin_loan_detail", loan_id=inst.loan_id))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
