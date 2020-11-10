#!/bin/env python2.7
'''
Backup Utility

The (hopefully) not-so-garbage configurable backup utility.
'''


# ------- Python Library Imports -------

# Standard Library
import argparse
import datetime
import getpass
import glob
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import time

# Additional Dependencies
try:
    import yaml
except ImportError as e:
    sys.exit('Unable to import PyYAML library - ' + str(e) + '.')

# Custom Modules
try:
    import emails
except ImportError as e:
    sys.exit('Unable to import email definitions - ' + str(e) + '.')
    
# --------------------------------------



# ----------- Initialization -----------

HELP_DESCRIPTION = """
The (hopefully) not-so-garbage configurable backup utility.
"""

HELP_EPILOG = """
"""

# Color Sequences
C_BLUE   = '\033[94m'
C_GREEN  = '\033[92m'
C_ORANGE = '\033[93m'
C_RED    = '\033[91m'
C_END    = '\033[0m'
C_BOLD   = '\033[1m'

# --------------------------------------



# ---------- Private Functions ---------

def _c(instring, color=C_BLUE):
    '''
    Colorizes the specified string.
    '''
    if args.color_output and not color is None:
        return color + instring + C_END
    else:
        return instring


def _parse_arguments():
    '''
    Parses the command-line arguments into a global namespace called "args".
    '''
    if not os.getenv('BACKUPUTIL_CP_INTERVAL', '600').isdigit():
        sys.exit('Invalid value set for environment variable "BACKUPUTIL_CP_INTERVAL".')
    if not os.getenv('BACKUPUTIL_EMAIL_LVL', 'never') in ['never', 'error', 'warning', 'completion']:
        sys.exit('Invalid value set for environment variable "BACKUPUTIL_EMAIL_LVL".')
    if not os.getenv('BACKUPUTIL_LOG_LVL', 'info') in ['info', 'debug']:
        sys.exit('Invalid value set for environment variable "BACKUPUTIL_LOG_LVL".')
    if not os.getenv('BACKUPUTIL_LOG_MODE', 'append') in ['append', 'overwrite']:
        sys.exit('Invalid value set for environment variable "BACKUPUTIL_LOG_MODE".')
    if not os.getenv('BACKUPUTIL_RATE_LIMIT', '0').isdigit():
        sys.exit('Invalid value set for environment variable "BACKUPUTIL_RATE_LIMIT".')
    argparser = argparse.ArgumentParser(
        description = HELP_DESCRIPTION,
        epilog = HELP_EPILOG,
        usage = 'backuputil [-c FILE] (TARGET | --list-targets) [...]',
        add_help = False,
        formatter_class = lambda prog: argparse.RawDescriptionHelpFormatter(prog, max_help_position=45, width=100)
    )
    if not '--list-targets' in sys.argv:
        argparser.add_argument(
            'target',
            help = 'Specifies target specification to execute within the parsed configuration file.'
        )
    argparser.add_argument(
        '-b',
        '--borg-executable',
        default = os.getenv('BACKUPUTIL_BORG_PATH', '/usr/bin/borg'),
        dest = 'borg_executable',
        help = '[env: BACKUPUTIL_BORG_PATH] Specifies the path to the Borg Backup executable binary. Defaults to "/usr/bin/borg".',
        metavar = 'FILE'
    )
    argparser.add_argument(
        '--cert-path',
        default = os.getenv('BACKUPUTIL_CERT_PATH', os.path.expanduser('~/.ssh/backuputil.pem')),
        dest = 'cert_path',
        help = '[env: BACKUPUTIL_CERT_PATH] Specifies the path to the default certificate file to use for remote backups. Defaults to "~/.ssh/backuputil.pem".',
        metavar = 'FILE'
    )
    argparser.add_argument(
        '-C',
        '--checkpoint-int',
        default = int(os.getenv('BACKUPUTIL_CP_INTERVAL', '900')),
        dest = 'checkpoint_interval',
        help = '[env: BACKUPUTIL_CP_INTERVAL] Specifies the time interval (in seconds) in which the underlying Borg subprocess will write checkpoints. Defaults to 900 seconds.',
        metavar = 'SEC',
        type = int
    )
    argparser.add_argument(
        '-c',
        '--config-file',
        default = os.getenv('BACKUPUTIL_CONFIG_FILE', '/etc/backuputil.yaml'),
        dest = 'config_file',
        help = '[env: BACKUPUTIL_CONFIG_FILE] Specifies the configuration file to load target definitions from. Defaults to "/etc/backuputil.yaml".',
        metavar = 'FILE'
    )
    argparser.add_argument(
        '-d',
        '--dry-run',
        action = 'store_true',
        dest = 'dry_run',
        help = 'Specifies that the script should only execute a dry-run, preventing any files from actually being backed-up.'
    )
    argparser.add_argument(
        '-e',
        '--email-level',
        choices = ['never', 'error', 'warning', 'completion'],
        default = os.getenv('BACKUPUTIL_EMAIL_LVL', 'never'),
        dest = 'email_level',
        help = '[env: BACKUPUTIL_EMAIL_LVL] Specifies the condition at which the script should send an email, being "never", "error", "warning", or "completion". Defaults to "never".',
        metavar = 'LVL'
    )
    argparser.add_argument(
        '-t',
        '--email-to',
        default = os.getenv('BACKUPUTIL_EMAIL_TO', ''),
        dest = 'email_to',
        help = '[env: BACKUPUTIL_EMAIL_TO] Specifies the email address to receive sent emails. This option is ignored if "-e" is not specified or set to "never".',
        metavar = 'EMAIL'
    )
    argparser.add_argument(
        '--force-prune',
        action = 'store_true',
        dest = 'force_prune',
        help = 'Specifies that the script should force the deletion of corrupted archives during the pruning process.'
    )
    argparser.add_argument(
        '-h',
        '--help',
        action = 'help',
        help = 'Displays help and usage information.'
    )
    argparser.add_argument(
        '-i',
        '--info',
        action = 'store_true',
        dest = 'info',
        help = 'Displays information regarding the repository relevant to the specified target (instead of performing a back-up).'
    )
    argparser.add_argument(
        '--list-archives',
        action = 'store_true',
        dest = 'list_archives',
        help = 'Lists all existing archives (backups) in the repository relevant to the specified target (instead of performing a back-up).'
    )
    argparser.add_argument(
        '--list-targets',
        action = 'store_true',
        dest = 'list_targets',
        help = 'Lists all of the available targets in the specified configuration file.'
    )
    argparser.add_argument(
        '-f',
        '--log-file',
        default = os.getenv('BACKUPUTIL_LOG_FILE', '/var/log/backuputil.log'),
        dest = 'log_file',
        help = '[env: BACKUPUTIL_LOG_FILE] Specifies the log file to write to. Defaults to "/var/log/backuputil.log".',
        metavar = 'FILE'
    )
    argparser.add_argument(
        '-l',
        '--log-level',
        choices = ['info', 'debug'],
        default = os.getenv('BACKUPUTIL_LOG_LVL', 'info'),
        dest = 'log_level',
        help = '[env: BACKUPUTIL_LOG_LVL] Specifies the log level of the script, being either "info" or "debug". Defaults to "info".',
        metavar = 'LVL'
    )
    argparser.add_argument(
        '-m',
        '--log-mode',
        choices = ['append', 'overwrite'],
        default = os.getenv('BACKUPUTIL_LOG_MODE', 'append'),
        dest = 'log_mode',
        help = '[env: BACKUPUTIL_LOG_MODE] Specifies whether to "append" or "overwrite" the specified log file. Defaults to "append".',
        metavar = 'MODE'
    )
    argparser.add_argument(
        '--no-color',
        action = 'store_false',
        dest = 'color_output',
        help = 'Disables color output to stdout/stderr.'
    )
    argparser.add_argument(
        '-p',
        '--password',
        default = os.getenv('BACKUPUTIL_PASSWORD', ''),
        dest = 'password',
        help = '[env: BACKUPUTIL_PASSWORD] Specifies the default password string to use when authenticating with destination repositories.',
        metavar = 'STR'
    ) 
    argparser.add_argument(
        '--post-run',
        default = os.getenv('BACKUPUTIL_POST_RUN', ''),
        dest = 'post_run',
        help = '[env: BACKUPUTIL_POST_RUN] Specifies the default commmand to run after a backup process has completed.',
        metavar = 'CMD'
    )
    argparser.add_argument(
        '--pre-run',
        default = os.getenv('BACKUPUTIL_PRE_RUN', ''),
        dest = 'pre_run',
        help = '[env: BACKUPUTIL_PRE_RUN] Specifies the default commmand to run before starting a backup process.',
        metavar = 'CMD'
    )
    argparser.add_argument(
        '-r',
        '--rate-limit',
        default = int(os.getenv('BACKUPUTIL_RATE_LIMIT', '0')),
        dest = 'rate_limit',
        help = '[env: BACKUPUTIL_RATE_LIMIT] Specifies the default rate limit to use (in KiB/s) in transfers to remote servers. Defaults to "0" (unlimited).',
        metavar = 'INT',
        type = int
    )
    argparser.add_argument(
        '--repair',
        action = 'store_true',
        dest = 'repair',
        help = 'Attempts to repair any issues pertaining to archive or repository integrity (instead of performing a new backup). It is recommended to run the script with "--verify-integrity" first to determine the severity of any data corruption.'
    )
    argparser.add_argument(
        '--restore',
        default = '',
        dest = 'restore',
        help = 'Restores the contents of an archive associated with the specified target into the path specified by "--restore-to".',
        metavar = 'ARCHIVE[:PATH]',
    )
    argparser.add_argument(
        '--restore-to',
        default = os.getcwd(),
        dest = 'restore_to',
        help = 'Specifies the destination path for "--restore". Defaults to the current working directory.',
        metavar = 'PATH',
    )
    argparser.add_argument(
        '-T',
        '--timestamp-fmt',
        default = os.getenv('BACKUPUTIL_TIMESTAMP', '%Y-%m-%d.%H-%M-%S'),
        dest = 'timestamp_format',
        help = '[env: BACKUPUTIL_TIMESTAMP] Specifies the format to use for generating timestamps via Python\'s "strftime()" method. Defaults to "%%Y-%%m-%%d.%%H-%%M-%%S".',
        metavar = 'STR'
    )
    argparser.add_argument(
        '--unlock',
        action = 'store_true',
        dest = 'unlock',
        help = 'Specifies that the script should unlock (break-lock) the repository associated with the specified backup target. This is used to recover from a failed run that results in an active repository lock. The script will not perform a new backup.'
    )
    argparser.add_argument(
        '-u',
        '--user',
        default = os.getenv('BACKUPUTIL_USER', getpass.getuser()),
        dest = 'user',
        help = '[env: BACKUPUTIL_USER] Specifies the default login user relative to the specified target server with which remote transfer connections are established. Defaults to the current user.',
        metavar = 'NAME'
    )
    argparser.add_argument(
        '-v',
        '--verify-integrity',
        action = 'store_true',
        dest = 'verify_integrity',
        help = 'Verifies the integrity of the repository (and any previous archives) associated with the specified target (instead of performing a new backup).'
    )
    global args
    args = argparser.parse_args()


