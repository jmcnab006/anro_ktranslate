# anro_ktranslate

Deploys Kentik `ktranslate` as an SNMP polling collector with a
Prometheus-compatible endpoint.

## Intended architecture

```
SNMP devices
    |
    v
Nagios-accessible collector host
    |
    +-- ktranslate :8082/metrics
             |
             v
       Prometheus or Alloy
             |
             v
           Grafana
```

This role is intentionally scoped to SNMP polling and Prometheus output.
Flow, syslog and other ktranslate modes should be added as separate,
explicit features after the SNMP deployment is proven.

## Why package_url is the default

The upstream release currently publishes multiple release assets. In a
managed environment, mirror the exact Ubuntu `.deb` you approve into an
internal artifact repository, record its SHA-256 checksum, and point the
role at that URL. This avoids guessing asset names and makes deployments
repeatable.

## Required variables

```yaml
anro_ktranslate_package_url: "https://repo.example.net/ktranslate_2.2.37_amd64.deb"
anro_ktranslate_package_checksum: "sha256:..."
```

Use `anro_ktranslate_install_method: preinstalled` when another role or
gold image already installs the binary.

## SNMP configuration

`anro_ktranslate_snmp_config` is rendered directly as YAML. Its top-level
sections are:

- `devices`: explicit devices, when you choose to manage them directly.
- `trap`: optional SNMP trap listener configuration.
- `discovery`: CIDRs, ports and default credentials used to discover devices.
- `global`: poll interval, profile paths, timeout, retries and enabled MIBs.

The included defaults track the structure of the upstream
`snmp-base.yaml` sample. Keep SNMP communities and SNMPv3 secrets in
Ansible Vault, not role defaults or Git.

### Minimal discovery example

```yaml
anro_ktranslate_snmp_config:
  devices: {}
  trap:
    listen: "127.0.0.1:1620"
    community: "{{ vault_ktranslate_trap_community }}"
    version: ""
    transport: ""
  discovery:
    cidrs:
      - "10.20.0.0/24"
    ignore_list: []
    debug: false
    ports: [161]
    default_communities:
      - "{{ vault_snmp_v2_community }}"
    default_v3: null
    add_devices: true
    add_mibs: true
    threads: 8
    replace_devices: true
    check_all_ips: false
    use_snmp_v1: false
  global:
    poll_time_sec: 60
    drop_if_outside_poll: false
    mib_profile_dir: "/etc/ktranslate/profiles"
    mibs_db: "/etc/ktranslate/mibs.db"
    mibs_enabled: ["IF-MIB"]
    timeout_ms: 5000
    retries: 1
    global_v3: null
    response_time: true
    ping_interval_sec: 60
    jitter_time_sec: 10
    fast_poll: false
    watch_profile_changes: false
```

## Prometheus or Alloy scrape job

```yaml
scrape_configs:
  - job_name: ktranslate
    scrape_interval: 60s
    scrape_timeout: 30s
    static_configs:
      - targets:
          - nagios01.example.net:8082
          - nagios02.example.net:8082
        labels:
          collector_type: ktranslate
```

## Deployment

```bash
ansible-playbook -i inventory examples/playbook.yml
```

## Validation

The role:

1. checks that `snmp.yaml` is valid YAML;
2. starts and enables `ktranslate.service`;
3. requests `/metrics`;
4. verifies that the response resembles Prometheus exposition text.

Useful manual checks:

```bash
systemctl status ktranslate
journalctl -u ktranslate -f
curl -s http://127.0.0.1:8082/metrics | head
```

## Scaling guidance

Start with one small CIDR and one collector. Measure:

- poll cycle duration;
- CPU and memory;
- SNMP timeout rates;
- metric series count;
- device and interface cardinality.

Then partition devices across the Nagios-accessible collectors by site or
network reachability. Avoid making every collector poll every device.

## Secrets

Example Vault variables:

```yaml
vault_snmp_v2_community: "..."
vault_ktranslate_trap_community: "..."
```

Encrypt them:

```bash
ansible-vault encrypt group_vars/ktranslate_collectors/vault.yml
```
