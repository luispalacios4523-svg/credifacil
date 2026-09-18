from datetime import date
from dateutil.relativedelta import relativedelta


def calculate_amortization(principal: float, monthly_rate: float, term_months: int,
                           handling_fee: float = 0, start_date: date = None):
    """
    Calcula el plan de amortización francés (cuota fija).
    monthly_rate es el interés mensual en porcentaje (4 = 4% mensual).
    handling_fee es la cuota de manejo fija que se suma a cada cuota.
    Retorna (monthly_payment, total_payment, installments_list)
    """
    if start_date is None:
        start_date = date.today()

    r = monthly_rate / 100

    if r == 0:
        base_payment = principal / term_months
    else:
        base_payment = principal * (r * (1 + r) ** term_months) / ((1 + r) ** term_months - 1)

    base_payment = round(base_payment)
    balance = principal
    installments = []

    for i in range(1, term_months + 1):
        interest = round(balance * r)
        capital = base_payment - interest
        # última cuota: ajustar diferencias de redondeo
        if i == term_months:
            capital = round(balance)
        balance = round(balance - capital)
        due = start_date + relativedelta(months=i)

        installments.append({
            "number": i,
            "due_date": due,
            "amount": capital + interest + handling_fee,
            "principal": capital,
            "interest": interest,
            "fee": handling_fee,
            "balance": max(balance, 0),
        })

    monthly_payment = base_payment + handling_fee
    total_payment = sum(inst["amount"] for inst in installments)
    return monthly_payment, total_payment, installments