def _run_process(cmd, splitlines=True):
    '''
    Runs the specified command as a subprocess, returning the output of the
    command (optionally not split by lines) and its exit code.
    '''
    process = subprocess.Popen(
        cmd,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
        shell = True
    )
    output = process.communicate()[0]
    exit_code = process.returncode
    if splitlines:
        return (output.splitlines(), exit_code)
    else:
        return (output, exit_code)


def _send_email(subject, body, level='error', debug=False):
    '''
    Sends an email to the configured recipients with the specified body, subject,
    and alert level. Whether the email actually gets sent is dependent on the
    alert level specified by "args.email_level".
    '''
    if not level in ['error', 'warning', 'info']:
        raise Exception('Invalid email level: "' + str(level) + '"')
    if args.email_level == 'never' or (args.email_level == 'error' and level in ['warning', 'info']) or (args.email_level == 'warning' and level == 'info'):
        return
    if level == 'error':
        full_subject = 'ERROR: ' + subject
        full_body = body + '\n\nSee "' + args.log_file + '" on the machine for more details.'
    elif level == 'warning':
        full_subject = 'WARNING: ' + subject
        full_body = body + '\n\nSee "' + args.log_file + '" on the machine for more details.'
    else:
        full_subject = subject
        full_body = body
    with open('/tmp/backuputil.email', 'w') as f:
        f.write('To: ' + args.email_to + '\n')
        f.write('Subject: ' + full_subject + '\n\n')
        f.write(full_body)
    with open(os.devnull, 'w') as DEVNULL:
        email_exit_code = subprocess.call('cat /tmp/backuputil.email | /usr/sbin/sendmail -t', shell=True, stdout=DEVNULL, stderr=subprocess.STDOUT)
    if email_exit_code != 0:
        raise Exception('sendmail subprocess call returned non-zero exit code')


def _setup_logging():
    '''
    Sets-up logging.
    '''
    if args.log_file:
        try:
            if args.log_mode == 'append':
                logging_fmode = 'a'
            else:
                logging_fmode = 'w'
            if args.log_level == 'info':
                logging_level = logging.INFO
            else:
                logging_level = logging.DEBUG
            logging.basicConfig(
                filename = args.log_file,
                filemode = logging_fmode,
                level    = logging_level,
                format   = '[%(levelname)s] [%(asctime)s] [%(process)d] %(message)s',
                datefmt  = '%m/%d/%Y %I:%M:%S %p'
            )
            logging.addLevelName(logging.CRITICAL, 'CRI')
            logging.addLevelName(logging.ERROR, 'ERR')
            logging.addLevelName(logging.WARNING, 'WAR')
            logging.addLevelName(logging.INFO, 'INF')
            logging.addLevelName(logging.DEBUG, 'DEB')
        except Exception as e:
            sys.exit('Unable to initialize logging system - ' + str(e) + '.')
    else:
        logger = logging.getLogger()
        logger.disabled = True


def _step(instring, color=C_BLUE):
    '''
    Formats the specified string as a "step".
    '''
    return _c('::', color) + ' ' + _c(instring, C_BOLD)


def _substep(instring, color=C_BLUE):
    '''
    Formats the specified string as a "sub-step".
    '''
    return '  ' + _c('-->', color) + ' ' + instring


def _subsubstep(instring, color=None):
    '''
    Formats the specified string as a "sub-sub-step".
    '''
    return '      ' + _c(instring, color)


# --------------------------------------



# ---------- Public Functions ----------

def get_hostname():
    '''
    Obtains the hostname of the machine.
    '''
    logging.debug('Getting hostname and FQDN...')
    try:
        global hostname
        hostname = socket.gethostname().split('.', 1)[0]
        global fqdn
        fqdn = socket.getfqdn()
    except Exception as e:
        logging.critical('Unable to discern hostname - ' + str(e) + '.')
        sys.exit(1)
    logging.debug('Hostname: ' + hostname)
    logging.debug('FQDN: ' + fqdn)


