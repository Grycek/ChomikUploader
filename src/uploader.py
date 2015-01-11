#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# Author: Adam (adam_gr [at] gazeta.pl)
#
# Written: 12/11/2011
#
# Released under: GNU GENERAL PUBLIC LICENSE
#
# Ver: 0.5

import view
from chomikbox_es import *
import getpass
import re
import traceback
import model
import threading
import select
##########################################

def debug_fun(tb):
    """
    tb = traceback
    """
    v  = view.View()
    st    = traceback.format_tb(tb)
    stack = []
    while tb:
        stack.append(tb.tb_frame)
        tb = tb.tb_next
    #traceback.print_exc()
    v.print_( "-"*10 )
    v.print_( ''.join(st) )
    v.print_( "Locals by frame, innermost last" )
    for frame in stack:
        v.print_()
        v.print_( "Frame %s in %s at line %s" % (frame.f_code.co_name,
                                             frame.f_code.co_filename,
                                             frame.f_lineno) )
        for key, value in frame.f_locals.items():
            try:
               v.print_( "\t%20s = " % key, value)
            except:
                v.print_( "<ERROR WHILE PRINTING VALUE>" )
    v.print_( "-"*10 )



#############################
class UploaderThread(threading.Thread):
    def __init__(self, user, password, chomikpath, dirpath, view_, model_):
        threading.Thread.__init__(self)
        self.uploader   = Uploader(user, password, view_, model_)
        self.chomikpath = chomikpath
        self.dirpath    = dirpath
        self.daemon     = True
    
    def run(self):
        self.uploader.upload_dir(self.chomikpath, self.dirpath)
        
        
#############################
class Uploader(object):
    def __init__(self, user = None, password = None, view_ = None, model_ = None, debug = False):
        if view_ == None:
            self.view    = view.View()
        else:
            self.view    = view_
        if model_ == None:
            self.model   = model.Model()
        else:
            self.model   = model_
        self.debug            = debug
        self.user             = user
        self.password         = password
        self.notuploaded_file = 'notuploaded.txt'
        self.uploaded_file    = 'uploaded.txt'
        self.chomik = Chomik(self.view, self.model)
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
            if self.debug:
                trbck = sys.exc_info()[2]
                debug_fun(trbck)
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
        lock = self.model.return_chdirlock()
        lock.acquire()
        try:
            if not self.chomik.chdirs(chomikpath):
                self.view.print_( 'Nie udalo sie zmienic katalogu w chomiku', chomikpath )
                sys.exit(1)
        finally:
            lock.release()
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
            #TODO: przetwarzany jest plik
            filepath = os.path.join(dirpath, fil)
            #if not self.model.in_uploaded(filepath):
            if not self.model.is_uploaded_or_pended_and_add(filepath):
                self.__upload_file_aux(fil, dirpath)
                self.model.remove_from_pending(filepath)
            
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
        self.view.print_( 'Uploadowanie pliku:', filepath )
        try:
            result = self.chomik.upload(filepath, os.path.basename(filepath))
        except Exception, e:
            self.view.print_( 'Blad:' )
            self.view.print_( e )
            self.view.print_( 'Blad. Plik ',filepath, ' nie zostal wyslany\r\n' )
            if self.debug:
                trbck = sys.exc_info()[2]
                debug_fun(trbck)
            return

        if result == False:
            self.view.print_( 'Blad. Plik ',filepath, ' nie zostal wyslany\r\n' )
        else:
            self.model.add_uploaded(filepath)
            self.model.remove_notuploaded(filepath)
            self.view.print_( 'Zakonczono uploadowanie\r\n' )



    
    def __upload_dir_aux(self, dirpath,dr):
        """
        Zmiana pozycji na chomiku i wyslanie katalogu
        """
        lock = self.model.return_chdirlock()
        lock.acquire()
        try:
            changed = self.chomik.chdirs(dr)
        except Exception, e:
            self.view.print_( 'Blad. Nie wyslano katalogu: ', os.path.join(dirpath, dr)  )
            self.view.print_( e )
            if self.debug:
                trbck = sys.exc_info()[2]
                debug_fun(trbck)
            time.sleep(60)
            return
        finally:
            lock.release()
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
            if not self.model.is_uploaded_or_pended_and_add(filepath):
                self.__resume_file_aux(filepath, filename, folder_id, chomik_id, token, host, port, stamp)
                self.model.remove_from_pending(filepath)
                

    
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
            if self.debug:
                trbck = sys.exc_info()[2]
                debug_fun(trbck)
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

    ####################################################################
    
    def upload_multi(self, chomikpath, dirpath, n):
        #Bug w pythonie
        #Trzeba wywolac funkcje encoding zanim uruchomi sie watek
        ########################
        try:
            text = ''
            text = text.decode('cp1250')
        except Exception:
            pass
        try:
            text = ''
            text = text.decode('utf8')
        except Exception:
            pass
        #########################
        th = []
        for i in xrange(n):
            upl = UploaderThread(self.user, self.password, chomikpath, dirpath, view_ = self.view, model_ = self.model)
            upl.start()
        while threading.active_count() > 1:
            time.sleep(1.)
                
if __name__ == '__main__':
    pass
