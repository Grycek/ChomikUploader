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
import time
import cgi
##################
from soap import SOAP


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

###########################################################
import htmlentitydefs, re

_char = re.compile(r'&(\w+?);')
_dec  = re.compile(r'&#(\d{2,4});')
_hex  = re.compile(r'&#x(\d{2,4});')

def _char_unescape(m, defs=htmlentitydefs.entitydefs):
    try:
        return defs[m.group(1)]
    except KeyError:
        return m.group(0)

def unescape(string):
    """back replace html-safe sequences to special characters
        >>> unescape('&lt; &amp; &gt;')
        '< & >'
        >>> unescape('&#39;')
        "'"
        >>> unescape('&#x27;')
        "'"
    
    full list of sequences: htmlentitydefs.entitydefs
    """
    result = _hex.sub(lambda x: unichr(int(x.group(1), 16)),\
        _dec.sub(lambda x: unichr(int(x.group(1))),\
            _char.sub(_char_unescape, string)))
    if string.__class__ != unicode:
        return result.encode('utf-8')
    else:
        return result
###########################################################
glob_timeout = 20
#KONFIGURACJA
#login_ip   = "208.43.223.12"
#login_ip   = "main.box.chomikuj.pl"
login_ip   = "box.chomikuj.pl"
#login_port = 8083
login_port = 80
version = "2.0.5"
client = "ChomikBox-" + version


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


def escape_name(text):  
    return cgi.escape(text)

