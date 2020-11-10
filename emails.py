'''
Contains email bodies for the backuputil script.
'''

PRE_MSG = 'The backuputil script reports that'

BACKUP_ERR = """
{pre} it encountered an error-level exit code from the backup subprocess.
""".format(pre=PRE_MSG)

BACKUP_EXCEPTION = """
{pre} it encountered an exception while executing the backup subprocess.
""".format(pre=PRE_MSG)

BACKUP_WARN = """
{pre} it encountered a warning-level exit code from the backup subprocess.
""".format(pre=PRE_MSG)

CANT_CHECK_FOR_RUNNING_BACKUPS = """
{pre} it encountered an exception while trying to check for existing backup processes.
""".format(pre=PRE_MSG)

CANT_PARSE_CONF = """
{pre} it encountered an exception while trying to parse the specified configuration file.
""".format(pre=PRE_MSG)

CANT_READ_CONF = """
{pre} it encountered an exception while trying to read the specified configuration file.
""".format(pre=PRE_MSG)

CANT_SET_ENV = """
{pre} it encountered an exception while trying to set environment variables required by the "borg" subprocess.
""".format(pre=PRE_MSG)

CONFIG_DOESNT_EXIST = """
{pre} the specified path for the configuration file does not exist on the local filesystem.
""".format(pre=PRE_MSG)

BORG_DOESNT_EXIST = """
{pre} the specified path for the Borg Backup executable binary does not exist on the local filesystem.
""".format(pre=PRE_MSG)

EXISTING_BACKUP_RUNNING = """
{pre} it was unable to proceed with the backup process because another backup process was already running.
""".format(pre=PRE_MSG)

INFO_ERR = """
{pre} it encountered an error-level exit code from the repository verification subprocess.
Make sure the destination repository was created via "borg init" prior to running the script.
""".format(pre=PRE_MSG)

INFO_EXCEPTION = """
{pre} it encountered an exception while executing the repository verification subprocess.
""".format(pre=PRE_MSG)

INFO_WARN = """
{pre} it encountered a warning-level exit code from the repository verification subprocess.
""".format(pre=PRE_MSG)

INVALID_CONF = """
{pre} the specified configuration file contains one or more invalid specifications.
""".format(pre=PRE_MSG)

INVALID_TARGET = """
{pre} the given target is not defined in the specified configuration file.
""".format(pre=PRE_MSG)

INVALID_TARGET_SPEC = """
{pre} the specified target has an invalid definition.
""".format(pre=PRE_MSG)

POST_RUN_EXCEPTION = """
{pre} it encountered an exception while executing the specified post-run command.
""".format(pre=PRE_MSG)

POST_RUN_EXIT = """
{pre} it encountered a non-zero exit code while executing the specified post-run command.
""".format(pre=PRE_MSG)

PRE_RUN_EXCEPTION = """
{pre} it encountered an exception while executing the specified pre-run command.
""".format(pre=PRE_MSG)

PRE_RUN_EXIT = """
{pre} it encountered a non-zero exit code while executing the specified pre-run command.
""".format(pre=PRE_MSG)

PRUNE_ERR = """
{pre} it encountered an error-level exit code from the pruning subprocess.
""".format(pre=PRE_MSG)

PRUNE_EXCEPTION = """
{pre} it encountered an exception while executing the pruning subprocess.
""".format(pre=PRE_MSG)

PRUNE_WARN = """
{pre} it encountered a warning-level exit code from the pruning subprocess.
""".format(pre=PRE_MSG)