def handle_backup():
    '''
    Handles the main backup/pruning process.
    '''
    if args.dry_run:
        print(_step('Executing ' + args.target + ' (DRY RUN)...'))
        logging.info('Executing ' + args.target + ' (DRY RUN)...')
    else:
        print(_step('Executing ' + args.target + '...'))
        logging.info('Executing ' + args.target + '...')
    prepare_execution()
    global backup_output
    backup_output = ''
    global prune_output
    prune_output = ''
    timestamp = datetime.datetime.now().strftime(args.timestamp_format)
    logging.debug('Timestamp: ' + timestamp)
    if args.log_level == 'debug':
        common_options = '--debug'
    else:
        common_options = '--info'
    logging.debug('Common Subprocess CLI Options: ' + common_options)
    if args.dry_run:
        additional_create_options = '--dry-run'
    else:
        additional_create_options = '--stats'
    if args.log_level == 'debug': additional_create_options += ' --list'
    logging.debug('Additional Borg "create" Options: ' + additional_create_options)
    archive_str = '{repo_str}::{timestamp}'.format(
        repo_str = repo_str,
        timestamp = timestamp
    )
    create_options = additional_create_options
    if exclude_paths:
        for e in exclude_paths:
            create_options += " --exclude '" + e + "'"
    create_options += ' --checkpoint-interval ' + str(args.checkpoint_interval)
    borg_create_cmd = '{borg} {common_options} --remote-ratelimit {rate_limit} create {create_options} {archive} {paths}'.format(
        borg = args.borg_executable,
        common_options = common_options,
        rate_limit = rate_limit,
        create_options = create_options,
        archive = archive_str,
        paths = ' '.join(src_paths)
    )
    logging.debug('Borg Backup Command: ' + borg_create_cmd)
    if dst_srv:
        logging.info('Verifying remote repository...')
        print(_substep('Verifying remote repository...'))
    else:
        logging.info('Verifying local repository...')
        print(_substep('Verifying local repository...'))
    borg_info_cmd = '{borg} {common_options} info {repo_str}'.format(
        borg = args.borg_executable,
        common_options = common_options,
        repo_str = repo_str
    )
    try:
        (info_out, info_ec) = _run_process(borg_info_cmd)
    except Exception as e:
        printe(_subsubstep('Unable to verify repository - ' + str(e) + '.', C_RED))
        logging.critical('Unable to verify repository - ' + str(e) + '.')
        send_email(
            'Unable to verify repository',
            emails.INFO_EXCEPTION,
            'error'
        )
        sys.exit(4)
    logging.debug('INFO EXIT CODE: ' + str(info_ec))
    if info_ec == 1:
        if info_out:
            for l in info_out:
                logging.warning('INFO OUTPUT: ' + l)
        printe(_subsubstep('Warning: Repository verification subprocess returned warning-level exit code.', C_ORANGE))
        logging.warning('Repository verification subprocess returned warning-level exit code.')
        send_email(
            'Repository verification subproces returned warning-level exit code',
            emails.INFO_WARN,
            'warning'
        )
    elif info_ec > 1:
        if info_out:
            for l in info_out:
                logging.critical('INFO OUTPUT: ' + l)
        printe(_subsubstep('Unable to verify repository - subprocess returned error-level exit code.', C_RED))
        printe(_subsubstep('Make sure the destination repository was created via "borg init" prior to running the script.', C_RED))
        logging.critical('Unable to verify repository - subprocess returned error-level exit code.')
        send_email(
            'UUnable to verify repository',
            emails.INFO_ERR,
            'error'
        )
        sys.exit(4)
    else:
        if info_out:
            for l in info_out:
                logging.debug('INFO OUTPUT: ' + l)
    if pre_run and not args.dry_run:
        logging.info('Executing pre-run command "' + pre_run + '"...')
        print(_substep(pre_run))
        try:
            (pre_out, pre_ec) = _run_process(pre_run)
        except Exception as e:  
            printe(_subsubstep('Unable to execute pre-run command - ' + str(e) + '.', C_RED))
            logging.critical('Unable to execute pre-run command - ' + str(e) + '.')
            send_email(
                'Unable to execute pre-run command',
                emails.PRE_RUN_EXCEPTION,
                'error'
            )
            sys.exit(4)
        logging.debug('PRE RUN EXIT CODE: ' + str(pre_ec))
        if pre_ec != 0:
            if pre_out:
                for l in pre_out:
                    logging.critical('PRE RUN OUTPUT: ' + l)
            printe(_subsubstep('Unable to proceed - pre-run command returned non-zero exit code.', C_RED))
            logging.critical('Unable to proceed - pre-run command returned non-zero exit code.')
            send_email(
                'Specified pre-run command returned non-zero exit code',
                emails.PRE_RUN_EXIT,
                'error'
            )
            sys.exit(4)
        else:
            if pre_out:
                for l in pre_out:
                    logging.info('PRE RUN OUTPUT: ' + l)
    logging.info('Performing backup...')
    print(_substep('Performing backup...'))
    try:
        backup_process = subprocess.Popen(
            borg_create_cmd,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            shell = True
        )
        for line in iter(backup_process.stdout.readline, ''):
            backup_output += line
            logging.info('BACKUP OUTPUT: ' + line.rstrip())
        while backup_process.poll() is None: time.sleep(0.5)
        backup_exit_code = backup_process.returncode
        logging.debug('BACKUP EXIT CODE: ' + str(backup_exit_code))
    except Exception as e:
        printe(_subsubstep('Unable to perform backup - ' + str(e) + '.', C_RED))
        logging.critical('Unable to perform backup - ' + str(e) + '.')
        send_email(
            'Unable to perform backup',
            emails.BACKUP_EXCEPTION,
            'error'
        )
        sys.exit(4)
    if backup_exit_code == 1:
        printe(_subsubstep('Warning: backup subprocess returned warning-level exit code.', C_ORANGE))
        logging.warning('Backup subprocess returned warning-level exit code.')
        send_email(
            'Backup process completed with warnings',
            emails.BACKUP_WARN,
            'warning'
        )
    elif backup_exit_code > 1:
        printe(_subsubstep('Unable to perform backup - subprocess returned error-level exit code.', C_RED))
        logging.critical('Unable to perform backup - subprocess returned error-level exit code.')
        send_email(
            'Unable to perform backup',
            emails.BACKUP_ERR,
            'error'
        )
        sys.exit(4)
    if not keep: return
    logging.info('Pruning old backups...')
    print(_substep('Pruning old backups...'))
    if args.dry_run:
        prune_options = '--dry-run'
    else:
        prune_options = '--stats'
    if args.force_prune: prune_options += ' --force'
    if args.log_level == 'debug': prune_options += ' --list'
    keep_str = ''
    if 'hourly' in keep: keep_str += ' --keep-hourly ' + str(keep['hourly'])
    if 'daily' in keep: keep_str += ' --keep-daily ' + str(keep['daily'])
    if 'weekly' in keep: keep_str += ' --keep-weekly ' + str(keep['weekly'])
    if 'monthly' in keep: keep_str += ' --keep-monthly ' + str(keep['monthly'])
    if 'yearly' in keep: keep_str += ' --keep-yearly ' + str(keep['yearly'])
    keep_str.lstrip(' ')
    borg_prune_cmd = '{borg} {common_options} prune {prune_options} {keep} {repo_str}'.format(
        borg = args.borg_executable,
        common_options = common_options,
        prune_options = prune_options,
        keep = keep_str,
        repo_str = repo_str
    )
    logging.debug('Borg Prune Command: ' + borg_prune_cmd)
    try:
        prune_process = subprocess.Popen(
            borg_prune_cmd,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            shell = True
        )
        for line in iter(prune_process.stdout.readline, ''):
            prune_output += line
            logging.info('PRUNE OUTPUT: ' + line.rstrip())
        while prune_process.poll() is None: time.sleep(0.5)
        prune_exit_code = prune_process.returncode
        logging.debug('PRUNE EXIT CODE: ' + str(prune_exit_code))
    except Exception as e:
        printe(_subsubstep('Unable to prune old backups - ' + str(e) + '.', C_RED))
        logging.critical('Unable to prune old backups - ' + str(e) + '.')
        send_email(
            'Unable to prune old backups',
            emails.PRUNE_EXCEPTION,
            'error'
        )
        sys.exit(5)
    if prune_exit_code == 1:
        printe(_subsubstep('Warning: prune subprocess returned warning-level exit code.', C_ORANGE))
        logging.warning('Prune subprocess returned warning-level exit code.')
        send_email(
            'Backup process completed with warnings',
            emails.PRUNE_WARN,
            'warning'
        )
    elif prune_exit_code > 1:
        printe(_subsubstep('Unable to prune old backups - subprocess returned error-level exit code.', C_RED))
        logging.critical('Unable to prune old backups - subprocess returned error-level exit code.')
        send_email(
            'Unable to prune old backups',
            emails.PRUNE_ERR,
            'error'
        )
        sys.exit(5)
    if post_run and not args.dry_run:
        logging.info('Executing post-run command "' + post_run + '"...')
        print(_substep(post_run))
        try:
            (post_out, post_ec) = _run_process(post_run)
        except Exception as e:  
            printe(_subsubstep('Unable to execute post-run command - ' + str(e) + '.', C_RED))
            logging.critical('Unable to execute post-run command - ' + str(e) + '.')
            send_email(
                'Unable to execute post-run command',
                emails.POST_RUN_EXCEPTION,
                'error'
            )
            sys.exit(4)
        logging.debug('POST RUN EXIT CODE: ' + str(post_ec))
        if post_ec != 0:
            if post_out:
                for l in post_out:
                    logging.critical('POST RUN OUTPUT: ' + l)
            printe(_subsubstep('Unable to proceed - post-run command returned non-zero exit code.', C_RED))
            logging.critical('Unable to proceed - post-run command returned non-zero exit code.')
            send_email(
                'Specified post-run command returned non-zero exit code',
                emails.POST_RUN_EXIT,
                'error'
            )
            sys.exit(4)
        else:
            if post_out:
                for l in post_out:
                    logging.info('POST RUN OUTPUT: ' + l)
    


