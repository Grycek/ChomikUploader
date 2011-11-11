#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# Author: Adam Grycner (adam_gr [at] gazeta.pl)
#
# Written: 08/08/2011
#
# Released under: GNU GENERAL PUBLIC LICENSE
#
# Ver: 0.3

import socket
import urllib2
import hashlib
import re
import sys
import time
import os
#import progress
import view
import traceback
from xml.dom.minidom import parseString

glob_timeout = 240
#KONFIGURACJA
#login_ip   = "208.43.223.12"
login_ip   = "main.box.chomikuj.pl"
login_port = 8083


def change_coding(text):
    try:
        if sys.platform.startswith('win'):
          text = text.decode('cp1250').encode('utf-8')
    except Exception, e:
        print e
    return text

def to_unicode(text):
    try:
        if sys.platform.startswith('win'):
            text = text.decode('cp1250')
        else:
            text = text.decode('utf8')
    except Exception, e:
        print e
    return text


#####################################################################################################
class ChomikException(Exception):
    def __init__(self, filepath, filename, folder_id, chomik_id, token, server, port, stamp, excpt = None):
        Exception.__init__(self)
        self.filepath  = filepath
        self.filename  = filename
        self.folder_id = folder_id
        self.chomik_id = chomik_id
        self.token     = token
        self.server    = server
        self.port      = port
        self.stamp     = stamp
        self.excpt     = excpt
    
    def __str__(self):
        return str(self.excpt)
    
    def get_excpt(self):
    	return self.excpt
    
    def args(self):
        return (self.filepath, self.filename, self.folder_id, self.chomik_id, self.token, self.server, self.port, self.stamp)

