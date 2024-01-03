from sio.compilers.common import Compiler
from sio.workers.util import tempcwd
from sio.workers.executors import noquote
import os
import time

class PythonCompiler(Compiler):
    sandbox = 'python.3_6_5'
    lang = 'py'
    output_file = 'a.pyc' # hardcoded anyway in python3compile.py
    options = []  # Compiler options

    def _make_cmdline(self, executor):
        cmdline = [noquote(tempcwd(self.source_file))] #'/usr/bin/python3compile.py',  tempcwd(self.source_file)]
        os.chmod(tempcwd(os.path.dirname(self.source_file)), 0o777)
        os.chmod(tempcwd(self.source_file), 0o777)
        return cmdline

    def _postprocess(self, renv):
        self.environ = super(PythonCompiler, self)._postprocess(renv)
        if 'exec_info' in list(self.environ.keys()):
            self.environ['exec_info']['mode']='python3'
        return self.environ

def run_python(environ):
    return PythonCompiler().compile(environ)

run_default_py = run_python

