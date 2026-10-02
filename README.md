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

Every container follows the same lifecycle. `type` is descriptive metadata only.
Profiles are **explicit and independent**: an instance uses a profile only when it
sets `profile`, and profiles never inherit from one another. This keeps effective
configuration easy to trace during incidents.

Normalization precedence is:

```text
internal runtime defaults
        <
anro_ktranslate_instance_defaults
        <
explicitly selected profile
        <
instance configuration
```

Mappings recursively merge. Scalars and lists supplied at a later layer replace
the inherited value. `ktranslate_args` is a mapping and therefore merges by CLI
argument name; this avoids copying a complete command list just to change one
option. A `null` argument removes the inherited option.

`command` remains a raw escape hatch and is mutually exclusive with
`ktranslate_args`. There is deliberately no profile inheritance, command-list
position merging, or implicit profile selection.

For every instance, `name` is the canonical systemd unit, Docker container, and
configuration basename. Names must begin with `anro_ktranslate_service_prefix`
(default `ktranslate-`) so reconciliation remains safely scoped.

## What the role owns

The role owns systemd/Docker lifecycle, container runtime options, static managed
files, external file mounts, dynamic file reload signaling, and reconciliation of
removed role-managed instances. Docker installation and Grafana Alloy remain out
of scope.

The role intentionally does not reproduce ktranslate's full application schema.
Complex application data belongs in mounted files; the small `ktranslate_args`
mapping exists only to make common CLI overrides composable.

## Built-in profiles

Three independent profiles cover the common deployment roles:

```yaml
anro_ktranslate_profiles:
  polling:
    ktranslate_args:
      snmp: /etc/ktranslate/snmp.yaml
      format: prometheus
      sinks: prometheus
      prom_listen: ":8082"

  discovery:
    ktranslate_args:
      snmp: /etc/ktranslate/snmp.yaml
      snmp_discovery_on_start: true
      format: prometheus
      sinks: prometheus
      prom_listen: ":8082"

  traps:
    ktranslate_args:
      snmp: /etc/ktranslate/snmp.yaml
      snmp_trap: ":1620"
      format: prometheus
      sinks: prometheus
      prom_listen: ":8082"
```

The role standardizes on `traps` for the workload/profile name. The listener port
is not published automatically; host exposure is deployment-specific and belongs
in the instance `ports` list.

### Polling instance

A normal poller needs only to select the profile and provide its device/config
file and any deployment-specific port mapping:

```yaml
anro_ktranslate_instances:
  - name: ktranslate-poll-router-001
    type: polling
    profile: polling
    ports:
      - "127.0.0.1:18082:8082/tcp"
    files:
      - name: snmp.yaml
        source: managed
        destination: /etc/ktranslate/snmp.yaml
        format: yaml
        content: "{{ router_001_snmp_config }}"
        reload: signal
        reload_signal: USR2
```

### Discovery override without command duplication

Only the changed CLI argument is declared on the instance:

```yaml
anro_ktranslate_instances:
  - name: ktranslate-discovery-mn-001
    type: discovery
    profile: discovery
    ktranslate_args:
      snmp_discovery_min: 30
```

The effective command includes all discovery profile arguments plus
`-snmp_discovery_min=30`.

### Override or remove inherited arguments

```yaml
anro_ktranslate_instances:
  - name: ktranslate-poll-special-001
    type: polling
    profile: polling
    ktranslate_args:
      prom_listen: ":9090"  # Overrides the profile value.
      sinks: null            # Removes -sinks entirely.
```

Boolean values render as lowercase `true`/`false`, matching normal CLI syntax.
CLI values are limited to strings, numbers, booleans, and null; structured data
should be placed in a managed/external file instead.

### Instance without a profile

Profiles are optional and never selected from `type` automatically:

```yaml
anro_ktranslate_instances:
  - name: ktranslate-custom-001
    type: custom
    command:
      - "-format=prometheus"
      - "-sinks=prometheus"
      - "-prom_listen=:8082"
```

This explicit behavior makes it immediately visible whether a container is using
a reusable profile or a raw command.

## Main variables

```yaml
anro_ktranslate_image: "kentik/ktranslate:latest"
anro_ktranslate_docker_binary: "/usr/bin/docker"
anro_ktranslate_systemd_dir: "/etc/systemd/system"
anro_ktranslate_config_dir: "/etc/ktranslate"
anro_ktranslate_environment_dir: "/etc/ktranslate/environment"
anro_ktranslate_service_prefix: "ktranslate"

anro_ktranslate_default_network: bridge
anro_ktranslate_default_pull_policy: missing
anro_ktranslate_default_restart_sec: 5
anro_ktranslate_default_stop_timeout: 30
anro_ktranslate_default_start_limit_interval_sec: 60
anro_ktranslate_default_start_limit_burst: 5

anro_ktranslate_instance_defaults: {}
anro_ktranslate_reconcile: true
anro_ktranslate_instances: []
```

Production deployments should pin `anro_ktranslate_image` to an explicit version
or digest rather than `latest`.

## Instance schema

```yaml
anro_ktranslate_instances:
  - name: ktranslate-polling-site-a
    type: polling
    profile: polling
    enabled: true

    image: "kentik/ktranslate:<pinned-version>"
    network: bridge
    pull_policy: missing
    restart_sec: 5
    stop_timeout: 30
    start_limit_interval_sec: 60
    start_limit_burst: 5

    environment: {}
    ports: []
    files: []
    volumes: []
    cap_add: []

    # Mergeable normal CLI override surface.
    ktranslate_args: {}

    # Raw escape hatch; do not use together with ktranslate_args.
    # command: []

    extra_docker_args: []
```

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
    ktranslate_args:
      prom_listen: null  # nulls out the prom_listen
      sinks: "kafka"     # sets the sink to kafka
      format: "flat_json"  # sets our output format to flat_json
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

## Molecule

The default Molecule scenario runs Ubuntu 24.04 with a real nested Docker daemon.
It verifies:

- systemd -> Docker lifecycle;
- bridge networking and port publishing;
- host networking without `--publish`;
- managed raw/YAML files;
- externally owned file mounts;
- disabled instances;
- explicit polling-profile selection and keyed CLI argument merging;
- SIGUSR2 reload of a changed managed SNMP file without replacing the container.

The nested workload image is also Ubuntu 24.04 so the lifecycle test does not
hide behavior behind a mock Docker CLI.

Run:

```bash
ansible-lint
ansible-playbook --syntax-check molecule/default/converge.yml
molecule test
```
