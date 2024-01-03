import urllib.parse
import importlib
import platform

import zope

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application import service
from twisted.application import internet

from sio.protocol.worker import WorkerFactory
from sio.sioworkersd.workermanager import WorkerManager
from sio.sioworkersd.scheduler import getDefaultSchedulerClassName
from sio.sioworkersd.taskmanager import TaskManager
from sio.sioworkersd import siorpc


def _host_from_url(url):
    return urllib.parse.urlparse(url).hostname


class WorkerOptions(usage.Options):
    # TODO: default concurrency to number of detected cpus
    optParameters = [['port', 'p', 7888, "sioworkersd port number", int],
                     ['concurrency', 'c', 1, "maximum concurrent jobs", int],
                     ['name', 'n', platform.node(), "worker name"]]
    optFlags = [['can-run-cpu-exec', None,
                    "Mark this worker as suitable for running tasks, which "
                    "are judged in safe mode on cpu (without oitimetool). "
                    "Has effect only for tasks received from oioioi instances "
                    "with USE_UNSAFE_EXEC disabled. All workers with this "
                    "option enabled should have same cpu. "]]

    def parseArgs(self, host):
        self['host'] = host

@zope.interface.implementer(service.IServiceMaker, IPlugin)
class WorkerServiceMaker(object):
    """Run worker process.
    """
    tapname = 'worker'
    description = 'sio worker process'
    options = WorkerOptions

    def makeService(self, options):
        return internet.TCPClient(options['host'], options['port'],
                WorkerFactory(
                    concurrency=options['concurrency'],
                    # Twisted argument parser set this to 0 or 1.
                    can_run_cpu_exec=bool(options['can-run-cpu-exec']),
                    name=options['name']))


class ServerOptions(usage.Options):
    optParameters = [
        ['worker-listen', 'w', '', "workers listen address"],
        ['worker-port', '', 7888, "workers port number"],
        ['rpc-listen', 'r', '', "RPC listen address"],
        ['rpc-port', '', 7889, "RPC listen port"],
        ['database', 'db', 'sioworkersd.db', "database file path"],
        ['scheduler', 's', getDefaultSchedulerClassName(),
             "scheduler class"],
    ]


@zope.interface.implementer(service.IServiceMaker, IPlugin)
class ServerServiceMaker(object):
    tapname = 'sioworkersd'
    description = 'workers and jobs execution manager'
    options = ServerOptions

    def makeService(self, options):
        # root service, leaf in the tree of dependency
        workerm = WorkerManager()

        sched_module, sched_class = options['scheduler'].rsplit('.', 1)
        try:
            SchedulerClass = \
                getattr(importlib.import_module(sched_module), sched_class)
        except ImportError:
            print("[ERROR] Invalid scheduler module: " + sched_module + "\n")
            raise
        except AttributeError:
            print("[ERROR] Invalid scheduler class: " + sched_class + "\n")
            raise

        taskm = TaskManager(options['database'], workerm,
                            SchedulerClass(workerm))
        taskm.setServiceParent(workerm)

        rpc = siorpc.makeSite(workerm, taskm)
        internet.TCPServer(int(options['rpc-port']), rpc,
                interface=options['rpc-listen']).setServiceParent(workerm)

        internet.TCPServer(int(options['worker-port']), workerm.makeFactory(),
                interface=options['worker-listen']).setServiceParent(workerm)

        return workerm


workerMaker = WorkerServiceMaker()

serverMaker = ServerServiceMaker()