def handle_info():
    '''
    Handles the "--info" flag.

    Note that this function will call "sys.exit()" on its own.
    '''
    if 'dst_srv' in target:
        print(_step('Getting remote repository information...'))
        logging.info('Getting remote repository information...')
    else:
        print(_step('Getting local repository information...'))
        logging.info('Getting local repository information...')
    prepare_execution()
    print(_substep('Getting info...'))
    logging.debug('Getting info...')
    borg_info_cmd = '{borg} info {repo_str}'.format(
        borg = args.borg_executable,
        repo_str = repo_str
    )
    try:
        (info_out, info_ec) = _run_process(borg_info_cmd)
    except Exception as e:
        printe(_subsubstep('Unable to obtain info - ' + str(e) + '.', C_RED))
        logging.critical('Unable to obtain info - ' + str(e) + '.')
        sys.exit(8)
    logging.debug('INFO EXIT CODE: ' + str(info_ec))
    if info_ec == 1:
        if info_out:
            for l in info_out:
                printe(_subsubstep(l))
                logging.warning('INFO OUTPUT: ' + l)
        printe(_subsubstep('Warning: subprocess returned warning-level exit code.', C_ORANGE))
        logging.warning('Subprocess returned warning-level exit code.')
    elif info_ec > 1:
        if info_out:
            for l in info_out:
                printe(_subsubstep(l))
                logging.critical('INFO OUTPUT: ' + l)
        printe(_subsubstep('Error: subprocess returned error-level exit code.', C_RED))
        logging.critical('Subprocess returned error-level exit code.')
        sys.exit(8)
    else:
        if info_out:
            for l in info_out:
                print(_subsubstep(l))
                logging.info('INFO OUTPUT: ' + l)
    logging.info('Process complete.')
    sys.exit(0)


def handle_list_archives():
    '''
    Handles the "--list-archives" flag.

    Note that this function will call "sys.exit()" on its own.
    '''
    if 'dst_srv' in target:
        print(_step('Listing remote repository archives...'))
        logging.info('Listing remote repository archives...')
    else:
        print(_step('Listing local repository archives...'))
        logging.info('Listing local repository archives...')
    prepare_execution()
    print(_substep('Getting archive list...'))
    logging.debug('Getting archive list...')
    borg_list_cmd = '{borg} list --short {repo_str}'.format(
        borg = args.borg_executable,
        repo_str = repo_str
    )
    try:
        (list_out, list_ec) = _run_process(borg_list_cmd)
    except Exception as e:
        printe(_subsubstep('Unable to obtain archive list - ' + str(e) + '.', C_RED))
        logging.critical('Unable to obtain archive list - ' + str(e) + '.')
        sys.exit(9)
    logging.debug('LIST EXIT CODE: ' + str(list_ec))
    if list_ec == 1:
        if list_out:
            for l in list_out:
                printe(_subsubstep(l))
                logging.warning('LIST OUTPUT: ' + l)
        printe(_subsubstep('Warning: subprocess returned warning-level exit code.', C_ORANGE))
        logging.warning('Subprocess returned warning-level exit code.')
    elif list_ec > 1:
        if list_out:
            for l in list_out:
                printe(_subsubstep(l))
                logging.critical('LIST OUTPUT: ' + l)
        printe(_subsubstep('Error: subprocess returned error-level exit code.', C_RED))
        logging.critical('Subprocess returned error-level exit code.')
        sys.exit(9)
    else:
        if list_out:
            for l in list_out:
                print(_subsubstep(l))
                logging.info('LIST OUTPUT: ' + l)
    logging.info('Process complete.')
    sys.exit(0)


def handle_list_targets():
    '''
    Handles the "--list-targets" flag.

    Note that this flag will simply return a non-zero exit code if there is an
    issue. The only output will be the list of targets.
    '''
    try:
        with open(args.config_file, 'r') as f:
            targets = [t for t in yaml.safe_load(f.read())['targets']]
        for target in targets: print(target)
    except Exception as e: sys.exit(1)
    sys.exit(0)


