#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# Author: Adam Grycner (adam_gr [at] gazeta.pl)
#
# Written: 08/08/2011
#
# Released under: GNU GENERAL PUBLIC LICENSE
#
# Ver: 0.3
import os
import threading
import re


def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance


#@singleton
class Model(object):
    
    def __init__(self):
        """
        Wczytywanie danych z plikow uploaded.txt i notuploaded.txt
        """
        self.lock                  = threading.Lock()
        self.notuploaded_file_name = 'notuploaded.txt'
        self.uploaded_file_name    = 'uploaded.txt'
        self.uploaded              = []
        self.notuploaded           = []
        
        if not os.path.exists(self.uploaded_file_name):
            open(self.uploaded_file_name, 'w').close()
        f = open(self.uploaded_file_name, 'r')
        self.uploaded = f.read().split('\n')
        self.uploaded = set([i.strip() for i in self.uploaded])
        f.close()
        #TODO: tu stanowczo jakis test zrobic
        if not os.path.exists(self.notuploaded_file_name):
        	open(self.notuploaded_file_name,"w")
        f     = open(self.notuploaded_file_name,"r")
        files = [ i.strip() for i in f.readlines()]
        f.close()
        self.notuploaded_resume = []
        self.notuploaded_normal = []
        
        for f in files:
            try:
                filepath, filename, folder_id, chomik_id, token, host, port, stamp = re.findall("([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)", f)[0]
                self.notuploaded_resume.append( (filepath, filename, folder_id, chomik_id, token, host, port, stamp) )
            except IndexError, e:
                self.notuploaded_normal.append( f.strip() )
        
    
    def add_notuploaded_normal(self, filepath):
        """
        Dodawanie informacji o filepath na liscie notuploaded i w pliku notuploaded.txt
        """
        self.lock.acquire()
        try:
            if not filepath in self.notuploaded_normal:
                self.notuploaded_normal.append(filepath)
                f = open(self.notuploaded_file_name,'a')
                f.write(filepath + '\r\n')
                f.close()
        finally:
            self.lock.release()

    def add_notuploaded_resume(self, filepath, filename, folder_id, chomik_id, token, host, port, stamp):
        """
        Dodawanie informacji o filepath i danych do wznawiania na liscie notuploaded i w pliku notuploaded.txt
        """
        self.lock.acquire()
        try:
            self.notuploaded_resume = [ i for i in self.notuploaded_resume if i[0] != filepath]
            self.notuploaded_normal = [ i for i in self.notuploaded_normal if i != filepath]
            self._save_notuploaded()
            self.notuploaded_resume.append( (filepath, filename, folder_id, chomik_id, token, host, port, stamp) )
            f = open(self.notuploaded_file_name,'a')
            f.write(filepath + '\t')
            f.write(filename + '\t')
            f.write(str(folder_id) + '\t')
            f.write(str(chomik_id) + '\t')
            f.write(str(token) + '\t')
            f.write(str(host) + '\t')
            f.write(str(port) + '\t')
            f.write(str(stamp))
            f.write('\r\n')
            f.close()
        finally:
            self.lock.release()
    
    def remove_notuploaded(self, filepath):
        """
        Usuwanie filepath z listy notuploaded i z pliku notuploaded.txt
        """
        self.lock.acquire()
        try:
            self.notuploaded_resume = [ i for i in self.notuploaded_resume if i[0] != filepath]
            self.notuploaded_normal = [ i for i in self.notuploaded_normal if i != filepath]
            self._save_notuploaded()
        finally:
            self.lock.release()

    def _save_notuploaded(self):
        """
        Zapisanie do pliku nieudanych wyslan
        """
        f = open(self.notuploaded_file_name,'w')
        for nu in self.notuploaded_resume:
            l = [ str(i) for i in list(nu)]
            f.write( '\t'.join(l) )
            f.write( '\r\n' )
        for nu in self.notuploaded_normal:
            f.write( nu )
            f.write( '\r\n' )
        f.close()

        
    def get_notuploaded_resume(self):
        """
        Zwraca liste plikow, ktore mozna wznowic
        """
        return self.notuploaded_resume


    def add_uploaded(self, filepath):
        """
        Dodanie filepath do listy plikow poprawnie wyslanych
        """
        self.lock.acquire()
        try:
            self.uploaded.add(filepath)
            f = open(self.uploaded_file_name,'a')
            f.write(filepath + '\r\n')
            f.close()
        finally:
            self.lock.release()


    def in_uploaded(self, filepath):
        """
        Sprawdzanie, czy plik znajduje sie na liscie plikow wyslanych
        """
        self.lock.acquire()
        try:
            result = filepath in self.uploaded
        finally:
            self.lock.release()
        return result
        
    
if __name__ == '__main__':
    pass
