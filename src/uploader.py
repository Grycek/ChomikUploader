#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# Author: Adam Grycner (adam_gr [at] gazeta.pl)
#
# Written: 08/08/2011
#
# Released under: GNU GENERAL PUBLIC LICENSE
#
# Ver: 0.3

import view
from chomikbox import *
import getpass
import re
import traceback
import model


class Uploader(object):
    def __init__(self, user = None, password = None):
        self.view             = view.View()
        self.model            = model.Model()
        self.user             = user
        self.password         = password
        self.notuploaded_file = 'notuploaded.txt'
        self.uploaded_file    = 'uploaded.txt'
        self.chomik = Chomik()
        if self.user == None:
            self.user     = raw_input('Podaj nazwe uzytkownika:\n')
        if self.password == None:
            self.password = getpass.getpass('Podaj haslo:\r\n')
        self.view.print_('Logowanie')
        if not self.chomik.login(self.user, self.password):
            self.view.print_( 'Bledny login lub haslo' )
            sys.exit(1)


    
    def upload_file(self, chomikpath, filepath):
        self.view.print_( 'Zmiana katalogow' )
        self.chomik.chdirs(chomikpath)
        self.view.print_( 'Uploadowanie' )
        try:
            result = self.chomik.upload(filepath, os.path.basename(filepath))
        except Exception, e:
            self.view.print_( 'Blad: ', e )
            self.view.print_( "-"*10 )
            traceback.print_exc(file=sys.stdout)
            self.view.print_( "-"*10 )
            result = False
        if  result == True:
            self.view.print_( 'Zakonczono uploadowanie' )
        else:
            self.view.print_( 'Blad. Plik nie zostal wyslany' )
            
            
            
    def upload_dir(self, chomikpath, dirpath):
    	self.view.print_( 'Wznawianie nieudanych transferow' )
    	self.resume()
    	self.view.print_( 'Zakonczono probe wznawiania transferow\r\n' )
        self.view.print_( 'Zmiana katalogow' )
        if not self.chomik.chdirs(chomikpath):
            self.view.print_( 'Nie udalo sie zmienic katalogu w chomiku', chomikpath )
            sys.exit(1)
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
            #address = self.chomik.cur_adr
            address = self.chomik.cur_adr()
            self.__upload_dir_aux(dirpath,dr)
            self.chomik.cur_adr(address)
            #self.chomik.cur_adr = address


    
    def __upload_file_aux(self, fil, dirpath):
        """
        Wysylanie pliku wraz z kontrola bledow.
        W odpowiednim pliku zapisujemy, czy plik zostal poprawnie wyslany
        """
        filepath = os.path.join(dirpath, fil)
        if self.model.in_uploaded(filepath):
            return
        self.view.print_( 'Uploadowanie pliku:', filepath )
        try:
            result = self.chomik.upload(filepath, os.path.basename(filepath))
        except ChomikException, e:
            self.view.print_( 'Blad:' )
            self.view.print_( e )
            #TODO: traceback
            self.view.print_( 'Blad. Plik ', filepath, ' nie zostal wyslany\r\n' )
            _, filename, folder_id, chomik_id, token, server, port, stamp = e.args()
            self.model.add_notuploaded_resume( filepath, filename, folder_id, chomik_id, token, server, port, stamp )
            if type(e.get_excpt()) == KeyboardInterrupt:
            	raise e.get_excpt()
            else:
                return
        except Exception, e:
            self.view.print_( 'Blad:' )
            self.view.print_( e )
            self.view.print_( 'Blad. Plik ',filepath, ' nie zostal wyslany\r\n' )
            self.model.add_notuploaded_normal(filepath)
            return

        if result == False:
            self.view.print_( 'Blad. Plik ',filepath, ' nie zostal wyslany\r\n' )
            self.model.add_notuploaded_normal(filepath)
        else:
            self.model.add_uploaded(filepath)
            self.model.remove_notuploaded(filepath)
            self.view.print_( 'Zakonczono uploadowanie\r\n' )



    
    def __upload_dir_aux(self, dirpath,dr):
        """
        Zmiana pozycji na chomiku i wyslanie katalogu
        """
        try:
            changed = self.chomik.chdirs(dr)
        except Exception, e:
            self.view.print_( 'Blad. Nie wyslano katalogu: ', os.path.join(dirpath, dr)  )
            self.view.print_( e )
            #TODO: traceback
            time.sleep(60)
            return
        if changed != True:
            self.view.print_( "Nie udalo sie zmienic katalogu", dr  )
            return
        self.__upload_aux( os.path.join(dirpath, dr) )        
    ####################################################################
    
    
    def resume(self):
        """
        Wznawia wysylanie plikow z listy notuploaded.txt
        """
        notuploaded = self.model.get_notuploaded_resume()
        for filepath, filename, folder_id, chomik_id, token, host, port, stamp in notuploaded:
            self.__resume_file_aux(filepath, filename, folder_id, chomik_id, token, host, port, stamp)

    
    def __resume_file_aux(self, filepath, filename, folder_id, chomik_id, token, host, port, stamp):
        """
        Wysylanie/wznawianie pojedynczego pliku
        """
        self.view.print_( 'Wznawianie pliku:', filepath )
        try:
            result = self.chomik.resume(filepath, filename, folder_id, chomik_id, token, host, port, stamp)
        except Exception, e:
            self.view.print_( 'Blad:' )
            self.view.print_( e )
            #TODO: traceback
            self.view.print_( 'Blad. Plik ',filepath,' nie zostal wyslany\r\n' )
            return False
            
        if result == False:
            self.view.print_( 'Blad. Plik ',filepath, ' nie zostal wyslany\r\n' )
            return False
        else:
            self.model.add_uploaded(filepath)
            self.model.remove_notuploaded(filepath)
            self.view.print_( 'Zakonczono uploadowanie\r\n' )
            return True
