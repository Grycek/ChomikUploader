#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# Author: Adam (adam_gr [at] gazeta.pl)
#
# Written: 05/08/2012
#
# Released under: GNU GENERAL PUBLIC LICENSE
#
# Ver: 0.5

import socket
import urllib2
import hashlib
import re
import sys
import time
import os
import zlib
#import progress
import view
import traceback
import model
##################
from soap import SOAP
                                 
#############################
glob_timeout = 240
#KONFIGURACJA
#login_ip   = "208.43.223.12"
#login_ip   = "main.box.chomikuj.pl"
login_ip   = "box.chomikuj.pl"
#login_port = 8083
login_port = 80


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
    def __init__(self, view_ = None, model_ = None):
        if view_ == None:
            self.view    = view.View()
        else:
            self.view    = view_
        if model_ == None:
            self.model   = model.Model()
        else:
            self.model   = model_
        self.soap          = SOAP()
        ########
        #root folder
        self.folders_dom   = {}
        self.ses_id        = ''
        self.chomik_id     = '0'
        self.folder_id     = '0'
        self.cur_fold      = []
        self.user          = ''
        self.password      = ''


    def send(self, content):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (login_ip, login_port) )
        sock.send(content)
        resp = ""
        while True:
            tmp = sock.recv(640) 
            if tmp ==  '':
                break
            resp   += tmp
        sock.close()
        return resp.partition("\r\n\r\n")[2]
                
        
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
        xml_dict = [('ROOT',[('name' , self.user), ('passHash', password), ('ver' , '4'), ('client',[('name','chomikbox'),('version','2.0.4.3') ]) ])]
        xml_content = self.soap.soap_dict_to_xml(xml_dict, "Auth").strip()
        xml_len = len(xml_content)
        header  = """POST /services/ChomikBoxService.svc HTTP/1.1\r\n"""
        header += """SOAPAction: http://chomikuj.pl/IChomikBoxService/Auth\r\n"""
        header += """Content-Type: text/xml;charset=utf-8\r\n"""
        header += """Content-Length: %d\r\n""" % xml_len
        header += """Connection: Keep-Alive\r\n"""
        header += """Accept-Language: pl-PL,en,*\r\n"""
        header += """User-Agent: Mozilla/5.0\r\n"""
        header += """Host: box.chomikuj.pl\r\n\r\n"""
        header += xml_content
        resp = self.send(header)
        resp_dict =  self.soap.soap_xml_to_dict(resp)
        status = resp_dict['s:Envelope']['s:Body']['AuthResponse']['AuthResult']['a:status']
        if status != 'Ok':
            self.view.print_( "Blad(relogin):" )
            self.view.print_( status )
            return False
        try:
            chomik_id = resp_dict['s:Envelope']['s:Body']['AuthResponse']['AuthResult']['a:hamsterId']
            ses_id    = resp_dict['s:Envelope']['s:Body']['AuthResponse']['AuthResult']['a:token'] 
            self.ses_id    = ses_id
            self.chomik_id = chomik_id
        except IndexError, e:
            self.view.print_( "Blad(relogin):" )
            self.view.print_( e )
            #self.view.print_( resp )
            return False
        else:
            return True
        
        

    def get_dir_list(self):
        """
        Pobiera liste folderow chomika.
        """
        self.relogin()
        xml_dict = [('ROOT',[('token' , self.ses_id), ('hamsterId', self.chomik_id), ('folderId' , '0'), ('depth' , 0) ])]
        xml_content = self.soap.soap_dict_to_xml(xml_dict, "Folders").strip()
        xml_len = len(xml_content)
        header  = """POST /services/ChomikBoxService.svc HTTP/1.1\r\n"""
        header += """SOAPAction: http://chomikuj.pl/IChomikBoxService/Folders\r\n"""
        header += """Content-Type: text/xml;charset=utf-8\r\n"""
        header += """Content-Length: %d\r\n""" % xml_len
        header += """Connection: Keep-Alive\r\n"""
        header += """Accept-Language: pl-PL,en,*\r\n"""
        header += """User-Agent: Mozilla/5.0\r\n"""
        header += """Host: box.chomikuj.pl\r\n\r\n"""
        header += xml_content
        resp = self.send(header)
        resp_dict =  self.soap.soap_xml_to_dict(resp)
        status = resp_dict['s:Envelope']['s:Body']['FoldersResponse']['FoldersResult']['a:status']
        if status != 'Ok':
            self.view.print_( "Blad(pobieranie listy folderow):" )
            self.view.print_( status )        
            return False
        self.folders_dom = resp_dict['s:Envelope']['s:Body']['FoldersResponse']['FoldersResult']['a:folder']
        return True


    
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
                #we are cutting dirname to the length of 100
                f = f[:100]
                fold.append(f)
        folders   = fold
        fold      = []
        folder_id = '0'
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
        folder_id = '0'
        for f in folders_list:
            list_of_subfolders = dom.get('folders', {}).get('FolderInfo', {})
            if type(list_of_subfolders) == dict:
                list_of_subfolders = [list_of_subfolders]
            if to_unicode(f) in [i.get("name",None) for i in list_of_subfolders ]:
                for i in list_of_subfolders:
                    if to_unicode(f) == i.get("name",None):
                        dom       = i
                        folder_id = i["id"]
            else:
                return (False, None, None)
        return (True,dom, folder_id)


    
    def __create_nodes(self, folder_list):
        folder_id = '0'
        fold      = []
        self.get_dir_list()
        dom       = self.folders_dom
        for f in folder_list:
            list_of_subfolders = dom.get('folders', {}).get('FolderInfo', {})
            if type(list_of_subfolders) == dict:
                list_of_subfolders = [list_of_subfolders]
            if to_unicode(f) in [i.get("name",None) for i in list_of_subfolders ]:
                for i in list_of_subfolders:
                    if to_unicode(f) == i.get("name",None):
                        dom       = i
                        folder_id = i["id"]
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
        if len(dirname) > 100:
            self.view.print_( "Dirname too long" )
            self.view.print_( "Dirname shortened\r\n" )
            dirname = dirname[:100]
        self.relogin()
        if folder_id == None:
            folder_id = self.folder_id
        dirname   = change_coding(dirname)
        self.view.print_( "Creating", dirname, "directory" )
        #dirname   = urllib2.quote(dirname)
        ########################
        xml_dict = [('ROOT',[('token' , self.ses_id), ('newFolderId' , folder_id), ('name', dirname) ])]
        xml_content = self.soap.soap_dict_to_xml(xml_dict, "AddFolder").strip()
        xml_len = len(xml_content)
        header  = """POST /services/ChomikBoxService.svc HTTP/1.1\r\n"""
        header += """SOAPAction: http://chomikuj.pl/IChomikBoxService/AddFolder\r\n"""
        header += """Content-Type: text/xml;charset=utf-8\r\n"""
        header += """Content-Length: %d\r\n""" % xml_len
        header += """Connection: Keep-Alive\r\n"""
        header += """Accept-Language: pl-PL,en,*\r\n"""
        header += """User-Agent: Mozilla/5.0\r\n"""
        header += """Host: box.chomikuj.pl\r\n\r\n"""
        header += xml_content
        resp = self.send(header)
        resp_dict =  self.soap.soap_xml_to_dict(resp)
        status = resp_dict['s:Envelope']['s:Body']['AddFolderResponse']['AddFolderResult']['status']['#text']
        if status == 'Ok':
            self.view.print_( "Creation success\r\n" )
            return True
        else:
            error_msg = resp_dict['s:Envelope']['s:Body']['AddFolderResponse']['AddFolderResult']['errorMessage']['#text']
            if error_msg == 'NameExistsAtDestination':
                return True
            else:
                self.view.print_( "Creation fail" )
                self.view.print_( error_msg )
                return False

    def rmdir(self):
        """
        Usuwanie obecnego katalogu
        """
        self.relogin()
        self.view.print_( "Removing current directory" )
        ########################
        xml_dict = [('ROOT',[('token' , self.ses_id), ('folderId' , self.folder_id), ('force', '1') ])]
        xml_content = self.soap.soap_dict_to_xml(xml_dict, "RemoveFolder").strip()
        xml_len = len(xml_content)
        header  = """POST /services/ChomikBoxService.svc HTTP/1.1\r\n"""
        header += """SOAPAction: http://chomikuj.pl/IChomikBoxService/RemoveFolder\r\n"""
        header += """Content-Type: text/xml;charset=utf-8\r\n"""
        header += """Content-Length: %d\r\n""" % xml_len
        header += """Connection: Keep-Alive\r\n"""
        header += """Accept-Language: pl-PL,en,*\r\n"""
        header += """User-Agent: Mozilla/5.0\r\n"""
        header += """Host: box.chomikuj.pl\r\n\r\n"""
        header += xml_content
        resp = self.send(header)
        resp_dict =  self.soap.soap_xml_to_dict(resp)
        status = resp_dict['s:Envelope']['s:Body']['RemoveFolderResponse']['RemoveFolderResult']['a:status']
        if status == 'Ok':
            self.view.print_( "Removal success\r\n" )
            return True
        else:
            self.view.print_( "Removal fail" )
            self.view.print_( status )
            return False


        
    ###########################################################################
    def upload(self, filepath, filename):
        self.relogin()
        filename_tmp               = change_coding(filename)
        self.model.add_notuploaded_normal(filepath)
        token, stamp, server, port = self.__upload_get_tokens(filepath, filename_tmp)
        #saving information for resuming
        self.model.add_notuploaded_resume(filepath, filename, self.folder_id, self.chomik_id, token, server, port, stamp)
        if token == None:
            return False
        else:
            result = self.__upload(filepath, filename, token, stamp, server, port)
            if result == True:
                self.model.remove_notuploaded(filepath)
            return result


    def __upload_get_tokens(self, filepath, filename):
        """
        Pobiera informacje z serwera o tym gdzie i z jakimi parametrami wyslac plik
        """
        #Pobieranie informacji o serwerze
        filename_len = len(filename)
        xml_dict = [('ROOT',[('token' , self.ses_id), ('folderId' , self.folder_id), ('fileName', filename) ])]
        xml_content = self.soap.soap_dict_to_xml(xml_dict, "UploadToken").strip()
        xml_len = len(xml_content)
        header  = """POST /services/ChomikBoxService.svc HTTP/1.1\r\n"""
        header += """SOAPAction: http://chomikuj.pl/IChomikBoxService/UploadToken\r\n"""
        header += """Content-Type: text/xml;charset=utf-8\r\n"""
        header += """Content-Length: %d\r\n""" % xml_len
        header += """Connection: Keep-Alive\r\n"""
        header += """Accept-Language: pl-PL,en,*\r\n"""
        header += """User-Agent: Mozilla/5.0\r\n"""
        header += """Host: box.chomikuj.pl\r\n\r\n"""
        header += xml_content
        resp = self.send(header)
        resp_dict =  self.soap.soap_xml_to_dict(resp)
        status = resp_dict['s:Envelope']['s:Body']['UploadTokenResponse']['UploadTokenResult']['a:status']
        if status != 'Ok':
            self.view.print_( "Blad(pobieranie informacji z chomika):" )
            self.view.print_( status )
            return None, None, None, None
        try:
            self.token  = resp_dict['s:Envelope']['s:Body']['UploadTokenResponse']['UploadTokenResult']['a:key']
            self.stamp  = resp_dict['s:Envelope']['s:Body']['UploadTokenResponse']['UploadTokenResult']['a:stamp']
            self.server = resp_dict['s:Envelope']['s:Body']['UploadTokenResponse']['UploadTokenResult']['a:server']
            self.server, _, self.port = self.server.partition(":")
            return self.token, self.stamp, self.server, self.port
        except IndexError, e:
            self.view.print_( "Blad(pobieranie informacji z chomika):", e )
            self.view.print_( resp )
            return None, None, None, None
        
                

        
    def __upload(self, filepath, filename, token, stamp, server, port):
        """
        Wysylanie pliku znajdujacego sie pod 'filepath' i nazwanie go 'filename'
        #TODO: Opis i podpis
        """
        
        #Tworzenie naglowka
        size = os.path.getsize(filepath)
        header, contenttail =  self.__create_header(server, port, token, stamp, filename, size)  
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        ip = socket.gethostbyname_ex(server)[2][0]
        sock.connect( ( ip , int(port) ) )
        sock.send(header)
        
        f = open(filepath,'rb')
        pb = view.ProgressBar(total=size, rate_refresh = 0.5, count = 0, name = filepath)
        self.view.add_progress_bar(pb)
        last_time = time.time()
        try:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                sock.send(chunk)
                pb.update(len(chunk))
                now = time.time()
                if now - last_time > 0.5:
                    self.view.update_progress_bars()
                    last_time = now
            f.close()        
            #self.view.print_( 'Sending tail' )
            sock.send(contenttail)
        finally:
            self.view.update_progress_bars()
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
        self.relogin()
        self.chomik_id = chomik_id
        self.folder_id = folder_id
        filename_tmp   = change_coding(filename)        
        filesize_sent = self.__resume_get_tokens(filepath, filename_tmp, token, server, port)
        if filesize_sent == False:
            return False
        else:
            return self.__resume(filepath, filename_tmp, token, server, port, stamp, filesize_sent)


    def __resume_get_tokens(self, filepath, filename, token, server, port):
        """
        Pobiera informacje z serwera o tym gdzie i z jakimi parametrami wyslac plik
        """
        #Pobieranie informacji o serwerze
        filename_len = len(filename)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (server, int(port) ) )
        tmp = """GET /resume/check/?key={0}& HTTP/1.1\r\nConnection: close\r\nUser-Agent: ChomikBox\r\nHost: {1}:{2}\r\n\r\n""".format(token, server, port)
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
        try:
            filesize_sent = int(re.findall( """<resp file_size="([^"]*)" skipThumbnails="[^"]*" res="1"/>""", resp)[0])
            return filesize_sent
        except IndexError, e:
            self.view.print_( "Nie mozna bylo wznowic pobierania" )
            self.view.print_( resp )
            return False
        


    def __resume(self, filepath, filename, token, server, port, stamp, filesize_sent):
        """
        Wznawianie uploadowania pliku filepath o nazwie filename o danych: folder_id, chomik_id, token, server, port, stamp
        """
        #Tworzenie naglowka
        size  = os.path.getsize(filepath)
        header, contenttail =  self.__create_header(server, port, token, stamp, filename, (size - filesize_sent), resume_from = filesize_sent)  
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect( (server,int(port) ) )
        sock.send(header)
        
        f = open(filepath,'rb')
        f.seek(filesize_sent)
        pb = view.ProgressBar(total=size, rate_refresh = 0.5, count = filesize_sent, name = filepath)
        self.view.add_progress_bar(pb)
        last_time = time.time()
        try:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                sock.send(chunk)
                pb.update(len(chunk))
                now = time.time()
                if now - last_time > 0.5:
                    self.view.update_progress_bars()
                    last_time = now
            f.close()        
            sock.send(contenttail)
        finally:
            self.view.update_progress_bars()
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
    pass
