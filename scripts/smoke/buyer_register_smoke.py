#!/usr/bin/env python3
"""Smoke test: buyer sign-up (POST /auth/buyer/register/) and buyer login by phone or email.

Only name, phone and password are required; everything else is optional. Everything
it creates is named "Smoke Reg ..." and removed at the end (and at the start).
Runs against SMOKE_BASE (default http://127.0.0.1:8000). Standard library only.
"""
import json
import os
import struct
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
import zlib

BASE = os.environ.get("SMOKE_BASE", "http://127.0.0.1:8000") + "/api/v1"
SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PASS = FAIL = 0


def call(method, path, token=None, body=None, form=None):
    headers = {}
    if form is not None:
        boundary = uuid.uuid4().hex
        data = b""
        for field, value in form:
            if isinstance(value, tuple):
                name, content, ctype = value
                data += (f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{name}"\r\nContent-Type: {ctype}\r\n\r\n').encode() + content + b"\r\n"
            else:
                data += (f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n{value}\r\n').encode()
        data += f"--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    else:
        data = json.dumps(body).encode() if body is not None else None
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            return err.code, (json.loads(raw) if raw else None)
        except ValueError:
            return err.code, None


def check(label, expected, actual):
    global PASS, FAIL
    if expected == actual:
        PASS += 1
        print(f"OK   {label} (got {actual})")
    else:
        FAIL += 1
        print(f"FAIL {label} (expected {expected}, got {actual})")


def shell(code):
    out = subprocess.run(["uv", "run", "manage.py", "shell", "-c", code], cwd=SERVER_DIR, capture_output=True, text=True).stdout
    return out.strip().splitlines()[-1] if out.strip() else ""


def cleanup():
    shell(
        "import os\n"
        "from django.conf import settings\n"
        "from apps.accounts.models import User\n"
        "rows = User.objects.filter(name__istartswith='Smoke Reg')\n"
        "for path in rows.exclude(profile_pic_path__isnull=True).values_list('profile_pic_path', flat=True):\n"
        "    try: os.remove(os.path.join(settings.MEDIA_ROOT, path))\n"
        "    except OSError: pass\n"
        "rows.delete()\n"
    )


def png():
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x00\x00\xff" * 4 for _ in range(4))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


REG = "/auth/buyer/register/"
LOGIN = "/auth/buyer/login/"
R = lambda body: call("POST", REG, body=body)  # noqa: E731
cleanup()
s, login = call("POST", "/auth/admin/login/", body={"email": "test.admin@egoola.com", "password": "Test@12345"})
T = login["access"]

print("\n=== Minimum: name, mobile, password ===")
s, r = R({"name": "Smoke Reg One", "phone": "+8801700077001", "password": "Buy@12345"})
check("register with only name + phone + password", 201, s)
check("response keys", ["access", "actor_type", "address_line", "city", "country", "description", "educations", "email", "experiences", "id", "interests", "message", "name", "phone", "profile_pic_url", "refresh", "skills", "state", "status", "thana"], sorted(r))
check("no password in the response", False, "password" in r)
check("actor_type, active, email empty", ("user", "active", None), (r["actor_type"], r["status"], r["email"]))
B1 = r["id"]
check("the tokens work: refresh", 200, call("POST", "/auth/token/refresh/", body={"refresh": r["refresh"]})[0])
check("the access token is a buyer's: seller API -> 403", 403, call("GET", "/seller/me/", r["access"])[0])
check("the access token is not an admin's: admin API -> 403", 403, call("GET", "/accounts/buyers/", r["access"])[0])
check("the buyer is their own creator", "user,Smoke Reg One,True", shell(f"from apps.accounts.models import User; u = User.objects.get(pk={B1}); print(u.creator_type, u.creator_name, u.created_by == u.pk, sep=',')").replace("True", "True"))
check("the stored password is hashed", True, shell(f"from apps.accounts.models import User; print(User.objects.get(pk={B1}).password.startswith(('pbkdf2', 'argon2', 'bcrypt', 'scrypt')))") == "True")

print("\n=== Required fields ===")
for label, body, key in [
    ("no name", {"phone": "+8801700077002", "password": "Buy@12345"}, "name"),
    ("blank name", {"name": " ", "phone": "+8801700077002", "password": "Buy@12345"}, "name"),
    ("no phone", {"name": "Smoke Reg X", "password": "Buy@12345"}, "phone"),
    ("no password", {"name": "Smoke Reg X", "phone": "+8801700077002"}, "password"),
]:
    s, r = R(body)
    check(f"{label} -> 400 on '{key}'", (400, True), (s, key in (r or {})))
check("an empty body -> all three required", ["name", "password", "phone"], sorted(R({})[1]))

print("\n=== Everything optional, together ===")
s, r = R({"name": "Smoke Reg Full", "phone": "01700077003", "password": "Buy@12345", "email": "Smoke.Reg.Full@Example.com",
          "description": "I buy bags", "address_line": "Road 1, Feni", "country": 126, "state": 13, "city": 8,
          "skills": ["design"], "experiences": [{"title": "x"}], "interests": ["bags"], "educations": ["BSc"]})
check("register with every optional field", 201, s)
check("values saved", ("Smoke.Reg.Full@Example.com", "I buy bags", 126, 13, 8, ["design"]), (r["email"], r["description"], r["country"], r["state"], r["city"], r["skills"]))
s, r = R({"name": "Smoke Reg Location", "phone": "+8801700077004", "password": "Buy@12345", "country": 126})
check("only a country is fine", 201, s)
s, r = R({"name": "Smoke Reg Blank", "phone": "+8801700077005", "password": "Buy@12345", "email": "", "description": "", "address_line": ""})
check("blank optional values are fine", (201, None), (s, r.get("email")))
s, r = R({"name": "Smoke Reg Blank 2", "phone": "+8801700077006", "password": "Buy@12345", "email": ""})
check("a second buyer with no email is fine", 201, s)
s, r = R({"name": "Smoke Reg Spaces", "phone": "+880 1700-077007", "password": "Buy@12345"})
check("spaces and hyphens in the mobile number are removed", ("+8801700077007",), (r["phone"],))

print("\n=== Validation ===")
check("duplicate phone -> 400", ("buyer with this phone already exists.",), tuple(R({"name": "Smoke Reg D", "phone": "+8801700077001", "password": "Buy@12345"})[1]["phone"]))
check("same phone written with spaces -> 400", 400, R({"name": "Smoke Reg D", "phone": "+880 1700 077001", "password": "Buy@12345"})[0])
check("duplicate email (other case) -> 400", ("buyer with this email already exists.",), tuple(R({"name": "Smoke Reg D", "phone": "+8801700077010", "password": "Buy@12345", "email": "smoke.reg.full@example.com"})[1]["email"]))
for bad in ["abc", "123", "+88017abc", "1" * 20, "++8801700"]:
    check(f"bad mobile {bad!r} -> 400", 400, R({"name": "Smoke Reg B", "phone": bad, "password": "Buy@12345"})[0])
for pw in ["short1", "12345678", "password"]:
    check(f"weak password {pw!r} -> 400", 400, R({"name": "Smoke Reg B", "phone": "+8801700077011", "password": pw})[0])
check("bad email -> 400", 400, R({"name": "Smoke Reg B", "phone": "+8801700077011", "password": "Buy@12345", "email": "nope"})[0])
check("city of another state -> 400", 400, R({"name": "Smoke Reg B", "phone": "+8801700077011", "password": "Buy@12345", "country": 126, "state": 12, "city": 8})[0])
check("unknown country -> 400", 400, R({"name": "Smoke Reg B", "phone": "+8801700077011", "password": "Buy@12345", "country": 99999})[0])
s, r = R({"name": "Smoke Reg Sneaky", "phone": "+8801700077012", "password": "Buy@12345", "status": "suspended", "wallet_balance": "999", "email_verified_at": "2026-01-01T00:00:00Z"})
check("status / wallet / verified cannot be chosen", ("active", "0.00"), (r["status"], call("GET", f"/accounts/buyers/{r['id']}/", T)[1]["wallet_balance"]))
check("a failed sign-up saves nothing", 0, int(shell("from apps.accounts.models import User; print(User.objects.filter(name='Smoke Reg B').count())") or 0))
check("GET is not allowed -> 405", 405, call("GET", REG)[0])

print("\n=== Profile picture (multipart) ===")
form = [("name", "Smoke Reg Pic"), ("phone", "+8801700077013"), ("password", "Buy@12345"), ("profile_pic", ("me.png", png(), "image/png"))]
s, r = call("POST", REG, form=form)
check("multipart with a picture", 201, s)
pic = r["profile_pic_url"]
check("the picture is stored under profile-pics/", True, bool(pic) and "profile-pics" in pic)
check("a text file as picture -> 400", 400, call("POST", REG, form=[("name", "Smoke Reg Pic2"), ("phone", "+8801700077014"), ("password", "Buy@12345"), ("profile_pic", ("n.txt", b"hi", "text/plain"))])[0])
s, r = call("POST", REG, form=[("name", "Smoke Reg Form"), ("phone", "+8801700077015"), ("password", "Buy@12345"), ("country", "126"), ("state", "13")])
check("multipart without a file", (201, 126), (s, r["country"]))

print("\n=== Login: phone or email ===")
L = lambda body: call("POST", LOGIN, body=body)  # noqa: E731
s, r = L({"phone": "+8801700077001", "password": "Buy@12345"})
check("login with phone", (200, "user", "+8801700077001", None), (s, r["actor_type"], r["phone"], r["email"]))
check("phone typed with spaces", 200, L({"phone": "+880 1700 077001", "password": "Buy@12345"})[0])
check("login with email (a buyer who gave one)", 200, L({"email": "smoke.reg.full@example.com", "password": "Buy@12345"})[0])
check("login with the phone as written at sign-up (no +880)", 200, L({"phone": "01700077003", "password": "Buy@12345"})[0])
check("wrong password -> 401", 401, L({"phone": "+8801700077001", "password": "Wrong@12345"})[0])
check("unknown phone -> 401, same message", "Invalid phone number, email or password.", L({"phone": "+8801799999999", "password": "x"})[1]["detail"])
check("a buyer with no email cannot log in by email", 401, L({"email": "nobody@example.com", "password": "Buy@12345"})[0])
check("neither phone nor email -> 400", 400, L({"password": "Buy@12345"})[0])
check("both phone and email -> 400", 400, L({"phone": "+8801700077001", "email": "a@b.com", "password": "Buy@12345"})[0])
check("the seeded test buyer still logs in by email", 200, L({"email": "test.buyer@egoola.com", "password": "Test@12345"})[0])
A = lambda m, p, b=None: call(m, p, T, b)  # noqa: E731
A("PATCH", f"/accounts/buyers/{B1}/", {"status": "suspended"})
check("a suspended buyer cannot log in -> 401", 401, L({"phone": "+8801700077001", "password": "Buy@12345"})[0])

print("\n=== Admin buyer API: email is optional there too ===")
s, r = A("POST", "/accounts/buyers/", {"name": "Smoke Reg Admin Made", "phone": "+8801700077020", "password": "Buy@12345"})
check("an admin can create a buyer without an email", (201, None), (s, r.get("email")))
check("...and a second one", 201, A("POST", "/accounts/buyers/", {"name": "Smoke Reg Admin Made 2", "phone": "+8801700077021", "password": "Buy@12345", "email": ""})[0])

print("\n=== Cleanup ===")
cleanup()
check("no Smoke Reg buyers left", 0, int(shell("from apps.accounts.models import User; print(User.objects.filter(name__istartswith='Smoke Reg').count())") or 0))
print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
