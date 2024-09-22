
###################################
###connect to database

load("connect.py")

#returns
# my_session - database connection
# my_cursor - cursor to my_session

path_to_log = "/home/ben/dynabase/sample_data/fields_log.txt"
log_file = open(path_to_log, 'w', 1)


from fields.field_helpers_NF import add_field_NF
from fields.field_helpers_FF import add_field_FF


#########################

add_field_NF(QQ, my_cursor, log_file=log_file)

#degee 2
for d in range(2,200):
    if ZZ(d).is_squarefree():
        add_field_NF(QuadraticField(d,'a'), my_cursor, log_file=log_file)
        add_field_NF(QuadraticField(-d,'a'), my_cursor, log_file=log_file)

# degree 3
B=10
R=PolynomialRing(QQ,'z')
z=R.gen(0)
for C in xmrange([B,B,B]):
    F=R(C+[1])
    if F.is_irreducible():
        add_field_NF(NumberField(F,'a'), my_cursor, log_file=log_file)

###########################

# Finite Fields

for p in primes(2,20):
    for n in range(1,5):
        add_field_FF(GF(p**n), my_cursor)


my_session.commit()
my_session.close()
