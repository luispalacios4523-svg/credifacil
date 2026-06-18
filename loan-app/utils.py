from datetime import date
from dateutil.relativedelta import relativedelta


def calculate_amortization(principal: float, annual_rate: float, term_months: int, start_date: date = None):
    """
    Calcula el plan de amortización francés (cuota fija).
    Retorna (monthly_payment, total_payment, installments_list)
    """
    if start_date is None:
        start_date = date.today()

    r = (annual_rate / 100) / 12  # tasa mensual

    if r == 0:
        monthly_payment = principal / term_months
    else:
        monthly_payment = principal * (r * (1 + r) ** term_months) / ((1 + r) ** term_months - 1)

    monthly_payment = round(monthly_payment, 2)
    balance = principal
    installments = []

    for i in range(1, term_months + 1):
        interest = round(balance * r, 2)
        capital = round(monthly_payment - interest, 2)
        # última cuota: ajustar diferencias de redondeo
        if i == term_months:
            capital = round(balance, 2)
            monthly_payment_i = round(capital + interest, 2)
        else:
            monthly_payment_i = monthly_payment

        balance = round(balance - capital, 2)
        due = start_date + relativedelta(months=i)

        installments.append({
            "number": i,
            "due_date": due,
            "amount": monthly_payment_i,
            "principal": capital,
            "interest": interest,
            "balance": max(balance, 0),
        })

    total_payment = round(sum(inst["amount"] for inst in installments), 2)
    return monthly_payment, total_payment, installments
