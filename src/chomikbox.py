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
import progress
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

def print_coding(text):
    if sys.platform.startswith('win'):
        try:
            text = text.decode('utf-8')
        except Exception:
            try:
                text = text.decode('cp1250')
            except Exception, e:
                pass
    return text


##########################################################################################
#TODO: zmienic cos z kodowaniem
class Chomik(object):
    def __init__(self):
        #self.opener  = urllib2.build_opener()
        #current position
        self.folders_dom   = ''
        self.ses_id        = ''
        self.chomik_id     = ''
        self.folder_id     = 0
        self.cur_fold      = []
        self.user          = ''
        self.password      = ''


        
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
            #TODO: ukryc wyswietlanie bledow
            print "Blad(relogin):"
            print e
            print resp
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
        #print dom.childNodes[0].getAttribute("name")


    
    def cur_adr(self, atr = None):
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
                        #print folder_id, f
            else:
                self.mkdir(f, folder_id)
                self.get_dir_list()
                result, dom, folder_id = self.__access_node(fold + [f])
                #jezeli nie udalo sie ani utworzyc ani przejsc, to zwroc False
                if result == False:
                    return False
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
        print "Creating", print_coding(dirname), "directory"
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
            print "Creation success\n"
            return True
        else:
            print "Creation fail\n"
            return False
        


    def upload(self, filepath, filename):
    	try:
            return self.__upload(filepath, filename)
            #TODO: nie wiem jeszcze jakie wyjatki tu lapac
            #powinny tu byc lapane bledy, ktore wystapily podczas wysylania, aby
            #zapisac do pliku informacje do wznowienia wysylania
        except Exception, e:
        	raise e


    
    def __upload(self, filepath, filename):
        """
        Wysylanie pliku znajdujacego sie pod 'filepath' i nazwanie go 'filename'
        #TODO: Opis i podpis
        """
        self.relogin()
        #Pobieranie informacji o serwerze
        filename     = change_coding(filename)
        filename_len = len(filename)
        #print filename, filename_len
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (login_ip, login_port) )
        tmp = """POST /upload/token/?chomik_id={1}&folder_id={2}&sess_id={0}& HTTP/1.1\r\nConnection: close\r\nUser-Agent: ChomikBox\r\nHost: main.box.chomikuj.pl:8083\r\nContent-Length: {3}\r\n\r\n{4}""".format(self.ses_id, self.chomik_id, self.folder_id, filename_len, filename)
        #print tmp
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
        print resp
        try:
            self.token, self.stamp, self.server, self.port = re.findall( """<resp res="1" token="([^"]*)" stamp="(\d*)" server="([^:]*):(\d*)" />""", resp)[0]
        except IndexError, e:
            #FIXME
            print "Blad(pobieranie informacji z chomika):", e
            print resp
            return False
        
        #Tworzenie naglowka
        size = os.path.getsize(filepath)
        header, contenttail =  self.__create_header(self.server, self.port, self.token, self.stamp, filename, size)  
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (self.server, int(self.port) ) )
        sock.send(header)
        
        f = open(filepath,'rb')
        pb = progress.ProgressMeter(total=size, rate_refresh = 0.5)
        while True:
            chunk = f.read(1024)
            if not chunk:
                break
            sock.send(chunk)
            pb.update(len(chunk))
        
        f.close()        
        #print 'Sending tail'
        sock.send(contenttail)
        
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
                print "BLAD(nieudane wysylanie):\r\n",error_msg
            except IndexError:
                pass
            print resp
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
        
        #FIXME - czy contenttail zaczyna sie od "\r\n"
        contenttail   = "\r\n" + boundary + '--\r\n'
        
        contentlength = len(contentheader) + size + len(contenttail)

        header   = "POST /file/ HTTP/1.1\r\n"
        header  += "Content-Type: multipart/mixed; boundary={0}\r\n".format(boundary[2:])
        header  += "Connection: close\r\n"
        header  += "Host: {0}:{1}\r\n".format(server,port)
        #TODO - policz dlugosc
        header  += "Content-Length: {0}\r\n\r\n\r\n".format(contentlength) #FIXME - czy na pewno trzy entery?   
        header += contentheader
        
        return header, contenttail
    
    
#####################################################    
    def resume(self, filepath, filename, folder_id, chomik_id, token, server, port, stamp):
    	"""
    	Wznawianie uploadowania pliku filepath o nazwie filename o danych: folder_id, chomik_id, token, server, port, stamp
    	"""
        self.relogin()
        #Pobieranie informacji o serwerze
        filename     = change_coding(filename)
        filename_len = len(filename)
        #print filename, filename_len
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (server, port) )
        tmp = """GET /resume/check/?key={0}& HTTP/1.1\r\nConnection: close\r\nUser-Agent: ChomikBox\r\nHost: {1}:{2}\r\n\r\n""".format(token, server, port)
        print tmp
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
        print resp
        try:
            filesize_sent = int(re.findall( """<resp file_size="([^"]*)" skipThumbnails="[^"]*" res="1"/>""", resp)[0])
        except IndexError, e:
            print "Nie mozna bylo wznowic pobierania"
            return False
        
        #Tworzenie naglowka
        size  = os.path.getsize(filepath)
        header, contenttail =  self.__create_header(server, port, token, stamp, filename, (size - filesize_sent), resume_from = filesize_sent)  
        
        print header
        print contenttail
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (server,int(port) ) )
        sock.send(header)

        f = open(filepath,'rb')
        f.seek(filesize_sent)
        pb = progress.ProgressMeter(total=size, rate_refresh = 0.5)
        pb.update(filesize_sent)
        while True:
            chunk = f.read(1024)
            if not chunk:
                break
            sock.send(chunk)
            pb.update(len(chunk))
            
        f.close()        
        #print 'Sending tail'
        sock.send(contenttail)
        
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
                print "BLAD(nieudane wysylanie):\r\n",error_msg
            except IndexError:
                pass
            print resp
            return False
        
        
#####################################################
        
        
if __name__ == "__main__":
    c = Chomik()
    c.login("tmp_chomik1", "")
    #c.upload("/home/adam/VBox/Program w wersji Portable ChomikBox 2011.zip", "tmp")
    c.resume("/home/adam/VBox/Program w wersji Portable ChomikBox 2011.zip", "tmp", c.folder_id, c.chomik_id, "df812da8d5b2fe1312e80a6af969f924", "s2148.chomikuj.pl", 8084, 1314203696)
