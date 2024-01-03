from builtins import object
import xmlrpc.client
import os

CONNECT_TO='http://'+os.environ['SIOWORKERSD_HOST']+':7899'

def with_connection(fn):
    def wrapped(*args, **kwargs):
        server = xmlrpc.client.ServerProxy(CONNECT_TO, allow_none=True)

        try:
            return fn(server, *args, **kwargs)
        except Exception:
            raise

    return wrapped

@with_connection
def compilation_started(conn, env):
    if 'judgings' not in env: return
    for jid in list(env['judgings'].values()):

        conn.CompilationStarted(jid)

@with_connection
def compilation_finished(conn, env):
    if 'judgings' not in env: return
    for jid in list(env['judgings'].values()):
        conn.CompilationFinished(jid, env['result_code'], env['compiler_output'])

@with_connection
def judge_started(conn, env):
    if 'judging_id' not in env: return

    conn.JudgeStarted(env['judging_id'], env['name'])

class PrepareResponse(object):
    def __init__(self, val):
        self.force_not_judge = val

@with_connection
def judge_prepare(conn, env):
    if 'judging_id' not in env: return PrepareResponse(False)

    return PrepareResponse(conn.JudgePrepare(env['judging_id'], env['name']))

@with_connection
def judge_finished(conn, env):
    if 'judging_id' not in env: return

    return conn.JudgeFinished(env['judging_id'], env['name'], env['result_code'])

