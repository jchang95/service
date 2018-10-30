from distutils.core import setup
import py2exe,sys,os

sys.argv.append('py2exe')

setup(
  options = {'py2exe':{'bundle_files':1,'compressed':True}},
  console=[{'script':"SOProcessing.py"}],
  zipfile = None,
)

##setup(
##    console=[{'script':"SO_processFW.py"}],
##    options={"py2exe": {"includes": "decimal"}}
##)

#'dll_excludes': ['MSVCP90.dll', 'HID.DLL', 'w9xpopen.exe']},
