from distutils.core import setup


setup(name='chomikUploader',
      version='0.2',
      author='adam_gr',
      author_email='adam_gr [at] gazeta.pl',
      description='Uploading files on chomikuj.pl',
      package_dir = {'chomikuploader' : 'src'},
      packages = ['chomikuploader'],
      scripts = ['chomik']
     )
