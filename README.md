# anro_ktranslate

`anro_ktranslate` manages a stack of independent `ktranslate` Docker containers
as systemd services. The role intentionally manages **container lifecycle and
configuration delivery**, not ktranslate's application schema.

That boundary keeps the role small while allowing each instance to use any
ktranslate-supported input mode, format, sink, network mode, command-line option,
or configuration file layout.

Docker installation is intentionally out of scope. Install and start Docker
before applying this role.

## Design principles

The role has one desired-state interface:

```yaml
anro_ktranslate_instances: []
```

There are no separate polling, discovery, or trap arrays. Every container uses
the same lifecycle code. `type` remains descriptive workload metadata and, by
default, also selects a same-named reusable profile. An explicit `profile` can
select a different profile without changing the workload classification.

Effective instance configuration uses deterministic shallow merge precedence:

```text
anro_ktranslate_instance_defaults
              <
anro_ktranslate_profiles[profile or type]
              <
explicit anro_ktranslate_instances entry
```

Lists such as `command`, `files`, `ports`, and `volumes` are **replaced**, not
appended. This makes an instance override authoritative and avoids hidden list
ordering behavior.

For every instance, `name` is the single canonical runtime name:

```text
systemd unit:     <name>.service
Docker container: <name>
config directory: /etc/ktranslate/<name>/
environment file: /etc/ktranslate/environment/<name>.env
```

The role requires names to begin with `anro_ktranslate_service_prefix` (default
`ktranslate-`). This safely scopes reconciliation to units owned by this role.

## What the role owns

The role owns:

- systemd unit lifecycle;
- Docker container lifecycle;
- image, network, port, capability, bind-mount, and environment configuration;
- static managed files rendered from inventory;
- mounting externally owned files;
- reconciliation of removed role-managed instances.

The role does **not** translate a custom Ansible schema into ktranslate's input,
format, or sink configuration. `command` and `files` are the application-facing
interfaces. This prevents the Ansible role from becoming a second copy of
ktranslate's configuration schema.

## Prometheus default

The deployment default is a Prometheus format and sink listening on port 8082:

```yaml
anro_ktranslate_default_command:
  - "-format=prometheus"
  - "-sinks=prometheus"
  - "-prom_listen=:8082"
```

This is only a default. It is not hard-coded into the systemd template. Any
instance can replace `command` completely to use another ktranslate-supported
format, sink, input mode, or combination.

Publishing or scraping the endpoint remains an instance/deployment decision.
Grafana Alloy configuration is intentionally outside this role.

## Main variables

```yaml
anro_ktranslate_image: "kentik/ktranslate:latest"
anro_ktranslate_docker_binary: "/usr/bin/docker"
anro_ktranslate_systemd_dir: "/etc/systemd/system"
anro_ktranslate_config_dir: "/etc/ktranslate"
anro_ktranslate_environment_dir: "/etc/ktranslate/environment"
anro_ktranslate_service_prefix: "ktranslate"

anro_ktranslate_default_network: "bridge"
anro_ktranslate_default_pull_policy: "missing"
anro_ktranslate_default_restart_sec: 5
anro_ktranslate_default_stop_timeout: 30
anro_ktranslate_default_start_limit_interval_sec: 60
anro_ktranslate_default_start_limit_burst: 5

anro_ktranslate_default_command:
  - "-format=prometheus"
  - "-sinks=prometheus"
  - "-prom_listen=:8082"

# Optional stack-wide overrides; empty by default.
anro_ktranslate_instance_defaults: {}

anro_ktranslate_profiles:
  polling:
    command:
      - "-snmp=/etc/ktranslate/snmp.yaml"
      - "-format=prometheus"
      - "-sinks=prometheus"
      - "-prom_listen=:8082"

anro_ktranslate_reconcile: true
anro_ktranslate_instances: []
```

Production deployments should pin `anro_ktranslate_image` to an explicit
version or digest rather than `latest`.

## Instance schema

```yaml
anro_ktranslate_instances:
  - name: ktranslate-polling-site-a
    type: polling
    enabled: true

    image: "kentik/ktranslate:<pinned-version>"
    network: bridge
    pull_policy: missing
    restart_sec: 5
    stop_timeout: 30
    start_limit_interval_sec: 60
    start_limit_burst: 5

    environment: {}

    ports:
      - "127.0.0.1:18082:8082/tcp"

    files: []
    volumes: []
    cap_add: []

    # Omit command to inherit the Prometheus default. Supplying command replaces
    # the default completely.
    command: []

    # Escape hatch for uncommon Docker run options. Do not put secrets here.
    extra_docker_args: []
```

`command: []` is an explicit empty command. To inherit the Prometheus default,
omit the `command` key entirely.

## Profiles and normalized defaults

Profiles are convenience defaults, not separate lifecycle implementations. The
built-in `polling` profile removes the repeated SNMP/Prometheus CLI boilerplate
from normal polling instances:

