LOGIN_SALT="%2b%12%4/ZiN3Ga8VQjxm9.K2V3/."

from passlib.context import CryptContext



pwd_context = CryptContext(schemes=["bcrypt"], deprecated ="auto")

def get_password_hash(password):
    return pwd_context.hash(password)


salted_pass = LOGIN_SALT + "4dM1n_G4m0_L342e_2is73m" + LOGIN_SALT

print(get_password_hash(salted_pass))

hashed_pass = get_password_hash(salted_pass)





def verify_password(plain_password, hashed_password):

    return pwd_context.verify(salted_pass, hashed_password)


print(verify_password(plain_password= "4dM1n_G4m0_L342e_2is73m", hashed_password=hashed_pass))