#####################################################################################################
#TODO: zmienic cos z kodowaniem
class Chomik(object):
    def __init__(self):
        self.folders_dom   = ''
        self.ses_id        = ''
        self.chomik_id     = ''
        self.folder_id     = 0
        self.cur_fold      = []
        self.user          = ''
        self.password      = ''
        self.view          = view.View()


        
    def login(self, user, password):
        """
        Logowanie sie do chomika
        Zwraca True przy pomyslnym zalogowani, a False wpp
        """
        self.user          = user
        self.password      = password
        if self.relogin() == True:
            self.get_dir_list()
            return True
        else:
            return False


    
    def relogin(self):
        password = hashlib.md5(self.password).hexdigest()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (login_ip, login_port) )
        sock.send("""GET /auth/?name=""" + self.user + """&pass=""" + password + """&v=3 HTTP/1.1\r\nConnection: close\r\nUser-Agent: ChomikBox\r\nHost: main.box.chomikuj.pl:8083\r\n\r\n""" )
        #sock.send( """GET /auth/?name={0}&pass={1}&v=3& HTTP/1.1\r\nConnection: close\r\nUser-Agent: ChomikBox\r\nHost: main.box.chomikuj.pl:8083\r\n\r\n""".format(self.user,password) )
        resp = sock.recv(1024)
        sock.close()
        try:
            ses_id, chomik_id = re.findall('sess_id="([^"]*)" chomik_id="(\d*)"' ,resp)[0]
            self.ses_id    = ses_id
            self.chomik_id = chomik_id
        except IndexError, e:
            self.view.print_( "Blad(relogin):" )
            self.view.print_( e )
            self.view.print_( resp )
            #TODO: tracebar
            return False
        else:
            return True
        
        

    def get_dir_list(self):
        """
        Pobiera liste folderow chomika.
        #TODO - dopisac test
        """
        self.relogin()
        #Laczenie sie
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (login_ip, login_port) )
        #Prosba o liste folderow
        sock.send( """GET /folders/?sess_id={0}&chomik_id={1}& HTTP/1.1\r\nConnection: close\r\nUser-Agent: ChomikBox\r\nHost: main.box.chomikuj.pl:8083\r\n\r\n""".format(self.ses_id, self.chomik_id) )
        #Odbieranie odpowiedzi
        resp = ""
        while True:
            tmp = sock.recv(640) 
            if tmp ==  '' or '</chomik>' in resp:
                break
            resp   += tmp
        resp += tmp
        #Parsowanie odpowiedzi
        _, sep ,resp = resp.partition('<?xml version="1.0"?>')
        if sep == "":
            raise Exception("Blad pobierania listy folderow")
        dom = parseString(sep + resp).childNodes[0]
        self.folders_dom = dom
        #self.view.print_( dom.childNodes[0].getAttribute("name") )


    
    def cur_adr(self, atr = None):
        """
        Zwracanie lub ustawianie obecnego polozenia w katalogach
        """
        if atr == None:
            return self.cur_fold, self.folder_id
        else:
            self.cur_fold, self.folder_id = atr
    

    
    def chdirs(self, directories):
        """
        Zmien katalog na chomiku. Jezeli jakis katalog nie istnieje, to zostaje stworzony
        np. (chdirs(/katalog1/katalog2/katalog3) )
        """
        #zamiana directories na liste kolejnych wezlow
        folders = self.cur_fold + [i.replace("/","") for i in directories.split('/') if i != '']
        fold    = []
        for f in folders:
            if f == "..":
                if f != []:
                    del(fold[-1])
            else:
                fold.append(f)
        folders   = fold
        fold      = []
        folder_id = 0
        #pobieranie listy folderow
        result, dom, folder_id = self.__access_node(folders)
        if result == True:
            self.cur_fold  = folders
            self.folder_id = folder_id
        else:
            result, dom, folder_id = self.__create_nodes(folders)
            if result == False:
                return False
        self.cur_fold  = folders
        self.folder_id = folder_id
        return True
    

    
    def __access_node(self, folders_list):
        """
        Odwiedza kolejne wezly drzewa xmlowego wypisane na liscie folder_list.
        Jezeli jakiego wezla nie ma, to zwracany jest (False,None,None).
        JEzeli wszystkie wezly istnieja, to zwracane jest 
        (True, poddrzewo ostatniego wezla na liscie, folder_id ostatniego wezla na liscie)
        """
        dom       = self.folders_dom
        fold      = []
        folder_id = 0
        for f in folders_list:
            if to_unicode(f) in [i.getAttribute("name") for i in dom.childNodes]:
                for i in dom.childNodes:
                    if to_unicode(f) == i.getAttribute("name"):
                        dom       = i
                        folder_id = int(i.getAttribute("id"))
            else:
                return (False, None, None)
        return (True,dom, folder_id)


    
    def __create_nodes(self, folder_list):
        folder_id = 0
        fold      = []
        self.get_dir_list()
        dom       = self.folders_dom
        for f in folder_list:
            if to_unicode(f) in [i.getAttribute("name") for i in dom.childNodes]:
                for i in dom.childNodes:
                    if to_unicode(f) == i.getAttribute("name"):
                        dom            = i
                        #
                        folder_id = int(i.getAttribute("id"))
                        fold.append(f)
                        #self.view.print_( folder_id, f )
            else:
                self.mkdir(f, folder_id)
                self.get_dir_list()
                result, dom, folder_id = self.__access_node(fold + [f])
                #jezeli nie udalo sie ani utworzyc ani przejsc, to zwroc False
                if result == False:
                    return (False, None, None)
                else:
                    fold.append(f)
        return (True,dom, folder_id)
    


    def mkdir(self, dirname, folder_id = None):
        """
        Tworzenie katalogu w katalogu o id = folder_id
        """
        self.relogin()
        if folder_id == None:
            folder_id = self.folder_id
        dirname   = change_coding(dirname)
        self.view.print_( "Creating", dirname, "directory" )
        dirname   = urllib2.quote(dirname)
        #Laczenie sie
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (login_ip, login_port) )
        #Prosba o liste folderow
        sock.send( """GET /folderoper/?sess_id={0}&chomik_id={1}&oper=0&folder1={2}&folder2=-1&name={3}& HTTP/1.1\r\nConnection: close\r\nUser-Agent: ChomikBox\r\nHost: main.box.chomikuj.pl:8083\r\n\r\n""".format(self.ses_id, self.chomik_id, folder_id ,dirname) )
        #Odbieranie odpowiedzi
        resp = ""
        while True:
            tmp = sock.recv(640) 
            if tmp ==  '':
                break
            resp   += tmp
        resp += tmp
        #TODO - nie wiem kiedy chomik uznaje, ze utworzenie katalogu sie nie udalo
        #wiec na razie uznaje za blad,jesli w odpowiedzi nie otrzymamy "<resp res="1" />"
        if '<resp res="1" />' in resp:
            self.view.print_( "Creation success\r\n" )
            return True
        else:
            self.view.print_( "Creation fail\r\n" )
            return False
        

    def upload(self, filepath, filename):
        try:
            return self.__upload(filepath, filename)
            #TODO: nie wiem jeszcze jakie wyjatki tu lapac
            #powinny tu byc lapane bledy, ktore wystapily podczas wysylania, aby
            #zapisac do pliku informacje do wznowienia wysylania
            #Prawdopodobnie powinienem tutaj lapac tylko socket.error
        except (Exception, KeyboardInterrupt), e:
            try:
                excpt = ChomikException(filepath, filename, self.folder_id, self.chomik_id, self.token, self.server, self.port, self.stamp, excpt = e)
            except Exception:
                raise e
            else:
                raise excpt


    
    def __upload(self, filepath, filename):
        """
        Wysylanie pliku znajdujacego sie pod 'filepath' i nazwanie go 'filename'
        #TODO: Opis i podpis
        """
        self.relogin()
        #Pobieranie informacji o serwerze
        filename     = change_coding(filename)
        filename_len = len(filename)
        #self.view.print_( filename, filename_len )
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (login_ip, login_port) )
        tmp = """POST /upload/token/?chomik_id={1}&folder_id={2}&sess_id={0}& HTTP/1.1\r\nConnection: close\r\nUser-Agent: ChomikBox\r\nHost: main.box.chomikuj.pl:8083\r\nContent-Length: {3}\r\n\r\n{4}""".format(self.ses_id, self.chomik_id, self.folder_id, filename_len, filename)
        #self.view.print_( tmp )
        sock.send( tmp )
        #Odbieranie odpowiedzi
        resp = ""
        while True:
            tmp = sock.recv(640) 
            if tmp ==  '':
                break
            resp   += tmp
        resp += tmp
        sock.close()
        #self.view.print_( resp )
        try:
            self.token, self.stamp, self.server, self.port = re.findall( """<resp res="1" token="([^"]*)" stamp="(\d*)" server="([^:]*):(\d*)" />""", resp)[0]
        except IndexError, e:
            self.view.print_( "Blad(pobieranie informacji z chomika):", e )
            self.view.print_( resp )
            return False
        
        #Tworzenie naglowka
        size = os.path.getsize(filepath)
        header, contenttail =  self.__create_header(self.server, self.port, self.token, self.stamp, filename, size)  
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (self.server, int(self.port) ) )
        sock.send(header)
        
        f = open(filepath,'rb')
        #pb = progress.ProgressMeter(total=size, rate_refresh = 0.5)
        pb = view.ProgressBar(total=size, rate_refresh = 0.5, count = 0, name = filepath)
        self.view.add_progress_bar(pb)
        try:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                sock.send(chunk)
                pb.update(len(chunk))
                #TODO: to trzeba bedzie poprawic - osobny watek na widok?update_progress_bars
                self.view.update_progress_bars()
            f.close()        
            #self.view.print_( 'Sending tail' )
            sock.send(contenttail)
        finally:
            self.view.delete_progress_bar(pb)
        
        resp = ""
        while True:
            tmp = sock.recv(640)
            resp   += tmp
            if tmp ==  '' or "/>" in resp:
                break
        if '<resp res="1" fileid=' in resp:
            return True
        else:
            try:
                error_msg = re.findall('errorMessage="([^"]*)"',resp)[0]
                self.view.print_( "BLAD(nieudane wysylanie):\r\n",error_msg )
            except IndexError:
                pass
            self.view.print_( resp )
            return False
    
    
    
    def __create_header(self, server, port, token, stamp, filename, size, resume_from = 0):
        #FIXME: - cos krotki ten boundary
        boundary = "--!CHB" + str(int(time.time()))
        
        contentheader  = boundary + '\r\nname="chomik_id"\r\nContent-Type: text/plain\r\n\r\n{0}\r\n'.format(self.chomik_id)
        contentheader += boundary + '\r\nname="folder_id"\r\nContent-Type: text/plain\r\n\r\n{0}\r\n'.format(self.folder_id)
        contentheader += boundary + '\r\nname="key"\r\nContent-Type: text/plain\r\n\r\n{0}\r\n'.format(token)
        contentheader += boundary + '\r\nname="time"\r\nContent-Type: text/plain\r\n\r\n{0}\r\n'.format(stamp)
        contentheader += boundary + '\r\nname="resume_from"\r\nContent-Type: text/plain\r\n\r\n{0}\r\n'.format(resume_from)
        contentheader += boundary + '\r\nname="file"; filename="{0}"\r\n\r\n'.format(filename)
        
        contenttail   = "\r\n" + boundary + '--\r\n'
        
        contentlength = len(contentheader) + size + len(contenttail)

        header   = "POST /file/ HTTP/1.1\r\n"
        header  += "Content-Type: multipart/mixed; boundary={0}\r\n".format(boundary[2:])
        header  += "Connection: close\r\n"
        header  += "Host: {0}:{1}\r\n".format(server,port)
        header  += "Content-Length: {0}\r\n\r\n\r\n".format(contentlength)
        pass
        header += contentheader
        
        return header, contenttail
    
    