def handle_repair():
    '''
    Handles the "--repair" flag.

    Note that this function will call "sys.exit()" on its own.
    '''
    EC = 9
    if 'dst_srv' in target:
        print(_step('Repairing remote repository...'))
        logging.info('Repairing remote repository...')
    else:
        print(_step('Repairing local repository...'))
        logging.info('Repairing local repository...')
    prepare_execution()
    if args.log_level == 'debug':
        common_options = '--debug'
    else:
        common_options = '--info'
    print(_substep('Repairing repository...'))
    logging.debug('Repairing repository...')
    try:
        repair_ec = os.system(
            '{borg} {common_options} check --repair {repo}'.format(
                borg = args.borg_executable,
                common_options = common_options,
                repo = repo_str
            )
        )
    except Exception as e:
        printe(_subsubstep('Unable to repair repository - ' + str(e) + '.', C_RED))
        logging.critical('Unable to repair repository - ' + str(e) + '.')
        sys.exit(EC)
    logging.debug('REPAIR EXIT CODE: ' + str(repair_ec))
    if repair_ec == 1:
        printe(_subsubstep('Warning: Repository integrity repair returned warning-level exit code.', C_ORANGE))
        logging.warning('Repository integrity repair returned warning-level exit code.')
    elif repair_ec > 1:
        printe(_subsubstep('Repository integrity repair returned error-level exit code.', C_RED))
        logging.critical('Repository integrity repair returned error-level exit code.')
        sys.exit(EC)
    logging.info('Process complete.')
    sys.exit(0)
    


def handle_restore():
    '''
    Handles the "--restore" flag.

    Note that this function will call "sys.exit()" on its own.
    '''
    if 'dst_srv' in target:
        print(_step('Restoring from remote archive...'))
        logging.info('Restoring from remote archive...')
    else:
        print(_step('Restoring from local archive...'))
        logging.info('Restoring from local archive...')
    prepare_execution()
    print(_substep('Preparing restoration...'))
    logging.debug('Preparing restoration...')
    if ':' in args.restore:
        split_args_restore = args.restore.rsplit(':', 1)
        restore_archive = split_args_restore[0]
        logging.debug('Restore Archive: ' + restore_archive)
        restore_path = split_args_restore[1].lstrip('/')
        logging.debug('Restore Path: ' + restore_path)
    else:
        restore_archive = args.restore
        logging.debug('Restore Archive: ' + restore_archive)
        restore_path = ''
        logging.debug('Restore Path: NONE')
    if args.log_level == 'debug':
        common_args = '--debug'
        extra_args = '--list'
    else:
        common_args = '--info'
        extra_args = ''
    if os.path.isfile(args.restore_to):
        printe(_subsubstep('Specified restoration destination is an existing file...', C_RED))
        logging.critical('Specified restoration destination is an existing file...')
        sys.exit(6)
    if args.restore_to.endswith('.tar.gz') or args.restore_to.endswith('.tar.bz2') or args.restore_to.endswith('.tar.xz'):
        borg_cmd = '{borg} {common_args} export-tar {extra_args} {repo_str}::{archive} {restore_to}'.format(
            borg = args.borg_executable,
            common_args = common_args,
            extra_args = extra_args,
            repo_str = repo_str,
            archive = restore_archive,
            restore_to = args.restore_to
        )
        if restore_path: borg_cmd += ' ' + restore_path
        cwd = ''
    else:
        borg_cmd = '{borg} {common_args} extract {extra_args} {repo_str}::{archive}'.format(
            borg = args.borg_executable,
            common_args = common_args,
            extra_args = extra_args,
            repo_str = repo_str,
            archive = restore_archive
        )
        if restore_path: borg_cmd += ' ' + restore_path
        cwd = os.getcwd()
        logging.debug('Switching working directories...')
        try:
            if not os.path.isdir(args.restore_to):
                os.makedirs(args.restore_to)
            os.chdir(args.restore_to)
        except Exception as e:
            printe(_subsubstep('Unable to prepare restoration - unable to switch working directories - ' + str(e) + '.', C_RED))
            logging.critical('Unable to prepare restoration - unable to switch working directories - ' + str(e) + '.')
            sys.exit(6)
    logging.debug('RESTORATION COMMAND: ' + borg_cmd)
    logging.info('Restoring files...')
    print(_substep('Restoring files...'))
    try:
        restore_process = subprocess.Popen(
            borg_cmd,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            shell = True
        )
        for line in iter(restore_process.stdout.readline, ''):
            logging.info('RESTORE OUTPUT: ' + line.rstrip())
        while restore_process.poll() is None: time.sleep(0.5)
        restore_exit_code = restore_process.returncode
        logging.debug('RESTORE EXIT CODE: ' + str(restore_exit_code))
    except Exception as e:
        printe(_subsubstep('Unable to restore files - ' + str(e) + '.', C_RED))
        logging.critical('Unable to restore files - ' + str(e) + '.')
        sys.exit(6)
    if restore_exit_code == 1:
        printe(_subsubstep('Warning: restoration subprocess returned warning-level exit code.', C_ORANGE))
        logging.warning('Restoration subprocess returned warning-level exit code.')
    elif restore_exit_code > 1:
        printe(_subsubstep('Unable to restore files - subprocess returned error-level exit code.', C_RED))
        logging.critical('Unable to restore files - subprocess returned error-level exit code.')
        sys.exit(6)
    if cwd:
        print(_substep('Finalizing restoration...'))
        logging.debug('Finalizing restoration...')
        logging.debug('Reverting working directory...')
        try:
            os.chdir(cwd)
        except Exception as e:
            printe(_subsubstep('Unable to finalize restoration - unable to revert working directories - ' + str(e) + '.', C_RED))
            logging.critical('Unable to finalize restoration - unable to revert working directories - ' + str(e) + '.')
            sys.exit(6)
    logging.info('Process complete.')
    sys.exit(0)


def handle_unlock():
    '''
    Handles the "--unlock" flag.

    Note that this function will call "sys.exit()" on its own.
    '''
    EC = 10
    if 'dst_srv' in target:
        print(_step('Unlocking remote repository...'))
        logging.info('Unlocking remote repository...')
    else:
        print(_step('Unlocking local repository...'))
        logging.info('Unlocking local repository...')
    prepare_execution()
    if args.log_level == 'debug':
        common_options = '--debug'
    else:
        common_options = '--info'
    print(_substep('Unlocking repository...'))
    logging.debug('Unlocking repository...')
    try:
        (unlock_out, unlock_ec) = _run_process(
            '{borg} {common_options} break-lock {repo}'.format(
                borg = args.borg_executable,
                common_options = common_options,
                repo = repo_str
            )
        )
    except Exception as e:
        printe(_subsubstep('Unable to unlock repository - ' + str(e) + '.', C_RED))
        logging.critical('Unable to unlock repository - ' + str(e) + '.')
        sys.exit(EC)
    logging.debug('UNLOCK EXIT CODE: ' + str(unlock_ec))
    if unlock_ec == 1:
        for l in unlock_out:
            logging.warning('UNLOCK OUTPUT: ' + l)
            printe(_subsubstep(l))
        printe(_subsubstep('Warning: Repository unlock returned warning-level exit code.', C_ORANGE))
        logging.warning('Repository unlock returned warning-level exit code.')
    elif unlock_ec > 1:
        for l in unlock_out:
            logging.critical('UNLOCK OUTPUT: ' + l)
            printe(_subsubstep(l))
        printe(_subsubstep('Repository unlock returned error-level exit code.', C_RED))
        logging.critical('Repository unlock returned error-level exit code.')
        sys.exit(EC)
    else:
        for l in unlock_out:
            logging.info('UNLOCK OUTPUT: ' + l)
            print(_subsubstep(l))
    logging.info('Process complete.')
    sys.exit(0)


