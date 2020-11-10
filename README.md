# Introduction

`backuputil` is a Python script that extends and generalizes the functionality
of the [Borg Backup Utility](https://www.borgbackup.org/) by allowing multiple
"back-up tasks" to be specified in a single configuration file.

## System Requirements

`backuputil.py` may be executed directly if the host system runs Python 2.7 with
the PyYAML library installed.


----
# Usage

`backuputil` is invoked with a single required argument, being the name of the
backup target specification to execute within the parsed configuration file.
With regards to this repository, the simplest example would be:

```bash
$ backuputil -c example/backuputil.yaml user_files
```

To obtain the list of available targets within the configuration file:

```bash
$ backuputil -c example/backuputil.yaml --list-targets
```

## CLI Arguments

The following table describes the remaining optional arguments:

| Argument(s)                | Description                                                                                                                                                                                                                                     |
|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--borg-executable`        | Specifies the path to the Borg Backup executable binary.                                                                                                                                                                                        |
| `--cert-path`              | Specifies the path to the default certificate file to use for remote backups.                                                                                                                                                                   |
| `-C`, `--checkpoint-int`   | Specifies the time interval (in seconds) in which the underlying Borg subprocess will write checkpoints.                                                                                                                                        |
| `-c`, `--config-file`      | Specifies the configuration file to load target definitions from.                                                                                                                                                                               |
| `-d`, `--dry-run`          | Specifies that the script should only execute a dry-run, preventing any files from actually being backed-up.                                                                                                                                    |
| `-e`, `--email-level`      | Specifies the condition at which the script should send an email.                                                                                                                                                                               |
| `-t`, `--email-to`         | Specifies the email address to receive sent emails.                                                                                                                                                                                             |
| `--force-prune`            | Specifies that the script should force the deletion of corrupted archives during the pruning process.                                                                                                                                           |
| `-h`, `--help`             | Displays help and usage information.                                                                                                                                                                                                            |
| `-i`, `--info`             | Displays information about the relevant destination repository for the specified target (instead of performing a new backup).                                                                                                                   |
| `--list-archives`          | Lists all existing archives (backups) in the repository relevant to the specified target (instead of performing a new backup).                                                                                                                  |
| `--list-targets`           | Lists all of the available targets in the specified configuration file.                                                                                                                                                                         |
| `-f`, `--log-file`         | Specifies the log file to write to.                                                                                                                                                                                                             |
| `-l`, `--log-level`        | Specifies the log level of the script.                                                                                                                                                                                                          |
| `-m`, `--log-mode`         | Specifies whether to append or overwrite the specified log file.                                                                                                                                                                                |
| `--no-color`               | Disables color output to stdout/stderr.                                                                                                                                                                                                         |
| `-p`, `--password`         | Specifies the default password string to use when authenticating to destination repositories.                                                                                                                                                   |
| `--post-run`               | Specifies the default command to run after completing a backup process.                                                                                                                                                                         |
| `--pre-run`                | Specifies the default command to run prior to starting a backup process.                                                                                                                                                                        |
| `-r`, `--rate-limit`       | Specifies the default rate limit to use (in KiB/s) in transfers to remote servers (set to `0` for no limit).                                                                                                                                    |
| `--repair`                 | Instructs the script to attempt a repair of the repository and any corrupt archives (instead of performing a new backup).                                                                                                                       |
| `--restore`                | Restores the contents of an archive associated with the specified target into the path specified by `--restore-to`.                                                                                                                             |
| `--restore-to`             | Specifies the destintion path for `--restore`.                                                                                                                                                                                                  |
| `-T`, `--timestamp-fmt`    | Specifies the format to use for generating timestamps via Python's `strftime()` method.                                                                                                                                                         |
| `--unlock`                 | Specifies that the script should unlock (break-lock) the repository associated with the specified backup target. This is used to recover from a failed run that results in an active repository lock. The script will not perform a new backup. |
| `-u`, `--user`             | Specifies the default login user relative to the specified target server with which remote transfer connections are established.                                                                                                                |
| `-v`, `--verify-integrity` | Verifies the integrity of the repository (and any previous archives) associated with the specified target (instead of performing a new backup).                                                                                                 |

Each of the above options has the following set of corresponding value types and
default values:

| Arguments(s)             | Value Type / Possible Values                 | Default Value               |
|--------------------------|----------------------------------------------|-----------------------------|
| `--borg-executable`      | File Path                                    | `/usr/bin/borg`             |
| `--cert-path`            | File Path                                    | `~/.ssh/backuputil.pem`     |
| `-C`, `--checkpoint-int` | Integer                                      | `900`                       |
| `-c`, `--config-file`    | File Path                                    | `/etc/backuputil.yaml`      |
| `-e`, `--email-level`    | `never`, `error`, `warning`, or `completion` | `never`                     |
| `-t`, `--email-to`       | Email Address                                |                             |
| `-f`, `--log-file`       | File Path                                    | `/var/log/backuputil.log`   |
| `-l`, `--log-level`      | `info` or `debug`                            | `info`                      |
| `-m`, `--log-mode`       | `append` or `overwrite`                      | `append`                    |
| `-p`, `--password`       | Generic String                               |                             |
| `--post-run`             | Command String                               |                             |
| `--pre-run`              | Command String                               |                             |
| `-r`, `--rate-limit`     | Integer                                      | `0`                         |
| `--restore`              | Format String (See Below)                    |                             |
| `--restore-to`           | Path                                         | (Current Working Directory) |
| `-T`, `--timestamp-fmt`  | Format String                                | `%Y-%m-%d.%H-%M-%S`         |
| `-u`, `--user`           | User Name                                    | (Current User)              |

#### `--restore` Argument

The `--restore` argument tells the script to restore the contents of an archive
associated with the specified target into the current working directory. This is
specified via a value that adheres to the following format:

```
--restore ARCHIVE[:PATH]
```

where `ARCHIVE` is the name of the archive and `PATH` is an optional sub-path of
the archive to restore. For example

```bash
$ backuputil foo --restore '2019-01-29.00-01-02:/bar/baz.txt'
```

would restore `/bar/baz.txt` from the `2019-01-29.00-01-02` archive in the repo
specified by the `foo` target into the current working directory. You can obtain
a list of possible archives to extract from by running

```bash
$ backuputil TARGET --list-archives
```

The names of these archives will correspond to the timestamp (formatted via
`--timestamp-fmt`) at which they were created. **Be cautioned that if the
timestamp format contains a `:` character, a reference path _must_ be
specified**.

Furthermore, you can output the restoration to a specific path (instead of
restoring into the current working directory) by passing `--restore-to
DESTINATION_PATH`. If this path ends in `.tar.gz`, `.tar.bz2`, or `.tar.xz`,
then an archive containing the the restored files will be created.

## Script Output

The output of a typical run may look something like this on stderr/stdout (note
the prune error due to no archive existing):

```
$ backuputil -c example/backuputil.yaml home --dry-run
:: Validating environment...
  --> Validating borg executable path...
  --> Validating configuration file path...
  --> Checking for existing backup processes...
:: Loading configuration file...
  --> Reading configuration file...
  --> Parsing configuration file...
  --> Validating base configuration...
  --> Validating selected target...
:: Executing target (DRY RUN)...
  --> Performing backup...
  --> Pruning old backups...
      Unable to prune old backups - subprocess returned error-level exit code.
```

The corresponding log file for the above run looks like this:

```
[INF] [01/11/2019 01:03:55 PM] [7708] Validating environment...
[INF] [01/11/2019 01:03:55 PM] [7708] Loading configuration file...
[INF] [01/11/2019 01:03:55 PM] [7708] Executing target (DRY RUN)...
[INF] [01/11/2019 01:03:55 PM] [7708] BACKUP OUTPUT: Creating archive at "/backup/home::home.2019-01-11.13-03-55"
[INF] [01/11/2019 01:03:57 PM] [7708] PRUNE OUTPUT: Repository /backup/home does not exist.
[CRI] [01/11/2019 01:03:57 PM] [7708] Unable to prune old backups - subprocess returned error-level exit code.
```

Notice that the log file follows the following format:

```
[LOG_LEVEL] [TIMESTAMP] [PROCESS_ID] MESSAGE
```

Note that when `--log-level debug` is passed to `backuputil`, an additional set
of options will be passed to the underlying `borg` suprocesses to increase
verbosity. However, these additional bits of info will still be written to the
log file at the `[INF]` level.

## Exit Codes

The script not only returns non-zero exit codes on fatal errors, but even broadly categorizes them:

| Code | Description                                                                                         |
|------|-----------------------------------------------------------------------------------------------------|
| 0    | Script successfully ran, although perhaps with warnings.                                            |
| 1    | Generic issue prior to the environment validation step (invalid arguments, import exceptions, etc). |
| 2    | Issue during the environment validation step.                                                       |
| 3    | Issue with loading, parsing, or validating the configuration file and specified target.             |
| 4    | Issue with executing the backup process.                                                            |
| 5    | Issue with the pruning process.                                                                     |
| 6    | Issue with restoring an existing archive.                                                           |
| 7    | Issue with verifying the consistency of the repository.                                             |
| 8    | Issue with obtaining repository information.                                                        |
| 9    | Issue with attempting to repair a corrupt repository and/or corrupt archives.                       |
| 10   | Issue with unlocking the repository (via `--unlock`).                                               |
| 100  | Script was interrupted via CTRL+C or CTRL+D.                                                        |

## Environment Variables

The default behavior of the `backuputil` script may also be configured via
environment variables. Each environment variable has an associated command line
argument, as described in the table below:

| Environment Variable     | Corresponding CLI Argument |
|--------------------------|----------------------------|
| `BACKUPUTIL_BORG_PATH`   | `--borg-executable`        |
| `BACKUPUTIL_CERT_PATH`   | `--cert-path`              |
| `BACKUPUTIL_CP_INTERVAL` | `--checkpoint-int`         |
| `BACKUPUTIL_CONFIG_FILE` | `--config-file`            |
| `BACKUPUTIL_EMAIL_LVL`   | `--email-level`            |
| `BACKUPUTIL_EMAIL_TO`    | `--email-to`               |
| `BACKUPUTIL_LOG_FILE`    | `--log-file`               |
| `BACKUPUTIL_LOG_LVL`     | `--log-level`              |
| `BACKUPUTIL_LOG_MODE`    | `--log-mode`               |
| `BACKUPUTIL_PASSWORD`    | `--password`               |
| `BACKUPUTIL_POST_RUN`    | `--post-run`               |
| `BACKUPUTIL_PRE_RUN`     | `--pre-run`                |
| `BACKUPUTIL_RATE_LIMIT`  | `--rate-limit`             |
| `BACKUPUTIL_TIMESTAMP`   | `--timestamp-fmt`          |
| `BACKUPUTIL_USER`        | `--user`                   |

As an example, if `BACKUPUTIL_CERT_PATH` is set to `~/.ssh/foo.pem` but
`--cert-path ~/.ssh/bar.pem` was passed to `backuputil` via command-line, then
the script would use `~/.ssh/bar.pem` as the _default_ certificate path. A
target specification could furthermore overwrite this value by setting a value
for `cert_path`.

----
# Configuration File Layout

See `CONFIGURATION.md` within this repository for further information on writing
`backuputil` target configuration files.