```yaml
anro_ktranslate_instances:
  - name: ktranslate-poll-router-001
    type: polling
    ports:
      - "127.0.0.1:18082:8082/tcp"
    files:
      - name: snmp.yaml
        source: managed
        destination: /etc/ktranslate/snmp.yaml
        format: yaml
        content: "{{ router_001_snmp_config }}"
```

Because `type: polling` selects the built-in `polling` profile, the instance
inherits:

```yaml
command:
  - "-snmp=/etc/ktranslate/snmp.yaml"
  - "-format=prometheus"
  - "-sinks=prometheus"
  - "-prom_listen=:8082"
```

Define deployment-specific profiles to standardize vendor, credential boundary,
listener, or shard behavior without changing role code:

```yaml
anro_ktranslate_profiles:
  polling:
    command:
      - "-snmp=/etc/ktranslate/snmp.yaml"
      - "-format=prometheus"
      - "-sinks=prometheus"
      - "-prom_listen=:8082"

  polling_slow:
    command:
      - "-snmp=/etc/ktranslate/snmp.yaml"
      - "-format=prometheus"
      - "-sinks=prometheus"
      - "-prom_listen=:8082"
      # Add only flags supported by the pinned ktranslate version.

anro_ktranslate_instances:
  - name: ktranslate-poll-special-001
    type: polling
    profile: polling_slow
```

An instance may override any profile key. Because normalization is shallow, an
explicit `command` or `files` list replaces the profile list completely.

## Managed files

Managed files are static configuration maintained in inventory/Git and rendered
by this role. A managed file supports raw text, YAML serialization, or JSON
serialization.

### Raw file

```yaml
anro_ktranslate_instances:
  - name: ktranslate-polling-site-a
    type: polling
    files:
      - name: snmp.yaml
        source: managed
        destination: /etc/ktranslate/snmp.yaml
        format: raw
        mode: "0640"
        read_only: true
        content: |
          # Static ktranslate SNMP configuration maintained in Git.
          # Use the schema required by the pinned ktranslate version.
          ...
    command:
      - "-snmp=/etc/ktranslate/snmp.yaml"
      - "-format=prometheus"
      - "-sinks=prometheus"
      - "-prom_listen=:8082"
```

### YAML file

The role can serialize arbitrary mappings/lists without understanding their
application semantics:

```yaml
files:
  - name: application.yaml
    source: managed
    destination: /etc/ktranslate/application.yaml
    format: yaml
    content:
      example_key: example_value
      nested:
        - one
        - two
```

For sensitive managed files, set `no_log: true` and use an appropriately
restrictive mode such as `"0600"`.

## External files and future configuration renderers

An external file is **not created or modified by this role**. It is an explicit
ownership seam for a future API, URL, Git, NetBox, or other renderer.

```yaml
anro_ktranslate_instances:
  - name: ktranslate-polling-site-a
    type: polling
    files:
      - name: snmp.yaml
        source: external
        host_path: /var/lib/ktranslate-config/site-a/snmp.yaml
        destination: /etc/ktranslate/snmp.yaml
        read_only: true
    command:
      - "-snmp=/etc/ktranslate/snmp.yaml"
      - "-format=prometheus"
      - "-sinks=prometheus"
```

The external host file must exist when this role converges. Failing early is
intentional: otherwise Docker would fail later with an invalid bind mount.

By default, the role records the external file checksum in a comment in the
generated unit. If the external file changes before a later Ansible run, the
unit changes and the service is restarted.

For dynamic device inventory, set `reload: signal`. Signal-bound external files
are deliberately excluded from the systemd checksum comments. The role stores
their last successfully applied checksums in a root-only state file under the
instance configuration directory. On a later converge, a changed checksum sends
the configured signal without replacing the container. State is persisted only
after the reload succeeds so a failed signal is retried on the next run.

A renderer that updates an external file between Ansible runs may also send the
same signal immediately; otherwise the role detects and reloads it on the next
Ansible converge.

This model supports a future architecture without adding API/authentication logic
to this role:

```text
Git / API / NetBox / URL
          |
          v
  config renderer
          |
          v
 external host file
          |
          v
 anro_ktranslate bind mount
          |
          v
 ktranslate container
```

## Dynamic device files and live reload

ktranslate can reload SNMP device inventory in a running container when it
receives `SIGUSR2`. Use `reload: signal` for files whose contents can change
without changing container topology or static runtime configuration.

### Ansible-managed dynamic device file

```yaml
anro_ktranslate_instances:
  - name: ktranslate-poll-router-001
    type: polling
    files:
      - name: snmp.yaml
        source: managed
        destination: /etc/ktranslate/snmp.yaml
        format: yaml
        content: "{{ router_001_devices }}"
        reload: signal
        reload_signal: USR2
```

When the rendered content changes, the role keeps the existing container and
runs the equivalent of:

```text
docker kill --signal USR2 ktranslate-poll-router-001
```

### Externally owned dynamic device file

Use this when Git/CI, a discovery classifier, NetBox integration, or another
renderer owns the device file:

```yaml
anro_ktranslate_instances:
  - name: ktranslate-poll-router-001
    type: polling
    files:
      - name: snmp.yaml
        source: external
        host_path: /var/lib/ktranslate/devices/router-001.yaml
        destination: /etc/ktranslate/snmp.yaml
        read_only: true
        reload: signal
        reload_signal: USR2
```

