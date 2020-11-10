# Configuration File Layout

The `backuputil` script reads in a YAML configuration file, which contains one
or more _target specifications_. Each target specification is a blueprint which
defines where-to and what the underlying `borg` process should back-up. The idea
is that you have multiple target specifications (one for each distinct
component) which are called on different time schedules via `cron` or something
similar.

The core of the configuration file is the `targets` key, which defines a
dictionary of target specifications, each of which is a dictionary of _target
parameters_. Each target specification must be given a unique name, and may have
any of the following parameters:

| Parameter    | Description                                                                    |
|--------------|--------------------------------------------------------------------------------|
| `cert_path`  | (Optional) The certificate to use for validating remote server identity.       |
| `dst_path`   | The destination path.                                                          |
| `dst_srv`    | The hostname or IP of the destination server (for remote back-ups).            |
| `exclude`    | (Optional) A list of paths to exclude from the backup process.                 |
| `keep`       | (Optional) The archive pruning configuration, as a dictionary of time slices.  |
| `password`   | (Optional) The password to use for authenticating to destination repositories. |
| `post_run`   | (Optional) A shell command to run after the bacjup process is successful.      |
| `pre_run`    | (Optional) A shell command to run before starting the backup process.          |
| `rate_limit` | (Optional) The rate limit (in KiB/s) to use during the transfer.               |
| `src_path`   | The source path (or list of source paths) of the content to back-up.           |
| `user`       | (Optional) The user to use for remote connections (for remote back-ups).       |

In greater detail:

### `cert_path` Parameter

This parameter overrides the default certificate file path provided by
`--cert-path` or the `BACKUPUTIL_CERT_PATH` environment variable. This
certificate is utilized to set the `ssh` identity when the script sets the
underlying `BORG_RSH` environment variable. This parameter has no effect on
local backups.

### `dst_path` Parameter

This parameter specifies the relevant destination Borg repository path. For
local backups, this path is passed directly to the underlying `borg` subprocess.
For remote backups, this path is essentially prefixed with `{user}@{dst_srv}:`.

### `dst_srv` Parameter

This parameter specifies the hostname or IP address of the destination server.
The inclusion of this key identifies that the encompassing target is a remote
backup.

### `exclude` Parameter

Specifies a list of paths to exclude from the backup process. In technicality,
the script passes each of these strings as its own `--exclude` option to the
underlying `borg` subprocess. These can actually correspond to more complex
patterns, so see `man borg-patterns` for more info.

### `keep` Parameter

The `keep` parameter specifies a dictionary of "time slices" to pass as
`--keep-*` arguments to the underlying `borg` pruning subprocess. This
dictionary may contain any of the following keys: `hourly`, `daily`, `weekly`,
`monthly`, and `yearly`. See `man borg-prune` for more info. The absence of the
`keep` parameter will skip the pruning process.

### `password` Parameter

This parameter overrides the default password provided by `--password` or the
`BACKUPUTIL_PASSWORD` environment variable. This is the password used to
authenticate with encrypted repositories, and thus is _not necessarily_ the
password utilized in remote server connections. Remote server authentication is
handled via the identity specified by `cert_path` (or its default values).

### `post_run` Parameter

This parameter overrides the default command to run after the backup process
specified by `--post-run` or the `BACKUPUTIL_POST_RUN` environment variable.
This is a command string which is executed in a regular shell environment, and
thus may contain pipes, etc. Note that this command must end with an exit code
of `0` in order for the run to be considered successful.

### `pre_run` Parameter

This parameter overrides the default command to run before the backup process
specified by `--pre-run` or the `BACKUPUTIL_PRE_RUN` environment variable. This
is a command string which is executed in a regular shell environment, and thus
may contain pipes, etc. Note that this command must end with an exit code of `0`
in order for the backup process to proceed.

### `rate_limit` Parameter

This parameter overrides the default transfer rate limit (in KiB/s) for remote
connections provided by `--rate-limit` or the `BACKUPUTIL_RATE_LIMIT`
environment variable. This parameter has no effect on local backups. This
parameter may be set to `0` to disable rate limiting.

### `src_path` Parameter

This parameter specifies a path or list of paths to include in the backup
process. Note that these paths support basic wildcard globbing with `*`.

### `user` Parameter

This parameter overrides the default user provided by `--user` or the
`BACKUPUTIL_USER` environment variable. This is the username utilized in
establishing remote connections, and thus is only a relevant parameter for
remote backups.
