#!/bin/bash

help() {
cat << EOF
Usage: $0 [option] command
Helps managing supervisor with configuration in this script. The only way to
reload configuration is to restart supervisor with this script.

Options:
  -h, --help    display this help

Commands:
  start         starts supervisor
  startfg       starts supervisor in foreground
  stop          stops supervisor
  restart       restart supervisor
  status        shows status of daemons that supervisor run
  shell         run supervisorctl's shell
EOF
}

command=
while [ -n "$1" ]; do
    case "$1" in
        "-h"|"--help")
            help
            exit 0
            ;;
        "start"|"startfg"|"stop"|"restart"|"status"|"shell")
            command="$1"
            ;;
        *)
            echo "Unknown option: $1"
            help
            exit 1
            ;;
    esac
    shift
done

if [ -z "$command" ]; then
    help
    exit 1
fi

# Set CWD to directory with config.
cd "$(dirname "$BASH_SOURCE")/config"

if ! [ -e supervisord.conf ] || \
   ! [ -e supervisord-conf-vars.conf ]; then
    echo "Please make sure that supervisord.conf and " \
         "supervisord-conf-vars.conf exist in config/ directory!"
    echo "You can copy example configs that resides in config/ directory."
    exit 1
fi

# Activate venv:
if [ -d "../../venv" ]
then
    source ../../venv/bin/activate
fi

# Set all config variables.
source supervisord-conf-vars.conf

# Set extra flags, currently there is a need only for --can-run-cpu-exec flag.
if [ "$WORKER_ALLOW_RUN_CPU_EXEC" == "true" ]; then
    export WORKER_EXTRA_FLAGS="--can-run-cpu-exec"
else
    export WORKER_EXTRA_FLAGS=""
fi

# Create necessary directories.
mkdir -pv "${WORKER_HOME}"/{logs,pidfiles}

# And run supervisor.*
case "$command" in
    "start")
        exec supervisord
        ;;
    "startfg")
        exec supervisord -n
        ;;
    "stop")
        exec supervisorctl shutdown
        ;;
    "restart")
        supervisorctl shutdown
        exec supervisord
        ;;
    "status")
        exec supervisorctl status
        ;;
    "shell")
        echo "Caution: In order to reload config, run \`$0 restart\`"
        exec supervisorctl
        ;;
esac