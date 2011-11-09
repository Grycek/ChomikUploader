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
from chomikbox import *
import getpass
import re

def print_coding(text):
    try:
        if sys.platform.startswith('win'):
          text = text.decode('cp1250')
    except Exception:
        pass
    return text

class Uploader(object):
    def __init__(self, user = None, password = None):
        self.user             = user
        self.password         = password
        self.notuploaded_file = 'notuploaded.txt'
        self.uploaded_file    = 'uploaded.txt'
        self.chomik = Chomik()
        if self.user == None:
            self.user     = raw_input('Podaj nazwe uzytkownika:\n')
        if self.password == None:
            self.password = getpass.getpass('Podaj haslo:\r\n')
        print 'Logowanie'
        if not self.chomik.login(self.user, self.password):
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
    	print 'Wznawianie nieudanych transferow'
    	self.resume()
    	print 'Zakonczono probe wznawiania transferow\r\n'
        print 'Zmiana katalogow'
        #open(self.notuploaded_file,'w').close()
        if not os.path.exists(self.uploaded_file):
            open(self.uploaded_file, 'w').close()
        f = open(self.uploaded_file, 'r')
        self.uploaded = f.read().split('\n')
        self.uploaded = [i.strip() for i in self.uploaded]
        f.close()
        self.uploaded = set(self.uploaded)
        if not self.chomik.chdirs(chomikpath):
            print 'Nie udalo sie zmienic katalogu w chomiku', chomikpath
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
        print 'Uploadowanie pliku:', print_coding(filepath)
        try:
            result = self.chomik.upload(filepath, os.path.basename(filepath))
        except ChomikException, e:
            print 'Blad:'
            print e
            print 'Blad. Plik ',print_coding(filepath),' nie zostal wyslany\n'
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
            print 'Blad:'
            print e
            print 'Blad. Plik ',print_coding(filepath),' nie zostal wyslany\n'
            f = open(self.notuploaded_file,'a')
            f.write(filepath + '\r\n')
            f.close()
            return
            pass

        if result == False:
            print 'Blad. Plik ',print_coding(filepath),' nie zostal wyslany\n'
            f = open(self.notuploaded_file,'a')
            f.write(filepath + '\r\n')
            f.close()
        else:
            f = open(self.uploaded_file,'a')
            f.write(filepath + '\r\n')
            f.close()
            print 'Zakonczono uploadowanie\n'



    
    def __upload_dir_aux(self, dirpath,dr):
        """
        Zmiana pozycji na chomiku i wyslanie katalogu
        """
        try:
            changed = self.chomik.chdirs(dr)
        except Exception, e:
            print 'Blad. Nie wyslano katalogu: ', print_coding( os.path.join(dirpath, dr) )
            print e
            time.sleep(60)
            return
        if changed != True:
            print "Nie udalo sie zmienic katalogu", print_coding( dr )
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
        print 'Wznawianie pliku:', print_coding(filepath)
        try:
            result = self.chomik.resume(filepath, filename, folder_id, chomik_id, token, host, port, stamp)
        except Exception, e:
            print 'Blad:'
            print e
            print 'Blad. Plik ',print_coding(filepath),' nie zostal wyslany\n'
            return False
            
        if result == False:
            print 'Blad. Plik ',print_coding(filepath),' nie zostal wyslany\n'
            return False
        else:
            f = open(self.uploaded_file,'a')
            f.write(filepath + '\r\n')
            f.close()
            print 'Zakonczono uploadowanie\n'
            return True
