from distutils.core import setup
import sys
import os

if sys.platform.startswith('win'):
    import py2exe
    
setup(name='chomikUploader',
          version='0.5.4.3',
          author='adam_gr',
          author_email='adam_gr [at] gazeta.pl',
          description='Uploading files on chomikuj.pl',
          package_dir = {'chomikuploader' : 'src'},
          packages = ['chomikuploader'],
          options = {"py2exe" : {
                                  "compressed" : True,
                                  "ignores" : ["email.Iterators", "email.Generator"],
                                  "bundle_files" : 1
                                },
                     "sdist"  : {
                                  'formats': 'zip'
                                }
                    },
          scripts = ['chomik'],
          console = ['chomik'],
          zipfile = None
         )

