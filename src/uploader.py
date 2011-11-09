#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# Author: Adam Grycner (adam_gr [at] gazeta.pl)
#
# Written: 08/08/2011
#
# Released under: GNU GENERAL PUBLIC LICENSE
#
# Ver: 0.3

#from chomik import *
import view
from chomikbox import *
import getpass
import re
import traceback


class Uploader(object):
    def __init__(self, user = None, password = None):
        self.view             = view.View()
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
        #open(self.notuploaded_file,'w').close()
        if not os.path.exists(self.uploaded_file):
            open(self.uploaded_file, 'w').close()
        f = open(self.uploaded_file, 'r')
        self.uploaded = f.read().split('\n')
        self.uploaded = [i.strip() for i in self.uploaded]
        f.close()
        self.uploaded = set(self.uploaded)
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
        if filepath in self.uploaded:
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
            f = open(self.notuploaded_file,'a')
            f.write(filepath + '\t')
            f.write(filename + '\t')
            f.write(str(folder_id) + '\t')
            f.write(str(chomik_id) + '\t')
            f.write(str(token) + '\t')
            f.write(str(server) + '\t')
            f.write(str(port) + '\t')
            f.write(str(stamp))
            f.write('\r\n')
            f.close()
            if type(e.get_excpt()) == KeyboardInterrupt:
            	raise e.get_excpt()
            else:
                return
        except Exception, e:
            self.view.print_( 'Blad:' )
            self.view.print_( e )
            self.view.print_( 'Blad. Plik ',filepath, ' nie zostal wyslany\r\n' )
            f = open(self.notuploaded_file,'a')
            f.write(filepath + '\r\n')
            f.close()
            return

        if result == False:
            self.view.print_( 'Blad. Plik ',filepath, ' nie zostal wyslany\r\n' )
            f = open(self.notuploaded_file,'a')
            f.write(filepath + '\r\n')
            f.close()
        else:
            f = open(self.uploaded_file,'a')
            f.write(filepath + '\r\n')
            f.close()
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
        if not os.path.exists(self.notuploaded_file):
        	open(self.notuploaded_file,"w")
        f           = open(self.notuploaded_file,"r")
        files       = [ i.strip() for i in f.readlines()]
        f.close()
        notuploaded = []
        for f in files:
            try:
                filepath, filename, folder_id, chomik_id, token, host, port, stamp = re.findall("([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)", f)[0]
                result = self.__resume_file_aux(filepath, filename, folder_id, chomik_id, token, host, port, stamp)
                if result == False:
                    notuploaded.append( (filepath, filename, folder_id, chomik_id, token, host, port, stamp) )
            except IndexError, e:
                continue
        f = open(self.notuploaded_file, "w")
        for n in notuploaded:
             f.write( "\t".join(n) )
             f.write( "\r\n" )
        f.close()

    
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
            f = open(self.uploaded_file,'a')
            f.write(filepath + '\r\n')
            f.close()
            self.view.print_( 'Zakonczono uploadowanie\r\n' )
            return True
