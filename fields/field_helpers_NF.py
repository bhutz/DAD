"""
Functionality for working with number fields

AUTHORS:

- Ben Hutz (2023-10): initial version

"""

# ****************************************************************************
#       Copyright (C) 2023 Ben Hutz <benjamin.hutz@slu.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#                  https://www.gnu.org/licenses/
# ****************************************************************************


import sys
from sage.categories.number_fields import NumberFields
from sage.libs.pari import pari
from sage.rings.cc import CC
from sage.rings.number_field.number_field import NumberField
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


def normalize_field_NF(K, emb=None, log_file=sys.stdout): #replace with lmfdb normalization
    """
    put the base field in normalized form.
    Return the normalized field and an embedding
    into it from the given field. If we are given a number field
    with no embedding, then one is created at random.
    """
    if K in NumberFields():
        if K != QQ:
            def_poly = K.defining_polynomial()
            def_poly_new, gen = pari(def_poly).polredabs(1)
            def_poly_new = def_poly_new.sage({def_poly.parent().variable_names()[0]:def_poly.parent().gen(0)})
            if def_poly_new != def_poly:
                gen = gen.lift().sage({def_poly.parent().variable_names()[0]:def_poly.parent().gen(0)})
                if emb is None:
                    if K.coerce_embedding() is None:
                        L = NumberField(def_poly_new, 'a', embedding=CC(def_poly_new.roots(ring=CC)[0][0]))
                    else:
                        L = NumberField(def_poly_new, 'a', embedding=gen(K.coerce_embedding()(K.gen())))
                else:
                    L = NumberField(def_poly_new, 'a', embedding=gen(emb(K.gen())))
                to_L = K.hom([gen], L)
                log_file.write('Normalized field:' + str(K) + ' to ' + str(L) + '\n')
                return L, to_L
            if K.variable_name() != 'a':
                L = K.change_names('a')
                log_file.write('Normalized field variable:' + str(K) + ' to ' + str(L) + '\n')
                return L, L.structure()[1]
        return K, K.automorphisms()[0].parent().identity()
    #other field
        raise NotImplementedError('Can only normalize number fields with this function')


def check_field_normalized_NF(K, log_file=sys.stdout):
    """
    check that base field is in normalize form.

    For number fields this is a monic polynomial.
    The generator is named 'a'.

    """
    if K is QQ:
        return True

    if K in NumberFields():
        if not K.is_absolute():
            return False
        def_poly = K.defining_polynomial()
        if K.variable_name() != 'a':
            return False
        def_poly_new = pari(def_poly).polredabs()
        if def_poly == pari(def_poly).polredabs():
            return True
        return False

    raise ValueError('field not a number field')


def lmfdb_field_label(K): #label finding
    #assumes the field is nomalized
    poly = K.defining_polynomial() 
    z = poly.parent().gen(0)
    C=poly.coefficients(sparse=False)
    from six.moves.urllib.request import urlopen
    import json
    url = 'https://beta.lmfdb.org/api/nf_fields/?coeffs={'
    for i in range(len(C)-1):
        url += str(C[i]) + ','
    url += str(C[-1]) + '}&_format=json&_fields=label&_delim=;'
    page = urlopen(url)
    dat = str(page.read().decode('utf-8'))
    dat = json.loads(dat)['data']
    if dat != []:
        label = dat[0]['label']
    else:
        # can't find the field
        label = 0
    return label


