from os import getgid, getuid, seteuid, setegid, getcwd
from sys import argv, exc_info, exit, stdout
from subprocess import call, Popen, PIPE
import traceback
import datetime
import logging


log_level = logging.INFO
proc_log = logging.getLogger()
proc_log= logging.basicConfig(
    level=log_level,
    format='%(levelname)s (%(threadName)-9s) %(message)s',
)

def exac(exec_opts, secret=False, **kwargs):
    '''
        Execute action into a subprocess

        :param exec_opts: Command to execute (See example exec_opts)
        :type exec_opts: String || List of Strings
        :example exec_opts: ["ls", "/tmp", "-l"]
                            || "ls /tmp -l"(only if shell=True)
                                See example kwargs for shell=True

        :param secret: If the command has sensitive info, hide the command from stdout/stderr
        :type secret: Bool True/False
        :example secret: NA

        :param kwargs: Here you can pass additional arguments to subprosses.Popen
        :param kwargs: key=value pairs
        :example kwargs: shell=True
    '''

    def die(errdict, err):
        errdict["stderr"] = err
        errdict["ExecTime"] = datetime.datetime.now() - errdict["startDatetime"]
        errdict["ExitCode"] = 1

        return errdict

    # Stats to be returned for this specific command
    exacval = {
        "ExitCode": -1,
        "stderr": u"",
        "stdout": u"",
        "ExecTime": datetime.timedelta(0),
        "Command": None,
        "PID": None,
    }
    exacval["startDatetime"] = datetime.datetime.now()
    exacval["shell"] = kwargs.get(
        "shell",
        False
    )

    # Check the executing mode type: shell=True/False?
    if exacval.get("shell") == False:
        try:
            assert isinstance(exec_opts, list)
        except AssertionError:
            return die(
                exacval,
                "You have set shell=False but exec_opts is not a list."
            )

        cmd = " ".join(exec_opts)
    elif exacval.get("shell") == True:
        if isinstance(exec_opts, list):
            return die(
                exacval,
                "Erro setting shell=True however command provided was not a string but a list"
            )
        else:
            cmd = exec_opts
    elif exacval.get("shell") not in [True, False]:
        return die(
            exacval,
            "Erro setting shell=%s. Acceptable values are True/False" % exacval.get("shell")
        )

    # Verify that a command has been issued
    assert len(exec_opts) > 0

    if secret == True:
        exacval["Command"] = "***"
        cmd = "***"
    else:
        exacval["Command"] = exec_opts

    logging.info(
        "::exac > At %s, executing \"%s\"" % (
            exacval["startDatetime"],
            cmd
        )
    )

    exacval["cwd"] = kwargs.get("cwd", getcwd())
    exacval["user"] = kwargs.get("user", getuid())

    try:
        prc = Popen(
            exec_opts,
            stdin=None,
            stdout=PIPE,
            stderr=PIPE,
            shell=exacval['shell']
        )

        exacval["PID"] = prc.pid
        logging.debug(
            "::exac > Command \"%s\" got pid %s" % (
                cmd,
                prc.pid
            )
        )
        logging.debug("::exac > Wating for command: %s" % cmd)

        exacval['stderr'] = b''
        exacval['stdout'] = b''

        while True:
            try:
                std = prc.communicate()
                exacval["stdout"], exacval["stderr"] = std[0], std[1]
                break
            except Exception as e:
                trace_message = "::exac > Got %s %s when trying to get stdout/stderr outputs of %s. Showing traceback:\n%s" % (
                    type(e),
                    e,
                    cmd,
                    traceback.format_exc()
                )
                return die(
                    exacval,
                    trace_message
                )

        prc.wait()
        exacval["ExitCode"] = prc.returncode
        exacval["ExecTime"] = datetime.datetime.now() - exacval["startDatetime"]

        prc.stdout.close()
        prc.stderr.close()
        prc.terminate()
        rt = exacval["ExitCode"]

        return exacval

    except FileNotFoundError:
        return die(
            exacval,
            "Command: {} is not available in your system".format(exec_opts[0])
        )