#####################################################    
    def resume(self, filepath, filename, folder_id, chomik_id, token, server, port, stamp):
        """
        Wznawianie uploadowania pliku filepath o nazwie filename o danych: folder_id, chomik_id, token, server, port, stamp
        """
        self.relogin()
        self.chomik_id = chomik_id
        self.folder_id = folder_id
        #Pobieranie informacji o serwerze
        filename     = change_coding(filename)
        filename_len = len(filename)
        #self.view.print_( filename, filename_len )
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (server, int(port) ) )
        tmp = """GET /resume/check/?key={0}& HTTP/1.1\r\nConnection: close\r\nUser-Agent: ChomikBox\r\nHost: {1}:{2}\r\n\r\n""".format(token, server, port)
        #self.view.print_( tmp )
        sock.send( tmp )
        #Odbieranie odpowiedzi
        resp = ""
        while True:
            tmp = sock.recv(640) 
            if tmp ==  '':
                break
            resp   += tmp
        resp += tmp
        sock.close()
        #self.view.print_( resp )
        try:
            filesize_sent = int(re.findall( """<resp file_size="([^"]*)" skipThumbnails="[^"]*" res="1"/>""", resp)[0])
        except IndexError, e:
            self.view.print_( "Nie mozna bylo wznowic pobierania" )
            return False
        
        #Tworzenie naglowka
        size  = os.path.getsize(filepath)
        header, contenttail =  self.__create_header(server, port, token, stamp, filename, (size - filesize_sent), resume_from = filesize_sent)  
        
        #self.view.print_( header )
        #self.view.print_( contenttail )
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (server,int(port) ) )
        sock.send(header)
        
        f = open(filepath,'rb')
        f.seek(filesize_sent)
        pb = view.ProgressBar(total=size, rate_refresh = 0.5, count = filesize_sent, name = filepath)
        #pb = progress.ProgressMeter(total=size, rate_refresh = 0.5)
        #pb.update(filesize_sent)
        self.view.add_progress_bar(pb)
        try:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                sock.send(chunk)
                pb.update(len(chunk))
                self.view.update_progress_bars()
            f.close()        
            #self.view.print_( 'Sending tail' )
            sock.send(contenttail)
        finally:
            self.view.delete_progress_bar(pb)
        
        resp = ""
        while True:
            tmp = sock.recv(640)
            resp   += tmp
            if tmp ==  '' or "/>" in resp:
                break
        if '<resp res="1" fileid=' in resp:
            return True
        else:
            try:
                error_msg = re.findall('errorMessage="([^"]*)"',resp)[0]
                self.view.print_( "BLAD(nieudane wysylanie):\r\n",error_msg )
            except IndexError:
                pass
            self.view.print_( resp )
            return False
        
        
#####################################################
        
        
if __name__ == "__main__":
    c = Chomik()
    c.login("", "")
    #c.upload("/home/adam/VBox/Program w wersji Portable ChomikBox 2011.zip", "tmp")
    c.resume("/home/adam/VBox/Program w wersji Portable ChomikBox 2011.zip", "tmp", c.folder_id, c.chomik_id, "df812da8d5b2fe1312e80a6af969f924", "s2148.chomikuj.pl", 8084, 1314203696)