def handle_verify_integrity():
    '''
    Handles the "--verify-integrity" flag.

    Note that this function will call "sys.exit()" on its own.
    '''
    if 'dst_srv' in target:
        print(_step('Verifying remote repository integrity...'))
        logging.info('Verifying remote repository integrity...')
    else:
        print(_step('Verifying local repository integrity...'))
        logging.info('Verifying local repository integrity...')
    prepare_execution()
    if args.log_level == 'debug':
        common_options = '--debug'
    else:
        common_options = '--info'
    logging.debug('Setting subprocess environment variables...')
    print(_substep('Verifying repository integrity...'))
    logging.debug('Verifying repository integrity...')
    try:
        (repo_out, repo_ec) = _run_process(
            '{borg} {common_options} check --repository-only {repo}'.format(
                borg = args.borg_executable,
                common_options = common_options,
                repo = repo_str
            )
        )
    except Exception as e:
        printe(_subsubstep('Unable to verify repository integrity - ' + str(e) + '.', C_RED))
        logging.critical('Unable to verify repository integrity - ' + str(e) + '.')
        sys.exit(7)
    logging.debug('VERIFY REPO EXIT CODE: ' + str(repo_ec))
    if repo_ec == 1:
        if repo_out:
            for l in repo_out:
                logging.warning('VERIFY REPO OUTPUT: ' + l)
                printe(_subsubstep(l))
        printe(_subsubstep('Warning: Repository integrity check returned warning-level exit code.', C_ORANGE))
        logging.warning('Repository integrity check returned warning-level exit code.')
    elif repo_ec > 1:
        if repo_out:
            for l in repo_out:
                logging.critical('VERIFY REPO OUTPUT: ' + l)
                printe(_subsubstep(l))
        printe(_subsubstep('Repository integrity check returned error-level exit code.', C_RED))
        logging.critical('Repository integrity check returned error-level exit code.')
        sys.exit(7)
    else:
        if repo_out:
            for l in repo_out:
                logging.info('VERIFY REPO OUTPUT: ' + l)
                print(_subsubstep(l))
    print(_substep('Verifying archive integrity...'))
    logging.debug('Verifying archive integrity...')
    try:
        (arch_out, arch_ec) = _run_process(
            '{borg} {common_options} check --archives-only {repo}'.format(
                borg = args.borg_executable,
                common_options = common_options,
                repo = repo_str
            )
        )
    except Exception as e:
        printe(_subsubstep('Unable to verify archive integrity - ' + str(e) + '.', C_RED))
        logging.critical('Unable to verify archive integrity - ' + str(e) + '.')
        sys.exit(7)
    logging.debug('VERIFY ARCHIVE EXIT CODE: ' + str(arch_ec))
    if arch_ec == 1:
        if arch_out:
            for l in arch_out:
                logging.warning('VERIFY ARCHIVE OUTPUT: ' + l)
                printe(_subsubstep(l))
        printe(_subsubstep('Warning: Archive integrity check returned warning-level exit code.', C_ORANGE))
        logging.warning('Archive integrity check returned warning-level exit code.')
    elif arch_ec > 1:
        if arch_out:
            for l in arch_out:
                logging.critical('VERIFY ARCHIVE OUTPUT: ' + l)
                printe(_subsubstep(l))
        printe(_subsubstep('Archive integrity check returned error-level exit code.', C_RED))
        logging.critical('Archive integrity check returned error-level exit code.')
        sys.exit(7)
    else:
        if arch_out:
            for l in arch_out:
                logging.info('VERIFY ARCHIVE OUTPUT: ' + l)
                print(_subsubstep(l))
    logging.info('Process complete.')
    sys.exit(0)
    

def main():
    '''
    The entrypoint of the script.
    '''
    # Parse command-line arguments
    _parse_arguments()

    # Handle --list-targets
    if args.list_targets: handle_list_targets()

    # Verify some command-line arguments
    if args.email_level != 'never' and not args.email_to:
        printe(_c('Invalid option combination: "--email-to" not specified.', C_RED))
        sys.exit(1)
    
    # Setup logging
    _setup_logging()

    # Log CLI arguments at the DEBUG level
    logging.debug('----- CLI Arguments -----')
    dargs = vars(args)
    for a in dargs:
        logging.debug(a + ' : ' + str(dargs[a]))
    logging.debug('-------------------------')

    # Get the hostname of the machine
    get_hostname()

    # Validate the executing environment
    validate_environment()

    # Parse the YAML configuration file
    parse_yaml_config()

    # Handle --unlock
    if args.unlock: handle_unlock()

    # Handle --info
    if args.info: handle_info()

    # Handle --list-archives
    if args.list_archives: handle_list_archives()

    # Handle --restore
    if args.restore: handle_restore()

    # Handle --verify-integrity
    if args.verify_integrity: handle_verify_integrity()

    # Handle --repair
    if args.repair: handle_repair()

    # Handle the backup process
    handle_backup()

    # We are done
    logging.info('Process complete.')
    email_body = 'The backuputil script reports that it has successfully finished executing the "' + args.target + '" target.'
    if args.log_level == 'debug':
        email_body += '\n\nThe output of the underlying process has been suppressed from this email since the script was executed at a "debug" log level.'
        email_body += ' Please check the configured log file on the executing machine for the full output.'
    elif args.dry_run:
        email_body += '\n\nThe output of the underlying process has been suppressed from this email since the script was executed as a dry-run.'
        email_body += ' Please check the configured log file on the executing machine for the full output.'
    else:
        if backup_output:
            email_body += '\n\n---------- Backup Subprocess Output ----------\n'
            email_body += backup_output
        if prune_output:
            email_body += '\n---------- Prune Subprocess Output ----------\n'
            email_body += prune_output
    send_email(
        'Successfully executed "' + args.target + '" target',
        email_body,
        'info'
    )
    sys.exit(0)