def add_field_NF(K, my_cursor, normalize=True, log_file=sys.stdout):
    """
    Add the field K to the number_fields table.

    label varchar(%s) PRIMARY KEY,
    degree integer,
    defn_poly_coeffs integer[],
    signature point,
    conductor integer,
    discriminant integer,
    class_number integer

    K absolute number field  deg.r.disc.num

    ##todo: deal with repeat 'x.x.x.' for higher degree number fields,
    so should search by normalized defining polynomial and then increment

    todo::this needs timeout
    """
    log_file.write('Adding field: ' + str(K) + ':')
    if not check_field_normalized_NF(K, log_file=log_file):
        if not normalize:
            raise ValueError('field not normalized')
        else:
            K, phi = normalize_field_NF(K, log_file=log_file)
    bool, K_label = lmfdb_field_label(K, my_cursor, log_file=log_file)
    if bool:
        log_file.write('already in db: ' + str(K) + '\n')
        #already in database
        return -1
    field_query = {}
    if K in NumberFields():
        if K == QQ:
            label = '1.1.1.'
        else:
            label = str(K.degree()) + '.' + str(K.signature()[0]) + '.' + str(K.discriminant().abs()) + '.'
    else:
        raise NotImplementedError("only number fields")

    #take into account distinct fields with the same initial label values
    # TODO: these end up not matching LMFDB labels
    field_query['label'] = label + '%'
    my_cursor.execute("""SELECT label FROM number_fields WHERE label LIKE %(label)s""",field_query)
    g = my_cursor.fetchall()

    #debugging sanity check
    for L in g:
        print(L)
    label = label + str(len(g)+1)
    log_file.write('label computed: ' + label + '\n')

    F = {}
    F['label'] = label
    F['degree'] = int(K.degree())
    F['defn_poly_coeffs'] = [int(t) for t in K.defining_polynomial().coefficients(sparse=False)]
    if K == QQ:
        F['signature'] = ([int(1),int(0)])
        F['conductor'] = int(1)
        F['discriminant'] = int(1)
        F['class_number'] = int(1)
        #F['embeddings'] = {'min_diff' : float(1.0),\
        #                   '0' : {'val_real' : float(0.0), 'val_imag' : float(0.0)}}
    else:
        F['signature'] = [int(t) for t in K.signature()]
        F['discriminant'] = int(K.discriminant())
        if K.is_abelian():
            F['conductor'] = int(K.conductor())
        F['class_number'] = int(K.class_number())
        #embedddings into CC sorted by value
        #embs = K.embeddings(CC)
        #half the min distance between roots
        #min_diff = min([(embs[i](K.gen())-embs[j](K.gen())).abs()\
        #                for i in range(len(embs)-1) for j in range(i+1,len(embs))])/2
        #keep track of embeddings by image of generator
        #i = 0
        #F['embeddings'] = {'min_diff':float(min_diff)}
        #for phi in K.embeddings(CC):
        #    F['embeddings'].update({str(i) : {'val_real':float(phi(K.gen()).real()),\
        #                                 'val_imag':float(phi(K.gen()).imag())}})
        #    i += 1

    # add to number fields
    if K==QQ or K.is_abelian():
        my_cursor.execute("""INSERT INTO number_fields VALUES
            (%(label)s, %(degree)s, %(defn_poly_coeffs)s,
             %(signature)s, %(conductor)s,%(class_number)s,%(discriminant)s)
            RETURNING label """,F)
    else:
        my_cursor.execute("""INSERT INTO number_fields VALUES
            (%(label)s, %(degree)s, %(defn_poly_coeffs)s,
             %(signature)s, %(class_number)s,%(discriminant)s)
            RETURNING label """,F)
    K_id = my_cursor.fetchone()[0]
    log_file.write('field inserted as: ' + str(K_id) + '\n')
    return K_id


def delete_field_NF(K, my_cursor):
    bool, K_label = lmfdb_field_label(K)
    if not bool:
        raise ValueError("field not in database")
    my_cursor.execute("""DELETE FROM number_fields WHERE label = %s""",K_label)
    val = my_cursor.rowcount
    if val==0:
        raise ValueError("Failed to find field" + str(K))
    elif val>1:
        raise ValueError("Deleted more than 1 row") #should never occur
    return val


def lmfdb_label_to_sage(label): # get field from db, return as sage object
    from six.moves.urllib.request import urlopen
    import json
    url = 'https://beta.lmfdb.org/api/nf_fields/?label=' + label + '&_format=json&_fields=coeffs&_delim=;'
    page = urlopen(url)
    dat = str(page.read().decode('utf-8'))
    dat = json.loads(dat)['data']
    if dat == []:
        return 0
    C = dat[0]['coeffs']
    if C == [0,1]:
        return QQ
    R.<z>=PolynomialRing(QQ)
    poly = 0
    for i in range(len(C)):
        poly += z**i*C[i]
    K.<a>=NumberField(poly)
    return K