import os.path
import logging

from sio.workers import ft
from sio.workers.executors import UnprotectedExecutor, SandboxExecutor, \
        ExecError, PRootExecutor
from sio.workers.util import tempcwd

logger = logging.getLogger(__name__)

DEFAULT_CHECKER_TIME_LIMIT = 30000  # in ms
DEFAULT_CHECKER_MEM_LIMIT = 256 * 2**10  # in KiB
RESULT_STRING_LENGTH_LIMIT = 1024  # in bytes

class CheckerError(Exception):
    pass

def _run_in_executor(env, command, executor, **kwargs):
    with executor:
        return executor(command,
            capture_output=True, split_lines=True,
            mem_limit=DEFAULT_CHECKER_MEM_LIMIT,
            time_limit=DEFAULT_CHECKER_TIME_LIMIT,
            environ=env, environ_prefix='checker_', **kwargs)

def _run_diff(env):
    renv = _run_in_executor(env, ['diff', '-b', '-q', 'out', 'hint'],
            UnprotectedExecutor(), extra_ignore_errors=(1,))
    return renv['return_code'] and ['WA'] or ['OK']

def _run_checker(env, use_sandboxes=False):

    # same for testlib and sinol checkers
    command = ['./chk', 'in', 'out', 'hint']

    def execute_checker(with_stderr=False):
        if env.get('untrusted_checker', False) and use_sandboxes:
            return _run_in_executor(env, command,
                    PRootExecutor('null-sandbox'), ignore_return=True,
                    forward_stderr=with_stderr)
        else:
            return _run_in_executor(env, command, UnprotectedExecutor(),
                    ignore_errors=True, forward_stderr=with_stderr)


    is_testlib = (env.get('checker_mode')=='testlib')
    renv = execute_checker(with_stderr=True)

    if is_testlib:
        #raise RuntimeError("\ntestlib checker!\nenviron:\n%s\n"%str(env))
        output = []
        if renv.get('return_code') == 0: output += ['OK']
        else:
            output += ['WRONG\n']
            #raise RuntimeError('throwing WA with renv=%s\n'%str(renv))
        output += ['\n'.join(renv.get('stdout'))]
        output += ['100']

        #output = ['WRONG', 'hedgehog\nhunting\nis illegal!!!1!11!', '100']
        #raise RuntimeError("testlib returns: [%s]\n\n"%output)
        return output
    else:
        if renv['return_code'] >= 2:
            renv = execute_checker(with_stderr=True)
            raise CheckerError(
                    'Checker returned code(%d) >= 2. Checker stdout and stderr: ' \
                    '"%s". Checker environ dump: %s' \
                            % (renv['return_code'], renv['stdout'], env))
        return renv['stdout']

def _run_compare(env):
    e = SandboxExecutor('exec-sandbox')
    renv = _run_in_executor(env, [os.path.join('bin', 'compare'),
            'hint', 'out'], e, ignore_errors=True)
    return renv['stdout']

def _limit_length(s):
    if len(s) > RESULT_STRING_LENGTH_LIMIT:
        suffix = '[...]'
        return s[:max(0, RESULT_STRING_LENGTH_LIMIT - len(suffix))] + suffix
    return s

def run(environ, use_sandboxes=True):

    ft.download(environ, 'out_file', 'out', skip_if_exists=True)
    ft.download(environ, 'hint_file', 'hint', add_to_cache=True)

    try:
        if environ.get('chk_file'):
            ft.download(environ, 'in_file', 'in', skip_if_exists=True,
                    add_to_cache=True)
            ft.download(environ, 'chk_file', 'chk', add_to_cache=True)
            os.chmod(tempcwd('chk'), 0o700)

            output = _run_checker(environ, use_sandboxes)
        elif use_sandboxes:
            output = _run_compare(environ)
        else:
            output = _run_diff(environ)
    except (CheckerError, ExecError) as e:
        logger.error('Checker failed! %s', e)
        logger.error('Environ dump: %s', environ)
        raise SystemError(e)

    while len(output) < 3:
        output.append('')
    if output[0] == 'OK':
        environ['result_code'] = 'OK'
        if output[1]:
            environ['result_string'] = _limit_length(output[1])
        environ['result_percentage'] = float(output[2] or 100)
    else:
        environ['result_code'] = 'WA'
        environ['result_string'] = _limit_length(output[1])
        environ['result_percentage'] = 0
    return environ
