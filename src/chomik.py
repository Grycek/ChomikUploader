#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# Author: Adam Grycner (adam_gr [at] gazeta.pl)
#
# Written: 23/02/2011
#
# Released under: GNU GENERAL PUBLIC LICENSE
#
# Ver: 0.2


import urllib2, urllib
import re
import socket
import cookielib
import sys
import mimetypes
import os
import progress
import time

glob_timeout = 240

#viewstate, user, pass
httpdata_logon = """__EVENTTARGET=&__EVENTARGUMENT=&__VIEWSTATE={0}&PageCmd=&PageArg=&ctl00%24LoginTop%24LoginChomikName={1}&ctl00%24LoginTop%24LoginChomikPassword={2}&ctl00%24LoginTop%24LoginButton.x=3&ctl00%24LoginTop%24LoginButton.y=12&ctl00%24SearchInputBox=&ctl00%24SearchFileBox=&ctl00%24SearchType=all&SType=0&ctl00%24CT%24ChomikLog%24LoginChomikName=&ctl00%24CT%24ChomikLog%24LoginChomikPassword="""

httpdata_mkdir = """ctl00%24SM=ctl00%24CT%24NewFolderW%24NFUp%7Cctl00%24CT%24NewFolderW%24NewFolderButton&PageCmd=&PageArg=undefined&ctl00%24SearchInputBox=&ctl00%24SearchFileBox=&ctl00%24SearchType=all&SType=0&ctl00%24CT%24ChomikID={0}&ctl00%24CT%24TW%24TreeExpandLog=20188%7C&ChomikSubfolderId={1}&ctl00%24CT%24FW%24SubfolderID={2}&FVSortType=1&FVSortDir=1&FVSortChange=&FVPage=0&ctl00%24CT%24FrW%24FrPage=1&FrGroupId=0&FrRefPage=&FrGrpPage=&FrGrpName=&ctl00%24CT%24NewFolderW%24NewFolderTextBox={3}&ctl00%24CT%24NewFolderW%24AFDescr=&ctl00%24CT%24NewFolderW%24AFPass=&__EVENTTARGET=ctl00%24CT%24NewFolderW%24NewFolderButton&__EVENTARGUMENT=&__VIEWSTATE={4}&__ASYNCPOST=true&"""

#ChomikID, ChomikSubfolderId, SubfolderId, FolderAddress, viewstate
httpdata_rmdir = """ctl00%24SM=ctl00%24SM%7Cctl00%24CT%24TW%24DynamicFolderLink&PageCmd=&PageArg=undefined&ctl00%24SearchInputBox=&ctl00%24SearchFileBox=&ctl00%24SearchType=all&SType=0&ctl00%24CT%24ChomikID={0}&treeExpandLog=0%7C5762328%7C31%7C32%7C34%7C&ChomikSubfolderId={1}&ctl00%24CT%24FW%24SubfolderID={2}&FVSortType=1&FVSortDir=1&FVSortChange=&FVPage=0&ctl00%24CT%24FW%24inpFolderAddress={3}&ctl00%24CT%24FrW%24FrPage=0&FrGroupId=0&FrRefPage=&FrGrpPage=&FrGrpName=&__EVENTTARGET=ctl00%24CT%24TW%24DynamicFolderLink&__EVENTARGUMENT=&__VIEWSTATE={4}&__ASYNCPOST=true&"""

def to_chomik_url(adr):
    #changes to chomikuj.pl adres format
    return urllib2.quote(adr).replace('%20','+').replace('%29',')').replace('%28','(').replace('%27',"'").replace('%21','!').replace('%','*')
    
def from_chomik(adr):
    #changes from chomikuj.pl adres format
    return urllib2.unquote(adr.replace('+', '%20').replace('*','%'))
    

