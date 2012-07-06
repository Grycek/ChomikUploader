#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# Author: Adam Grycner (adam_gr [at] gazeta.pl)
#
# Written: 12/11/2011
#
# Released under: GNU GENERAL PUBLIC LICENSE
#
# Ver: 0.4
import os
import threading
import re
import view


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
        self.view                  = view.View()
        self.lock                  = threading.Lock()
        ##synchronizacja zmiany katalogow w chomiku
        self.chdirs_lock           = threading.Lock()
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
        self.pending            = []
        
        for f in files:
            try:
                filepath, filename, folder_id, chomik_id, token, host, port, stamp = re.findall("([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)", f)[0]
                self.notuploaded_resume.append( (filepath, filename, folder_id, chomik_id, token, host, port, stamp) )
            except IndexError, e:
                self.notuploaded_normal.append( f.strip() )
        
    
    def _aux_remove_notuploaded_resume(self, filepath):
        it = 0
        while it < len(self.notuploaded_resume):
            i = self.notuploaded_resume[it]
            if i[0] == filepath:
                self.notuploaded_resume.remove(i)
            it += 1
            
    def _aux_remove_notuploaded_normal(self, filepath):
        it = 0
        while it < len(self.notuploaded_normal):
            i = self.notuploaded_normal[it]
            if i == filepath:
                self.notuploaded_normal.remove(i)
            it += 1
            
    def _aux_remove_pending(self, filepath):
        it = 0
        while it < len(self.pending):
            i = self.pending[it]
            if i == filepath:
                self.pending.remove(i)
            it += 1
    
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
            #FIXME:danger
            self._aux_remove_notuploaded_resume(filepath)
            self._aux_remove_notuploaded_normal(filepath)
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
            #FIXME:danger
            self._aux_remove_notuploaded_resume(filepath)
            self._aux_remove_notuploaded_normal(filepath)
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
    
    def add_to_pending(self, filepath):
        pass
    
    def remove_from_pending(self, filepath):
        self.lock.acquire()
        try:
            #FIXME:danger
            self._aux_remove_pending(filepath)
            #self.pending = [i for i in self.pending if i != filepath]
        finally:
            self.lock.release()
        
    def is_uploaded_or_pended_and_add(self, filepath):
        """
        Sprawdza, cyz plik byl juz wyslany lub, czy jest przetwarzany.
        Jesli nie, to dodaje go do listy przetwarzanych
        """
        self.lock.acquire()
        try:
            result1 = filepath in self.uploaded
            result2 = filepath in self.pending
            result  = (result1 or result2)
            if (not result1) and (not result2):
                self.pending.append(filepath)
        finally:
            self.lock.release()
        return result
    
    def return_chdirlock(self):
        return self.chdirs_lock
    
if __name__ == '__main__':
    m = Model()
    print m.add_uploaded('./tmp.txt')
    print m.is_uploaded_or_pended_and_add('./tmp.txt')
    print m.is_uploaded_or_pended_and_add('./tmp.txt')