def parse_yaml_config():
    '''
    Parses the specified YAML configuration file.
    '''
    print(_step('Loading configuration file...'))
    logging.info('Loading configuration file...')
    print(_substep('Reading configuration file...'))
    logging.debug('Reading configuration file...')
    try:
        with open(args.config_file, 'r') as f:
            config_raw = f.read()
    except Exception as e:
        printe(_subsubstep('Unable to read configuration file - ' + str(e) + '.', C_RED))
        logging.critical('Unable to read configuration file - ' + str(e) + '.')
        send_email(
            'Unable to read configuration file',
            emails.CANT_READ_CONF,
            'error'
        )
        sys.exit(3)
    print(_substep('Parsing configuration file...'))
    logging.debug('Parsing configuration file...')
    try:
        config = yaml.safe_load(config_raw)
    except Exception as e:
        printe(_subsubstep('Unable to parse configuration file - ' + str(e) + '.', C_RED))
        logging.critical('Unable to parse configuration file - ' + str(e) + '.')
        send_email(
            'Unable to parse configuration file',
            emails.CANT_PARSE_CONF,
            'error'
        )
        sys.exit(3)
    print(_substep('Validating base configuration...'))
    logging.debug('Validating base configuration...')
    if not 'targets' in config:
        printe(_subsubstep('Invalid configuration - "targets" key not found.', C_RED))
        logging.critical('Invalid configuration - "targets" key not found.')
        send_email(
            'Invalid configuration',
            emails.INVALID_CONF,
            'error'
        )
        sys.exit(3)
    if not isinstance(config['targets'], dict):
        printe(_subsubstep('Invalid configuration - value of "targets" key not dictionary of target specifications.', C_RED))
        logging.critical('Invalid configuration - value of "targets" key not dictionary of target specifications.')
        send_email(
            'Invalid configuration',
            emails.INVALID_CONF,
            'error'
        )
        sys.exit(3)
    print(_substep('Validating selected target...'))
    logging.debug('Validating selected target...')
    if not args.target in config['targets']:
        printe(_subsubstep('Invalid target - the specified target is not defined in the specified configuration file.', C_RED))
        logging.critical('Invalid target - the specified target is not defined in the specified configuration file.')
        send_email(
            'Invalid target',
            emails.INVALID_TARGET,
            'error'
        )
        sys.exit(3)
    global target
    target = config['targets'][args.target]
    if not isinstance(target, dict):
        printe(_subsubstep('Invalid target specification - value of target key not dictionary of target parameters.', C_RED))
        logging.critical('Invalid target specification - value of target key not dictionary of target parameters.')
        send_email(
            'Invalid target specification',
            emails.INVALID_TARGET_SPEC,
            'error'
        )
        sys.exit(3)
    logging.debug('Relevant Target Specification: ' + str(target))
    if not 'src_path' in target or not 'dst_path' in target:
        printe(_subsubstep('Invalid target specification - target does not specify a value for "src_path" or "dst_path".', C_RED))
        logging.critical('Invalid target specification - target does not specify a value for "src_path" or "dst_path".')
        send_email(
            'Invalid target specification',
            emails.INVALID_TARGET_SPEC,
            'error'
        )
        sys.exit(3)
    if not isinstance(target['dst_path'], str):
        printe(_subsubstep('Invalid target specification - destination path is not a path string.', C_RED))
        logging.critical('Invalid target specification - destination path is not a path string.')
        send_email(
            'Invalid target specification',
            emails.INVALID_TARGET_SPEC,
            'error'
        )
        sys.exit(3)
    if isinstance(target['src_path'], str):
        if '*' in target['src_path']:
            src_paths = glob.glob(os.path.expanduser(os.path.expandvars(target['src_path'])))
            if not src_paths:
                printe(_subsubstep('Invalid target specification - specified source path wildcard does not resolve to existing paths on the local filesystem.', C_RED))
                logging.critical('Invalid target specification - specified source path wildcard does not resolve to existing paths on the local filesystem.')
                send_email(
                    'Invalid target specification',
                    emails.INVALID_TARGET_SPEC,
                    'error'
                )
                sys.exit(3)
        else:
            if not os.path.exists(os.path.expanduser(os.path.expandvars(target['src_path']))):
                printe(_subsubstep('Invalid target specification - specified source path does not exist on the local filesystem.', C_RED))
                logging.critical('Invalid target specification - specified source path does not exist on the local filesystem.')
                send_email(
                    'Invalid target specification',
                    emails.INVALID_TARGET_SPEC,
                    'error'
                )
                sys.exit(3)
    elif isinstance(target['src_path'], list):
        for p in target['src_path']:
            if not isinstance(p, str):
                printe(_subsubstep('Invalid target specification - one or more specified source paths is not a path string.', C_RED))
                logging.critical('Invalid target specification - one or more specified source paths is not a path string.')
                send_email(
                    'Invalid target specification',
                    emails.INVALID_TARGET_SPEC,
                    'error'
                )
                sys.exit(3)
            if '*' in p:
                p_paths = glob.glob(os.path.expanduser(os.path.expandvars(p)))
                if not p_paths:
                    printe(_subsubstep('Invalid target specification - specified source path wildcard does not resolve to existing paths on the local filesystem.', C_RED))
                    logging.critical('Invalid target specification - specified source path wildcard does not resolve to existing paths on the local filesystem.')
                    send_email(
                        'Invalid target specification',
                        emails.INVALID_TARGET_SPEC,
                        'error'
                    )
                    sys.exit(3)
            else:
                if not os.path.exists(os.path.expanduser(os.path.expandvars(p))):
                    printe(_subsubstep('Invalid target specification - one or more specified source paths do not exist on the local filesystem.', C_RED))
                    logging.critical('Invalid target specification - one or more specified source paths do not exist on the local filesystem.')
                    send_email(
                        'Invalid target specification',
                        emails.INVALID_TARGET_SPEC,
                        'error'
                    )
                    sys.exit(3)
    else:
        printe(_subsubstep('Invalid target specification - "src_path" does not correspond to a path string or list of path strings.', C_RED))
        logging.critical('Invalid target specification - "src_path" does not correspond to a path string or list of path strings.')
        send_email(
            'Invalid target specification',
            emails.INVALID_TARGET_SPEC,
            'error'
        )
        sys.exit(3)
    if 'keep' in target:
        if not isinstance(target['keep'], dict):
            printe(_subsubstep('Invalid target specification - "keep" specification not a dictionary of time slices.', C_RED))
            logging.critical('Invalid target specification - "keep" specification not a dictionary of time slices.')
            send_email(
                'Invalid target specification',
                emails.INVALID_TARGET_SPEC,
                'error'
            )
            sys.exit(3)
        for slice_spec in target['keep']:
            if slice_spec not in ['hourly', 'daily', 'weekly', 'monthly', 'yearly']:
                printe(_subsubstep('Invalid target specification - "keep" specification contains one or more unknown time slices.', C_RED))
                logging.critical('Invalid target specification - "keep" specification contains one or more unknown time slices.')
                send_email(
                    'Invalid target specification',
                    emails.INVALID_TARGET_SPEC,
                    'error'
                )
                sys.exit(3)
    if 'exclude' in target:
        if not isinstance(target['exclude'], list):
            printe(_subsubstep('Invalid target specification - "exclude" specification not a list of paths.', C_RED))
            logging.critical('Invalid target specification - "exclude" specification not a list of paths.')
            send_email(
                'Invalid target specification',
                emails.INVALID_TARGET_SPEC,
                'error'
            )
            sys.exit(3)
    if 'post_run' in target:
        if not isinstance(target['post_run'], str): 
            printe(_subsubstep('Invalid target specification - "post_run" specification not a command string.', C_RED))
            logging.critical('Invalid target specification - "post_run" specification not a command string.')
            send_email(
                'Invalid target specification',
                emails.INVALID_TARGET_SPEC,
                'error'
            )
            sys.exit(3)
    if 'pre_run' in target:
        if not isinstance(target['pre_run'], str): 
            printe(_subsubstep('Invalid target specification - "pre_run" specification not a command string.', C_RED))
            logging.critical('Invalid target specification - "pre_run" specification not a command string.')
            send_email(
                'Invalid target specification',
                emails.INVALID_TARGET_SPEC,
                'error'
            )
            sys.exit(3)
    if 'rate_limit' in target:
        if not isinstance(target['rate_limit'], int):
            printe(_subsubstep('Invalid target specification - "rate_limit" specification not a positive integer value.', C_RED))
            logging.critical('Invalid target specification - "rate_limit" specification not a positive integer value.')
            send_email(
                'Invalid target specification',
                emails.INVALID_TARGET_SPEC,
                'error'
            )
            sys.exit(3)
        if target['rate_limit'] < 0:
            printe(_subsubstep('Invalid target specification - "rate_limit" specification not a positive integer value.', C_RED))
            logging.critical('Invalid target specification - "rate_limit" specification not a positive integer value.')
            send_email(
                'Invalid target specification',
                emails.INVALID_TARGET_SPEC,
                'error'
            )
            sys.exit(3)
    if 'dst_srv' in target:
        if not 'cert_path' in target:
            cert_path = args.cert_path
        else:
            cert_path = target['cert_path']
        if not os.path.isfile(cert_path):
            printe(_subsubstep('Invalid target specification - certificate file path does not correspond to an existing file.', C_RED))
            logging.critical('Invalid target specification - certificate file path does not correspond to an existing file.')
            send_email(
                'Invalid target specification',
                emails.INVALID_TARGET_SPEC,
                'error'
            )
            sys.exit(3)
        try:
            dst_srv_ip = socket.gethostbyname(target['dst_srv'])
        except Exception as e:
            printe(_subsubstep('Invalid target specification - unable to resolve hostname of destination server via DNS.', C_RED))
            logging.critical('Invalid target specification - unable to resolve hostname of destination server via DNS.')
            send_email(
                'Invalid target specification',
                emails.INVALID_TARGET_SPEC,
                'error'
            )
            sys.exit(3)