class Chomik(object):
    def __init__(self):
        self.opener  = urllib2.build_opener()
        #current position
        self.cur_adr = 'http://chomikuj.pl'


        
    def login(self, user, password):
        """
        Logowanie sie do chomika
        Zwraca True przy pomyslnym zalogowani, a False wpp
        """
        #Wlaczenie trybu debuggowania
        #(wyswietlanie wysylanych i otrzymywanych pakietow)
        h         = urllib2.HTTPHandler(debuglevel=0)
        #obsluga ciasteczek
        self.jar  = cookielib.CookieJar()
        
        httpcookies = urllib2.HTTPCookieProcessor()
        opener    =  urllib2.build_opener(h, httpcookies)
        #Przedstawiajmy sie jakos ladnie
        opener.addheaders = [('User-Agent','Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)')]
        
        #print "Logowanie"
        request   = urllib2.Request("http://chomikuj.pl")
        response  = opener.open(request)
        tekst     = response.read()
        viewstate = re.findall('id=\"__VIEWSTATE\" value=\"([^\"]*)\"', tekst)[0]
        response.close()
        request.add_data(httpdata_logon.format(viewstate, user, password))
        
        response  = opener.open(request)
        url       = response.geturl()
        tekst     = response.read()
        response.close()
        
        self.opener  = opener
        self.cur_adr = url
        #czy znalezlismy slowo wyloguj w wyniku
        return tekst.find('Wyloguj') > 0



    
    def chdirs(self, directories):
        """
        Zmien katalog na chomiku. Jezeli jakis katalog nie istnieje, to zostaje stworzony
        np. (chdirs(/katalog1/katalog2/katalog3) )
        """
        dirs = [i for i in directories.split('/') if i != '']
        for dir in dirs:
            changed = self.chdir(dir.replace('/',''))
            if changed != True:
                self.mkdir(dir.replace('/',''))
                if self.chdir(dir.replace('/','')) != True:
                    print "Nie zmieniono katalogu :", '\n', self.cur_adr,'\n', dir,'\n'
                    return False
        return True
        
    

    
    def chdir(self, directory):
        """
        Zmien katalog (zmiana o jeden poziom)
        """
        if directory == '..':
            return self.__chdir_up()
        
        request   = urllib2.Request(self.cur_adr + '/' + to_chomik_url(directory) )
        try:
            response  = self.opener.open(request, timeout = glob_timeout)
        except Exception:
            print "Chdir - timeout"
            #TODO: cos robic z tym wyjatkiem
            raise
        tekst     = response.read()
        response.close()
        
        try:
            try:
                return_adr = re.findall('<b>adres folderu:</b>[^<]*<a id="[^"]*" href="([^"]*)"' ,tekst)[0]
            except Exception:
                return_adr = re.findall('<a href="([^"]*)" id="ctl00_CT_FW_WWW' ,tekst)[0]
        except Exception:
            print "Faild to change dir {0}".format(directory)
            return False
        
        if return_adr.lower() == \
            (self.cur_adr + '/' + to_chomik_url(directory)).lower():
            self.cur_adr += '/' + to_chomik_url(directory)
            return True
        else:
            print 'Returned adr:\n', return_adr,'\nExpected adr:\n', (self.cur_adr + '/' + to_chomik_url(directory))
            #print return_adr.lower() == (self.cur_adr + '/' + to_chomik_url(directory)).lower(), '\n'
            return False

    
    def __chdir_up(self):
        #wyjdz z katalogu
        if self.cur_adr.count('/') <= 3:
            # jezeli jestes w pozycji root drzewa katalogow
            #to nie mozesz pojsc wyzej
            return False
        #zmiana adresu (odcinamy koncowke)
        self.cur_adr,_,_ = self.cur_adr.rpartition('/')
        return True

                
    def mkdir(self, dirname):
        #FIXME
        """
        Tworzenie katalogu
        """
        print "Creating", dirname, "directory"
        request   = urllib2.Request(self.cur_adr )
        response  = self.opener.open(request, timeout = glob_timeout)
        tekst     = response.read()
        ChomikID          = re.findall('<input name="ctl00\$CT\$ChomikID" type="hidden" id="ctl00_CT_ChomikID" value="(\d*)"' ,tekst)[0]
        ChomikSubfolderId = re.findall('<input id="ChomikSubfolderId" name="ChomikSubfolderId" type="hidden" value="(\d*)"', tekst)[0]
        SubfolderId       = re.findall('<input name="ctl00\$CT\$FW\$SubfolderID" type="hidden" id="ctl00_CT_FW_SubfolderID" value="(\d*)"', tekst)[0]
        viewstate         = re.findall('id=\"__VIEWSTATE\" value=\"([^\"]*)\"', tekst)[0]
        
        global httpdata_mkdir
        postdata  = httpdata_mkdir.format( ChomikID, ChomikSubfolderId, SubfolderId, urllib2.quote(dirname), viewstate)
        request   = urllib2.Request(self.cur_adr )
        request.add_data(postdata)
        
        response  = self.opener.open(request)    
        tekst     = response.read()
        response.close()
        
        if tekst.find('Nowy folder zosta') > 0:
            print "Creation success\n"
            return True
        else:
            print "Creation fail\n"
            return False


        
    def upload(self, filepath, filename):
        #FIXME
        """
        Wysylanie pliku znajdujacego sie pod 'filepath' i nazwanie go 'filename'
        #TODO: Opis i podpis
        """
        request   = urllib2.Request(self.cur_adr)
        response  = self.opener.open(request, timeout = glob_timeout)
        tekst     = response.read()
        response.close()  

        ChomikID          = re.findall('<input name="ctl00\$CT\$ChomikID" type="hidden" id="ctl00_CT_ChomikID" value="(\d*)"' ,tekst)[0]
        SubfolderId       = re.findall('<input name="ctl00\$CT\$FW\$SubfolderID" type="hidden" id="ctl00_CT_FW_SubfolderID" value="(\d*)"', tekst)[0]
        UploadToken       = ''
        TokenTime         = ''
        #Wejdz na podstrone uploadowania pliku (nacisniecie na przycisk dodaj nowy plik)
        request = urllib2.Request('http://chomikuj.pl/ChomikUploadingFile.aspx?id={0}&sid={1}&tk={2}&t={3}'.format(ChomikID, SubfolderId, UploadToken, TokenTime) )

        response  = self.opener.open(request, timeout = glob_timeout)
        #zapamietaj adres pod ktory zostalismy skierowani (znajduje sie tam m.in. nr serwera)
        tmp_url = response.geturl()
        _, host, urlpath =  re.findall('(http://(s\d*.chomikuj.pl)(/[^ ]*))', tmp_url)[0]
        tekst   = response.read()
        viewstate =  re.findall('id=\"__VIEWSTATE\" value=\"([^\"]*)\"', tekst)[0]
        response.close()
        
        size = os.path.getsize(filepath)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(glob_timeout)
        sock.connect((host, 80))
        header, contenttail =  self.__create_header(viewstate, SubfolderId, UploadToken, TokenTime, ChomikID, filename, filepath, host, urlpath, tmp_url, size)  
        sock.send(header)
        
        f = open(filepath)
        bufferlen = 0
        msglen    = 0
        pb = progress.ProgressMeter(total=size, rate_refresh = 0.5)
        while True:
            chunk = f.read(640)
            if not chunk:
                break
            sock.send(chunk)
            bufferlen += len(chunk)
            pere = float(bufferlen) / float(size) * 100
            rnd = round(pere, 1)
            pb.update(len(chunk))
            
        f.close()        
        print 'Sending tail'
        sock.send(contenttail)
        
        buff = 0
        result = ''
        while buff < 4000:
            tmp = sock.recv(640) 
            if tmp == '':
                break
            result += tmp
            buff   += len(tmp)
        sock.close()
        if result.find(':-)') > 0:
            return True  #uploadowanie sie powiodlo
        else:
            return False #uploadowanie sie nie powiodlo


    
    def __create_header(self, viewstate, SubfolderId, UploadToken, TokenTime, ChomikID, filename, filepath, host, urlpath, tmp_url, size):
        boundary      = "-----------------------------24725123512491151811399248393"
        contentheader  = boundary + '\r\nContent-Disposition: form-data; name="__EVENTTARGET"\r\n\r\nUploadButton\r\n'
        contentheader += boundary + '\r\nContent-Disposition: form-data; name="__EVENTARGUMENT"\r\n\r\n\r\n'
        contentheader += boundary + '\r\nContent-Disposition: form-data; name="__VIEWSTATE"\r\n\r\n{0}\r\n'.format(viewstate)
        contentheader += boundary + '\r\nContent-Disposition: form-data; name="SubfolderId"\r\n\r\n{0}\r\n'.format(SubfolderId)
        contentheader += boundary + '\r\nContent-Disposition: form-data; name="RegulationsOwner"\r\n\r\non\r\n'
        contentheader += boundary + '\r\nContent-Disposition: form-data; name="Token"\r\n\r\n{0}\r\n'.format(UploadToken)
        contentheader += boundary + '\r\nContent-Disposition: form-data; name="TokenTime"\r\n\r\n{0}\r\n'.format(TokenTime)
        contentheader += boundary + '\r\nContent-Disposition: form-data; name="ChomikId"\r\n\r\n{0}\r\n'.format(ChomikID)
        contentheader += boundary + '\r\nContent-Disposition: form-data; name="FileSample"; filename=""\r\nContent-Type: application/octet-stream\r\n\r\n\r\n'
        contentheader += boundary + '\r\nContent-Disposition: form-data; name="FileSampleDescription"\r\n\r\n\r\n'
        contentheader += boundary + '\r\nContent-Disposition: form-data; name="File1"; filename="{0}"\r\n'.format(filename) 
        mimetp, _      = mimetypes.guess_type(filepath)
        if mimetp != None:
            contentheader += boundary + 'Content-Type: {0}\r\n\r\n'.format(mimetp)
        else:
            contentheader += boundary + 'Content-Type: text/plain\r\n\r\n'
        
        contenttail   = '\r\n' + boundary + '\r\nContent-Disposition: form-data; name="File1Description"\r\n\r\n\r\n'
        contenttail  += '\r\n' + boundary + '\r\nContent-Disposition: form-data; name="FileUploader"\r\n\r\n\r\n'
        contenttail  += boundary + '--\r\n'
        #print 'Len1'
        contentlength = len(contentheader) + size + len(contenttail)
        #print 'Len2'
        header  = 'POST {0} HTTP/1.1\r\n'.format(urlpath)
        header += 'Host: {0}\r\n'.format(host)
        header += 'User-Agent: Mozilla/4.0 (compatible; MSIE 5.5; Windows NT\r\n'
        header += 'Referer: {0}\r\n'.format(tmp_url)
        header += 'Content-Type: multipart/form-data; boundary={0}\r\n'.format(boundary[2:]) #tutaj skrocilem boundary, bo tak jest w firefoksie
        header += 'Content-Length: {0}\r\n\r\n'.format(contentlength)
        header += contentheader
        return header, contenttail
