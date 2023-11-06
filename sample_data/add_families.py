
###################################
###connect to database

load("connect.py")

#returns
# my_session - database connection
# my_cursor - cursor to my_session

path_to_log = "/home/ben/Database/sample_data/families_log.txt"
log_file = open(path_to_log, 'w', 1)


#########################

R=PolynomialRing(QQ,1,'c')
c = R.gen()
P=ProjectiveSpace(R,1,'x,y')
x,y = P.gens()
F=DynamicalSystem([x**2+c*y**2,y**2])
label = add_family_NF(F, is_poly=True, num_crit=2, num_aut=1)

my_cursor.execute("""SELECT
        id
         FROM citations
        WHERE label=%s
        """,['Poonen1998'])
cites = my_cursor.fetchone()
add_citations_family_NF(label,cites)

###########################


my_session.commit()
my_session.close()
