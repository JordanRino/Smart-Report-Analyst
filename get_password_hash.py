import bcrypt

def hash_password() -> str:
    password = "admin"
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    print(hashed.decode("utf-8"))
    return hashed.decode("utf-8")

if __name__ == "__main__":
    hash_password()