#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# Author: Adam Grycner (adam_gr [at] gazeta.pl)
#
# Written: 12/11/2011
#
# Released under: GNU GENERAL PUBLIC LICENSE
#
# Ver: 0.4

import uploader   
import sys
import getopt

######################################################################################    
def usage():
    print 'Użycie programu:'
    print 'python', sys.argv[0], '[-h|--help]  [-l|--login nazwa_chomika] [-p|--password haslo chomika] [-r|--recursive katalog_w_chomiku katalog_na_dysku] [-u|--upload katalog_w_chomiku sciezka_do_pliku]\n'
    print '-h,--help\t\t pokazuje pomoc programu'
    print '-r,--recursive\t\t wysyla zawartosc katalogu (oraz wszystkich podkatalogow) na chomika do wskazanego katalogu. Na chomiku tworzona jest cala struktura podkatalogow. Przykład:',
    print 'python', sys.argv[0], '-r "/katalog1/katalog2/katalog3" "/home/nick/Dokumenty"'
    print '-u,--upload\t\t wysyla plik na chomika do wskazanego katalogu.Przykład:',
    print 'python', sys.argv[0], '-u "/katalog1/katalog2/katalog3" "/home/nick/Dokumenty/dokument1.txt"'
    print '-l,--login\t\t login/nazwa_uzytkownika do chomika'
    print '-p,--password\t\t haslo do chomika. Przyklad:',
    print 'python', sys.argv[0], '-l nazwa_chomika -p haslo -u "/katalog1/katalog2/katalog3" "/home/nick/Dokumenty/dokument1.txt"'
    print '-d, --debug\t\t wyswietala wiecej informacji przy okazji bledu programu'
    print '-t, --threads\t\t liczba watkow (ile plikow jest jednoczescnie wysylanych). Przyklad: ',
    print 'python', sys.argv[0], '-t 5 -r "/katalog1/katalog2/katalog3" "/home/nick/Dokumenty"'
    
#if __name__ == '__main__':
if True:
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hrul:p:dt:', ['help','recursive', 'upload', 'login', 'password','debug', 'threads'])
    except Exception, e:
        print 'Przekazano niepoprawny parametr'
        print e
        usage()
        sys.exit(2)
    
    if opts == []:
        usage()
    
    login    = None
    password = None
    threads  = 1
    debug    = False
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit()
        elif opt in ('-l', '--login'):
            login = arg
        elif opt in ('-p', '--password'):
            password = arg
        elif opt in ('-t', '--threads'):
            threads = int(arg)
        elif opt in ('-d', '--debug'):
            debug = True
    try:
        for opt, arg in opts:
            if opt in ('-r', '--recursive'):
                chomik_path, dirpath = args
                u = uploader.Uploader(login, password, debug = debug)
                if threads > 1:
                    u.upload_multi(chomik_path, dirpath, threads)
                else:
                    u.upload_dir(chomik_path, dirpath)
            elif opt in ('-u', '--upload'):
                chomik_path, filepath = args
                u = uploader.Uploader(login, password, debug = debug)
                u.upload_file(chomik_path, filepath)
    except ValueError, e:
        print e
        print "Blad: Musisz podac zarowno sciezke na chomiku, jak i na dysku. Ktoras z tych sciezek opusciles"
