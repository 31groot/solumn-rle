"""Grader's reference for the users_contact columns (README.md rules)."""
CALLING_CODE = {"IN": "91", "US": "1", "GB": "44"}


def normalize_email(email):
    email = email.strip().lower()
    local, _, domain = email.rpartition("@")
    if domain in ("gmail.com", "googlemail.com"):
        local, domain = local.split("+", 1)[0].replace(".", ""), "gmail.com"
    return f"{local}@{domain}"


def split_name(full_name):
    words = full_name.split()
    if not words:
        return "", ""
    if len(words) == 1:
        return words[0], ""
    return " ".join(words[:-1]), words[-1]


def to_e164(phone, country):
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    cc = CALLING_CODE[country]
    if digits.startswith(cc) and len(digits) == len(cc) + 10:
        national = digits[len(cc):]
    elif digits.startswith("0") and len(digits) == 11:
        national = digits[1:]
    else:
        national = digits
    return f"+{cc}{national}" if len(national) == 10 else None


def transform_user(row):
    first, last = split_name(row["full_name"])
    return {"email_normalized": normalize_email(row["email"]), "first_name": first, "last_name": last,
            "phone_e164": to_e164(row["phone"], row["country"])}