def unescape_name(text):
    text = text.replace("&quot;", '"')
    text = text.replace("&apos;", "'")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
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
    def __init__(self, view_ = None, model_ = None, debug = False):
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
        self.last_login    = 0
        self.debug         = debug


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
        #we log in recently
        if self.last_login + 300 > time.time():
            return True
        self.last_login = time.time()
        password = hashlib.md5(self.password).hexdigest()
        xml_dict = xml_dict = [('ROOT',[('name' , self.user), ('passHash', password), ('ver' , '4'), ('client',[('name','chomikbox'),('version',version) ]) ])]
        xml_content = self.soap.soap_dict_to_xml(xml_dict, "Auth").strip()
        xml_len = len(xml_content)
        header  = """POST /services/ChomikBoxService.svc HTTP/1.1\r\n"""
        header += """SOAPAction: http://chomikuj.pl/IChomikBoxService/Auth\r\n"""
        #header += """Content-Encoding: identity\r\n"""
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
            if self.ses_id == "-1" or self.chomik_id == "-1":
                return False 
        except IndexError, e:
            self.view.print_( "Blad(relogin):" )
            self.view.print_( e )
            #self.view.print_( resp )
            return False
        else:
            return True
        
        

    def get_dir_list(self, folder_id = 0, folder_dom_root = {}):
        """
        Pobiera liste folderow chomika.
        """
        self.relogin()
        xml_dict = [('ROOT',[('token' , self.ses_id), ('hamsterId', self.chomik_id), ('folderId' , folder_id), ('depth' , 0) ])]
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
        if folder_id == 0:
            self.folders_dom = resp_dict['s:Envelope']['s:Body']['FoldersResponse']['FoldersResult']['a:folder']
        else:
            #print "Get list dir:",  resp_dict['s:Envelope']['s:Body']['FoldersResponse']['FoldersResult']['a:folder']
            #FIXME danger
            folder_dom_root[u'folders'] = resp_dict['s:Envelope']['s:Body']['FoldersResponse']['FoldersResult']['a:folder'][u'folders']
            return True
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
                #f = f[:100]
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
            name = self.__dirname_refinement(f)
            name = to_unicode(name)
            if name in [unescape_name(i.get("name","")) for i in list_of_subfolders ]:
                for i in list_of_subfolders:
                    if name == unescape_name(i.get("name","")):
                        dom       = i
                        folder_id = i["id"]
                        break
            else:
                return (False, None, None)
        return (True,dom, folder_id)


    
    def __create_nodes(self, folder_list):
        folder_id = '0'
        fold      = []
        #self.get_dir_list()
        dom       = self.folders_dom
        for f in folder_list:
            list_of_subfolders = dom.get('folders', {}).get('FolderInfo', {})
            if type(list_of_subfolders) == dict:
                list_of_subfolders = [list_of_subfolders]
            name = self.__dirname_refinement(f)
            name = to_unicode(name)
            if name in [unescape_name(i.get("name","")) for i in list_of_subfolders ]:
                for i in list_of_subfolders:
                    if name == unescape_name(i.get("name","")):
                        dom       = i
                        folder_id = i["id"]
                        fold.append(f)
                        break
                        #self.view.print_( folder_id, f )
            else:
                #TODO: update self.folder_dom
                self.mkdir(name, folder_id)
                self.get_dir_list(folder_id, dom)
                result, dom, folder_id = self.__access_node(fold + [f])
                #jezeli nie udalo sie ani utworzyc ani przejsc, to zwroc False
                if result == False:
                    return (False, None, None)
                else:
                    fold.append(f)
        return (True,dom, folder_id)
    

    def __dirname_refinement(self, dirname):
        """
        Usuwa niedozwolone znaki z nazwy katalogu
        """
        dirname = to_unicode(dirname)[:256]
        #\ / : * ? " < > |.
        not_allowed = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
        for ch in not_allowed:
            if ch in dirname:
                dirname = dirname.replace(ch,"")
        if dirname.startswith("."):
            dirname = dirname[1:]
        if dirname.endswith("."):
            dirname = dirname[:-1]         
        dirname = dirname.encode('utf8')
        return dirname
    
    def mkdir(self, dirname, folder_id = None):
        """
        Tworzenie katalogu w katalogu o id = folder_id
        """
        #if len(dirname) > 100:
        #    self.view.print_( "Dirname too long" )
        #    self.view.print_( "Dirname shortened\r\n" )
        #    dirname = to_unicode(dirname).encode("utf8")
        dirname = self.__dirname_refinement(dirname)
        self.relogin()
        if folder_id == None:
            folder_id = self.folder_id
        dirname   = change_coding(dirname)
        self.view.print_( "Creating", dirname, "directory" )
        dirname   = escape_name(dirname)
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
        filename_tmp               = escape_name(filename_tmp)
        self.model.add_notuploaded_normal(filepath)
        token, stamp, server, port = self.__upload_get_tokens(filepath, filename_tmp)
        #saving information for resuming
        self.model.add_notuploaded_resume(filepath, filename, self.folder_id, self.chomik_id, token, server, port, stamp)
        if token == None:
            return False
        else:
            result = self.__upload_with_resume_option( filepath, filename, token, stamp, server, port, self.chomik_id, self.folder_id)
            if result == True:
                self.model.remove_notuploaded(filepath)
            return result
        
    def __upload_with_resume_option(self, filepath, filename, token, stamp, server, port, chomik_id, folder_id):
        try:
            result = self.__upload(filepath, filename, token, stamp, server, port)
        except (socket.error, socket.timeout), e:
            self.view.print_("Wznawianie\n")
            result = self.resume(filepath, filename, folder_id, chomik_id, token, server, port, stamp)
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
            self.locale = resp_dict['s:Envelope']['s:Body']['UploadTokenResponse']['UploadTokenResult']['a:locale']
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
                #self.view.print_( 'Sending Chunk: ' + str(len(chunk)) )
                sock.send(chunk)
                #self.view.print_( 'Chunk sent' )
                pb.update(len(chunk))
                #self.view.print_( 'Updating progressbar' )
                now = time.time()
                if now - last_time > 0.5:
                    self.view.update_progress_bars()
                    last_time = now
            f.close()        
            #self.view.print_( 'Sending tail' )
            sock.send(contenttail)
        except Exception, e:
        	if self.debug:
        	    trbck = sys.exc_info()[2]
        	    debug_fun(trbck)
        	raise e
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
        #boundary = "--!CHB" + str(int(time.time()))
        boundary = "--!CHB" + stamp
        
        contentheader  = boundary + '\r\nname="chomik_id"\r\nContent-Type: text/plain\r\n\r\n{0}\r\n'.format(self.chomik_id)
        contentheader += boundary + '\r\nname="folder_id"\r\nContent-Type: text/plain\r\n\r\n{0}\r\n'.format(self.folder_id)
        contentheader += boundary + '\r\nname="key"\r\nContent-Type: text/plain\r\n\r\n{0}\r\n'.format(token)
        contentheader += boundary + '\r\nname="time"\r\nContent-Type: text/plain\r\n\r\n{0}\r\n'.format(stamp)
        if resume_from > 0:
            contentheader += boundary + '\r\nname="resume_from"\r\nContent-Type: text/plain\r\n\r\n{0}\r\n'.format(resume_from)
        contentheader += boundary + '\r\nname="client"\r\nContent-Type: text/plain\r\n\r\n{0}\r\n'.format(client)
        contentheader += boundary + '\r\nname="locale"\r\nContent-Type: text/plain\r\n\r\n{0}\r\n'.format("PL")
        contentheader += boundary + '\r\nname="file"; filename="{0}"\r\n\r\n'.format(filename)
        
        contenttail   = "\r\n" + boundary + '--\r\n\r\n'
        
        contentlength = len(contentheader) + (size - 2) + len(contenttail)

        header   = "POST /file/ HTTP/1.0\r\n"
        header  += "Content-Type: multipart/mixed; boundary={0}\r\n".format(boundary[2:])
        #header  += "Connection: close\r\n"
        header  += "Host: {0}:{1}\r\n".format(server,port)
        header  += "Content-Length: {0}\r\n\r\n".format(contentlength)
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
        if (filesize_sent == -1) or token == None:
            if self.debug:
                self.view.print_( "Resume ", filename_tmp )
                self.view.print_( "Filesize sent", filesize_sent )
            return False
        else:
            return self.__resume_with_resume_option(filepath, filename, token, server, port, stamp, filesize_sent, chomik_id, folder_id)
    
    def __resume_with_resume_option(self, filepath, filename, token, server, port, stamp, filesize_sent, chomik_id, folder_id):
        try:
            result = self.__resume(filepath, filename, token, server, port, stamp, filesize_sent)
            self.view.print_( "Result", result )
        except (socket.error, socket.timeout), e:
            self.view.print_("Wznawianie\n")
            result = self.resume(filepath, filename, folder_id, chomik_id, token, server, port, stamp)
        return result


    def __resume_get_tokens(self, filepath, filename, token, server, port):
        """
        Pobiera informacje z serwera o tym gdzie i z jakimi parametrami wyslac plik
        """
        #Pobieranie informacji o serwerze
        filename_len = len(filename)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        ip = socket.gethostbyname_ex(server)[2][0]
        sock.connect( (ip, int(port) ) )
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
            return -1
        


    def __resume(self, filepath, filename, token, server, port, stamp, filesize_sent):
        """
        Wznawianie uploadowania pliku filepath o nazwie filename o danych: folder_id, chomik_id, token, server, port, stamp
        """
        #Tworzenie naglowka
        size  = os.path.getsize(filepath)
        header, contenttail =  self.__create_header(server, port, token, stamp, filename, (size - filesize_sent), resume_from = filesize_sent)  
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        ip = socket.gethostbyname_ex(server)[2][0]
        sock.connect( (ip,int(port) ) )
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
        except Exception, e:
            if self.debug:
                trbck = sys.exc_info()[2]
                debug_fun(trbck)
            raise e
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
