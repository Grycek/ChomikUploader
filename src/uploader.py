#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# Author: Adam Grycner (adam_gr [at] gazeta.pl)
#
# Written: 23/02/2011
#
# Released under: GNU GENERAL PUBLIC LICENSE
#
# Ver: 0.2

from chomik import *
import getpass

class Uploader(object):
    def __init__(self, user = None, password = None):
        self.notuploaded_file = 'notuploaded.txt'
        self.uploaded_file    = 'uploaded.txt'
        self.chomik = Chomik()
        if user == None:
            user     = raw_input('Podaj nazwe uzytkownika:\n')
        if password == None:
            password = getpass.getpass('Podaj haslo:\r\n')
        print 'Logowanie'
        if not self.chomik.login(user, password):
            print 'Bledny login lub haslo'
            sys.exit(1)


    
    def upload_file(self, chomikpath, filepath):
        print 'Zmiana katalogow'
        self.chomik.chdirs(chomikpath)
        print 'Uploadowanie'
        try:
            result = self.chomik.upload(filepath, os.path.basename(filepath))
        except Exception, e:
            print 'Blad: ', e
            result = False
        if  result == True:
            print 'Zakonczono uploadowanie'
        else:
            print 'Blad. Plik nie zostal wyslany'
            
            
            
    def upload_dir(self, chomikpath, dirpath):
        print 'Zmiana katalogow'
        f = open(self.notuploaded_file,'w')
        f.close()
        if not os.path.exists(self.uploaded_file):
            f = open(self.uploaded_file, 'w')
            f.close()
        f = open(self.uploaded_file, 'r')
        self.uploaded = f.read().split('\n')
        self.uploaded = [i.strip() for i in self.uploaded]
        f.close()
        self.uploaded = set(self.uploaded)
        self.chomik.chdirs(chomikpath)
        self.__upload_aux(dirpath)


    
    def __upload_aux(self, dirpath):
        """
        Uploaduje pliki z danego katalogu i jego podkatalogi.
        """
        files = [ i for i in os.listdir(dirpath) if os.path.isfile( os.path.join(dirpath, i) ) ]
        files.sort()
        dirs  = [ i for i in os.listdir(dirpath) if os.path.isdir( os.path.join(dirpath, i) ) ]
        dirs.sort()
        
        for fil in files:
            self.__upload_file_aux(fil, dirpath)
        
        for dr in dirs:
            address = self.chomik.cur_adr
            self.__upload_dir_aux(dirpath,dr)
            self.chomik.cur_adr = address


    
    def __upload_file_aux(self, fil, dirpath):
        """
        Wysylanie pliku wraz z kontrola bledow.
        W odpowiednim pliku zapisujemy, czy plik zostal poprawnie wyslany
        """
        filepath = os.path.join(dirpath, fil)
        if filepath in self.uploaded:
            return
        print 'Uploadowanie pliku: {0}'.format( filepath)
        try:
            result = self.chomik.upload(filepath, os.path.basename(filepath))
        except Exception, e:
            print 'Blad:'
            print e
            result  = False
        if  result == True:
            f = open(self.uploaded_file,'a')
            f.write(filepath + '\r\n')
            f.close()
            print 'Zakonczono uploadowanie\n'
        else:
            print 'Blad. Plik {0} nie zostal wyslany\n'.format(filepath)
            f = open(self.notuploaded_file,'a')
            f.write(filepath + '\r\n')
            f.close()


    
    def __upload_dir_aux(self, dirpath,dr):
        """
        Zmiana pozycji na chomiku i wyslanie katalogu
        """
        try:
            changed = self.chomik.chdirs(dr)
        except Exception, e:
            print 'Blad. Nie wyslano katalogu: ' + os.path.join(dirpath, dr)
            time.sleep(600)
            print e
            return
        if changed != True:
            print "Nie udalo sie zmienic katalogu", dr
            return
        self.__upload_aux( os.path.join(dirpath, dr) )        