The external producer owns `/var/lib/ktranslate/devices/router-001.yaml`; this
role only validates, mounts, fingerprints, and reloads it. The role never edits
or deletes externally owned files.

Use `reload: restart` (the default) for configuration changes that require a new
process, mount topology changes, profile/MIB changes whose live-reload behavior
is not documented, or any file where signal safety is uncertain.

### Restart versus signal behavior

| Change | Result |
| --- | --- |
| Managed file with `reload: restart` changes | Container restart |
| External file with `reload: restart` checksum changes | Unit changes; container restart |
| Managed file with `reload: signal` changes | Signal running container |
| External file with `reload: signal` checksum changes | Signal running container |
| Managed file is removed from desired state | Container restart |
| Environment or systemd runtime changes | Container restart |
| First deployment | Container starts with current files; no redundant signal |

If a restart and signal-bound file change occur in the same converge, the
restart wins and the signal is suppressed because the new process already reads
the current files.

## Network modes

Bridge is the default:

```yaml
network: bridge
ports:
  - "127.0.0.1:18082:8082/tcp"
```

Host networking is supported:

```yaml
network: host
ports: []
```

The role rejects `ports` with `network: host`. Docker port publishing is not
applicable when the container shares the host network namespace. Multiple
host-network containers must also be configured so they do not bind the same
listener ports.

## Non-Prometheus example

The role does not need code changes when an instance uses a different ktranslate
format or sink. The instance supplies the authoritative command:

```yaml
anro_ktranslate_instances:
  - name: ktranslate-flow-site-a
    type: flow
    network: host
    command:
      - "-format=flat_json"
      - "-sinks=kafka"
      # Add the remaining flags/environment required by the pinned ktranslate
      # version and your Kafka deployment.
    environment: {}
    files: []
```

## Additional bind mounts

Use `files` for individual configuration files. Use `volumes` for generic bind
mounts such as profile directories:

```yaml
volumes:
  - source: /srv/ktranslate/profiles
    target: /etc/ktranslate/profiles
    read_only: true
```

## Reconciliation

With `anro_ktranslate_reconcile: true`, the role identifies stale systemd units
only when both conditions are true:

1. the unit name matches `anro_ktranslate_service_prefix-*.service`;
2. the unit contains the role-managed marker.

Stale units are stopped and disabled, stale containers are removed, and their
role-managed unit/config/environment artifacts are deleted. External files are
never deleted by this role.

## Recommended production workflow

A scalable deployment should keep discovery, approval/classification, and
polling assignment separate from this role's container lifecycle:

```text
Discovery shards
      |
      v
Candidate devices
      |
      v
Classification / approval / Git PR
      |
      v
Approved device inventory
      |
      v
Shard renderer
      |
      +--> router-001.yaml --> ktranslate-poll-router-001 --USR2-->
      +--> router-002.yaml --> ktranslate-poll-router-002 --USR2-->
      +--> switch-001.yaml --> ktranslate-poll-switch-001 --USR2-->
```

Use stable poller names rather than CIDRs in service names. Device assignments
can then move between shard files without renaming systemd services or Docker
containers. CPU, memory, restart/OOM, poll duration, and device-count metrics can
inform when inventory automation should split a shard; the role should continue
to deploy declared desired state rather than making autonomous scaling decisions.

## Security

- Docker environment files are mode `0600` under a root-only directory.
- Managed file modes are explicit and default to `0640`.
- Use `no_log: true` for managed file content that contains secrets.
- `command` and `extra_docker_args` are stored in the systemd unit and can be
  visible through process inspection; do not put credentials there.
- External files remain owned by their producing system or role.
- Bind-mount paths and instance names are validated before service changes.
- Docker installation and daemon security policy are intentionally separate from
  this role.

## Migration from the proof-of-concept interface

Replace the three v1 arrays:

```yaml
anro_ktranslate_polling_instances: []
anro_ktranslate_discovery_instances: []
anro_ktranslate_trap_instances: []
```

with one list:

```yaml
anro_ktranslate_instances:
  - name: ktranslate-polling-site-a
    type: polling
  - name: ktranslate-discovery-site-a
    type: discovery
  - name: ktranslate-traps-site-a
    type: traps
```

The old generic `config:` mapping is replaced by `files:`. This removes the
assumption that ktranslate has exactly one configuration file and creates the
future ownership boundary needed for externally rendered configuration.

## Molecule

The default Molecule scenario runs Ubuntu 24.04 with a real nested Docker daemon.
It verifies:

- systemd -> Docker lifecycle;
- bridge networking and port publishing;
- host networking without `--publish`;
- managed raw/YAML files;
- externally owned file mounts;
- disabled instances;
- inheritance of the default Prometheus command.

The nested workload image is also Ubuntu 24.04 so the lifecycle test does not
hide behavior behind a mock Docker CLI.

Run:

```bash
ansible-lint
ansible-playbook --syntax-check molecule/default/converge.yml
molecule test
```
