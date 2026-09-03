# anro_ktranslate

Ansible role for running multiple `ktranslate` Docker containers as independent
systemd services. The inventory interface exposes separate polling, discovery,
and trap instance arrays while the role normalizes all instances to a common
container lifecycle model.

Docker installation is intentionally out of scope. Apply the Docker role for the
host before this role.

## Design

Each configured instance produces:

- one systemd unit;
- one generated ktranslate YAML configuration;
- one root-only Docker environment file;
- one Docker container whose lifecycle is owned by systemd.

Service naming is deterministic:

```text
ktranslate-polling-<name>.service
ktranslate-discovery-<name>.service
ktranslate-traps-<name>.service
```

When `anro_ktranslate_reconcile` is enabled, role-managed services that disappear
from inventory are stopped, disabled, removed, and their role-managed files are
deleted.

## Variables

```yaml
anro_ktranslate_image: "kentik/ktranslate:latest"
anro_ktranslate_docker_binary: "/usr/bin/docker"
anro_ktranslate_systemd_dir: "/etc/systemd/system"
anro_ktranslate_config_dir: "/etc/ktranslate"
anro_ktranslate_environment_dir: "/etc/ktranslate/environment"
anro_ktranslate_container_config_dir: "/etc/ktranslate"
anro_ktranslate_service_prefix: "ktranslate"
anro_ktranslate_default_network: "bridge"
anro_ktranslate_default_pull_policy: "missing"
anro_ktranslate_default_restart_sec: 5
anro_ktranslate_default_stop_timeout: 30
anro_ktranslate_reconcile: true

anro_ktranslate_polling_instances: []
anro_ktranslate_discovery_instances: []
anro_ktranslate_trap_instances: []
```

## Instance schema

All three arrays accept the same base schema:

```yaml
- name: "site-a-01"                  # required
  enabled: true                      # default: true
  image: "kentik/ktranslate:v2.x"   # default: anro_ktranslate_image
  network: "bridge"                 # default: global network
  pull_policy: "missing"            # always | missing | never
  restart_sec: 5
  stop_timeout: 30

  # Serialized directly to the per-instance config.yaml.
  config: {}

  # Written to a root-only env file and passed via --env-file.
  environment: {}

  # Docker --publish syntax.
  ports: []

  # Bind mounts. Source paths must be absolute.
  volumes: []
  # - source: "/srv/ktranslate/profiles"
  #   target: "/etc/ktranslate/custom-profiles"
  #   read_only: true

  cap_add: []

  # Arguments appended after the image. The upstream image ENTRYPOINT is
  # ktranslate, so these are ktranslate CLI arguments.
  command: []

  # Escape hatch for Docker flags not modeled above. Avoid secrets here because
  # the rendered unit is world-readable and visible through process inspection.
  extra_docker_args: []

  # Use only when the config mapping itself contains secrets. Prefer environment
  # variables for secrets when ktranslate supports them.
  config_no_log: false
```

## Example

```yaml
anro_ktranslate_image: "kentik/ktranslate:v2.2.35"

anro_ktranslate_polling_instances:
  - name: "us-central-site01-a"
    config:
      sinks:
        - prometheus
      prometheus_sink:
        listen_addr: ":8082"
    ports:
      - "9101:8082/tcp"
    command:
      - "-config"
      - "/etc/ktranslate/config.yaml"

  - name: "us-central-site01-b"
    config:
      sinks:
        - prometheus
      prometheus_sink:
        listen_addr: ":8082"
    ports:
      - "9102:8082/tcp"
    command:
      - "-config"
      - "/etc/ktranslate/config.yaml"

anro_ktranslate_discovery_instances:
  - name: "us-central-site01"
    config: {}
    command:
      - "-config"
      - "/etc/ktranslate/config.yaml"
      - "-snmp_discovery=true"

anro_ktranslate_trap_instances:
  - name: "us-central-site01"
    config: {}
    ports:
      - "1162:1162/udp"
    command:
      - "-config"
      - "/etc/ktranslate/config.yaml"
```

The role intentionally does not configure Grafana Alloy. Expose the required
Prometheus listener from each instance and configure Alloy separately.

## Security notes

- Environment files are mode `0600` and never rendered into the systemd unit.
- Generated ktranslate configuration is mode `0640`.
- `extra_docker_args` and `command` are visible in the systemd unit and process
  command line; do not place credentials in them.
- Bind-mount source paths must be absolute.
- Instance names are restricted to safe characters before they become systemd
  unit and container names.

## Testing

```bash
ansible-lint
ansible-playbook --syntax-check molecule/default/converge.yml
molecule test
```

The Molecule scenario uses a mock Docker CLI so the role's systemd lifecycle can
be tested without running nested Docker inside the Molecule container.