def prepare_execution():
    '''
    Prepares the execution environment (by setting a bunch of global variables).
    '''
    logging.debug('Preparing execution environment...')
    global dst_path
    dst_path = os.path.expandvars(os.path.expanduser(target['dst_path'])) 
    logging.debug('Destination Path: ' + dst_path)
    global src_paths
    if isinstance(target['src_path'], str):
        if '*' in target['src_path']:
            src_paths = glob.glob(os.path.expanduser(os.path.expandvars(target['src_path'])))
        else:
            src_paths = [os.path.expanduser(os.path.expandvars(target['src_path']))]
    else:
        src_paths = []
        for p in target['src_path']:
            if '*' in p:
                src_paths.extend(glob.glob(os.path.expanduser(os.path.expandvars(p))))
            else:
                src_paths.append(os.path.expanduser(os.path.expandvars(p)))
    logging.debug('Source Paths: ' + str(src_paths))
    global exclude_paths
    if 'exclude' in target:
        if isinstance(target['exclude'], str):
            exclude_paths = [os.path.expanduser(os.path.expandvars(target['exclude']))]
        else:
            exclude_paths = [os.path.expanduser(os.path.expandvars(e)) for e in target['exclude']]
    else:
        exclude_paths = []
    logging.debug('Excluded Paths: ' + str(exclude_paths))
    global rate_limit
    if 'rate_limit' in target:
        rate_limit = str(target['rate_limit'])
    else:
        rate_limit = str(args.rate_limit)
    logging.debug('Transfer Rate Limit: ' + rate_limit + ' KiB/s')
    global dst_srv
    if 'dst_srv' in target:
        dst_srv = target['dst_srv']
        logging.debug('Destination Server: ' + dst_srv)
    else:
        dst_srv = ''
        logging.debug('Destination Server: NONE')
    global cert_path
    if 'cert_path' in target:
        cert_path = target['cert_path']
    else:
        cert_path = args.cert_path
    logging.debug('Certificate Path: ' + cert_path)
    global password
    if 'password' in target:
        password = target['password']
    else:
        password = args.password
    if password:
        logging.debug('Repository Password: ' + password)
    else:
        logging.debug('Repository Password: NONE')
    global user
    if 'user' in target:
        user = target['user']
    else:
        user = args.user
    logging.debug('Remote Connection User: ' + user)
    global keep
    if 'keep' in target:
        keep = target['keep']
    else:
        keep = {}
    logging.debug('Pruning Configuration (keep): ' + str(keep))
    global post_run
    if 'post_run' in target:
        post_run = target['post_run']
    else:
        post_run = args.post_run
    logging.debug('Post-run Command: ' + post_run)
    global pre_run
    if 'pre_run' in target:
        pre_run = target['pre_run']
    else:
        pre_run = args.pre_run
    logging.debug('Pre-run Command: ' + pre_run)
    global repo_str
    if dst_srv:
        repo_str = '{user}@{server}:{path}'.format(
            user = user,
            server = dst_srv,
            path = dst_path
        )
    else:
        repo_str = dst_path
    logging.debug('Repository Reference String: ' + repo_str)
    print(_substep('Instantiating subprocess environment...'))
    logging.debug('Instantiating subprocess environment...')
    try:
        os.environ['BORG_RSH'] = 'ssh -i {cert} -o StrictHostKeyChecking=no'.format(
            cert=os.path.expanduser(os.path.expandvars(cert_path))
        )
        logging.debug('BORG_RSH = ' + os.environ['BORG_RSH'])
        os.environ['BORG_PASSPHRASE'] = password
        logging.debug('BORG_PASSPHRASE = ' + os.environ['BORG_PASSPHRASE'])
    except Exception as e:
        printe(_subsubstep('Unable to instantiate subprocess environment - ' + str(e) + '.', C_RED))
        logging.critical('Unable to instantiate subprocess environment - ' + str(e) + '.')
        send_email(
            'Unable to set subprocess environment variables',
            emails.CANT_SET_ENV,
            'error'
        )
        sys.exit(3)


def printe(instring):
    '''
    Prints the specified string to stderr.
    '''
    sys.stderr.write(instring + '\n')


def send_email(subject, body, level='error'):
    '''
    Sends an email to the configured recipients with the specified body, subject,
    and alert level. Whether the email actually gets sent is dependent on the
    alert level specified by "args.email_level".
    '''
    logging.debug('EMAIL CALL: ' + str({'subject': subject, 'body': body, 'level': level}))
    try:
        if args.log_level == 'debug':
            _send_email('backuputil@' + fqdn + ' - ' + subject, body, level, debug=True)
        else:
            _send_email('backuputil@' + fqdn + ' - ' + subject, body, level)
    except Exception as mail_e:
        logging.warning('Unable to send email - ' + str(mail_e) + '.')


def validate_environment():
    '''
    Validates the executing environment of the script.
    '''
    print(_step('Validating environment...'))
    logging.info('Validating environment...')
    print(_substep('Validating borg executable path...'))
    logging.debug('Validating borg executable path...')
    if not os.path.isfile(args.borg_executable):
        printe(_subsubstep('Specified borg executable path does not exist.', C_RED))
        logging.critical('Specified borg executable path does not exist.')
        send_email(
            'Unable to validate environment',
            emails.BORG_DOESNT_EXIST,
            'error'
        )
        sys.exit(2)
    logging.debug('Validating configuration file path...')
    print(_substep('Validating configuration file path...'))
    if not os.path.isfile(args.config_file):
        printe(_subsubstep('Specified configuration file path does not exist.', C_RED))
        logging.critical('Specified configuration file path does not exist.')
        send_email(
            'Unable to validate environment',
            emails.CONFIG_DOESNT_EXIST,
            'error'
        )
        sys.exit(2)
    print(_substep('Checking for existing backup processes...'))
    logging.debug('Checking for existing backup processes...')
    try:
        (pid_out, pid_ec) = _run_process(
            'pidof -x ' + os.path.basename(args.borg_executable),
            splitlines = False
        )
    except Exception as e:
        printe(_subsubstep('Unable to check for existing backup processes - ' + str(e) + '.', C_RED))
        logging.critical('Unable to check for existing backup processes - ' + str(e) + '.')
        send_email(
            'Unable to validate environment',
            emails.CANT_CHECK_FOR_RUNNING_BACKUPS,
            'error'
        )
        sys.exit(2)
    logging.debug('Existing Process Check Exit Code: ' + str(pid_ec))
    if pid_out: logging.debug('Existing Process ID (or subprocess output): ' + pid_out)
    if pid_ec == 0:
        printe(_subsubstep('Unable to proceed - another backup process is already running.', C_RED))
        logging.critical('Unable to proceed - another backup process is already running.')
        send_email(
            'Unable to validate environment',
            emails.EXISTING_BACKUP_RUNNING,
            'error'
        )
        sys.exit(2)


# --------------------------------------



# ---------- Boilerplate Magic ---------

if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError) as ki:
        sys.stderr.write('Recieved keyboard interrupt!\n')
        sys.exit(100)

# --------------------------------------
