"""Auditable repairs, applied only to isolated scenario copies."""
from pathlib import Path


def replace(root: Path, file: str, before: str, after: str):
    path = root / file
    text = path.read_text(encoding="utf-8")
    if before not in text:
        raise ValueError(f"Repair precondition missing: {file}: {before!r}")
    path.write_text(text.replace(before, after), encoding="utf-8")


def apply(root: Path, scenario: str):
    if scenario == "s1-null-user":
        for file, expression, ident in [
            ("shop/orders/invoice.py", "user = get_user(order.user_id)", "order.user_id"),
            ("shop/payments/receipt.py", "user = get_user(payment.user_id)", "payment.user_id"),
        ]:
            p = root / file
            p.write_text("from shop.errors import NotFoundError\n" + p.read_text(), encoding="utf-8")
            replace(root, file, expression, expression + f"\n    if user is None:\n        raise NotFoundError('user', {ident})")
        replace(root, "shop/users/routes.py", "from fastapi import APIRouter", "from fastapi import APIRouter, HTTPException")
        replace(root, "shop/users/routes.py", "    return service.get_user(user_id)",
                "    user = service.get_user(user_id)\n    if user is None:\n        raise HTTPException(status_code=404, detail='user not found')\n    return user")
        replace(root, "shop/orders/service.py", "        get_user(data.user_id)",
                "        if get_user(data.user_id) is None:\n            raise NotFoundError('user', data.user_id)")
        p = root / "shop/payments/charge.py"
        p.write_text("from shop.errors import NotFoundError\n" + p.read_text(), encoding="utf-8")
        replace(root, "shop/payments/charge.py", "    get_user(user_id)",
                "    if get_user(user_id) is None:\n        raise NotFoundError('user', user_id)")
        p = root / "shop/admin/reports.py"
        p.write_text("from shop.errors import NotFoundError\n" + p.read_text(), encoding="utf-8")
        replace(root, "shop/admin/reports.py", '        rows.append({"user": get_user(order.user_id).name, "total": order.total})',
                "        user = get_user(order.user_id)\n        if user is None:\n            raise NotFoundError('user', order.user_id)\n        rows.append({\"user\": user.name, \"total\": order.total})")
    elif scenario == "s2-cents":
        (root / "shop/payments/amounts.py").write_text('''from dataclasses import dataclass

from shop.payments.charge import Payment


@dataclass(frozen=True)
class DollarPayment:
    user_id: int
    amount: float


def dollar_amount(payment: Payment | DollarPayment) -> float:
    """Convert charged cents once; persisted dollar values are already converted."""
    if isinstance(payment, DollarPayment):
        return payment.amount
    return payment.amount / 100
''', encoding="utf-8")
        for file in ["shop/payments/receipt.py", "shop/orders/invoice.py", "shop/notifications/email.py", "shop/admin/reports.py"]:
            p = root / file
            p.write_text("from shop.payments.amounts import DollarPayment, dollar_amount\n" + p.read_text(), encoding="utf-8")
            text = p.read_text().replace("payment: Payment", "payment: Payment | DollarPayment").replace("List[Payment]", "List[Payment | DollarPayment]")
            text = text.replace("{payment.amount:.2f}", "{dollar_amount(payment):.2f}").replace('"amount": payment.amount', '"amount": dollar_amount(payment)').replace("sum(p.amount for p in payments)", "sum(dollar_amount(p) for p in payments)")
            p.write_text(text, encoding="utf-8")
        p = root / "shop/payments/repo.py"
        text = p.read_text().replace("from shop.payments.charge import Payment", "from shop.payments.charge import Payment\nfrom shop.payments.amounts import DollarPayment, dollar_amount")
        text = text.replace("List[Payment]", "List[DollarPayment]")
        text = text.replace("def save_payment(payment: Payment) -> Payment:", "def save_payment(payment: Payment | DollarPayment) -> DollarPayment:")
        text = text.replace("    _PAYMENTS.append(payment)\n    return payment", "    stored = DollarPayment(payment.user_id, dollar_amount(payment))\n    _PAYMENTS.append(stored)\n    return stored")
        p.write_text(text, encoding="utf-8")
        # Existing fixtures construct Payment directly. Update their INPUTS to the new
        # cents representation, keeping every dollar-output assertion unchanged.
        for file in ["tests/payments/test_receipt.py", "tests/payments/test_receipt_more.py", "tests/orders/test_invoice.py", "tests/notifications/test_email.py"]:
            p = root / file
            text = p.read_text()
            for old, new in [("Payment(1, 103.2)", "Payment(1, 10320)"), ("Payment(2, 50.0)", "Payment(2, 5000)"), ("Payment(1, 10.0)", "Payment(1, 1000)"), ("Payment(1, 1000.0)", "Payment(1, 100000)")]:
                text = text.replace(old, new)
            p.write_text(text, encoding="utf-8")
        replace(root, "tests/payments/test_routes.py", '== 10320', '== 103.2')
    elif scenario == "s3-pydantic2":
        replace(root, "shop/config.py", "from pydantic import BaseSettings", "from pydantic_settings import BaseSettings")
        p = root / "requirements.txt"
        p.write_text(p.read_text() + "pydantic-settings==2.5.2\n", encoding="utf-8")
        p = root / "shop/users/schemas.py"
        text = p.read_text().replace("from pydantic import BaseModel, constr", "from typing import Annotated\n\nfrom pydantic import BaseModel, ConfigDict, StringConstraints")
        text = text.replace('constr(regex=r"^[^@]+@[^@]+$")', 'Annotated[str, StringConstraints(pattern=r"^[^@]+@[^@]+$")]')
        text = text.replace("    class Config:\n        orm_mode = True", "    model_config = ConfigDict(from_attributes=True)")
        p.write_text(text, encoding="utf-8")
        p = root / "shop/orders/schemas.py"
        text = p.read_text().replace("from pydantic import BaseModel, validator", "from pydantic import BaseModel, ConfigDict, field_validator")
        text = text.replace("note: Optional[str]", "note: Optional[str] = None")
        text = text.replace('@validator("tags", each_item=True)', '@field_validator("tags")\n    @classmethod')
        text = text.replace('return value.strip()', 'return [tag.strip() for tag in value]')
        text = text.replace("    class Config:\n        orm_mode = True", "    model_config = ConfigDict(from_attributes=True)")
        p.write_text(text, encoding="utf-8")
        replace(root, "shop/payments/schemas.py", "regex=", "pattern=")
    else:
        raise ValueError("Unknown scenario: " + scenario)
