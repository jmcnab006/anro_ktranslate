# anro_ktranslate

Ansible role for deploying and managing **Kentik ktranslate** as an enterprise SNMP collector with a Prometheus metrics endpoint.

This role is designed to standardize ktranslate deployments across multiple monitoring collectors while maintaining a repeatable, fully tested deployment model.

---

# Features

- Ubuntu 22.04 (Jammy) support
- Ubuntu 24.04 (Noble) support
- Dedicated service account
- Systemd service
- Hardened service configuration
- Configurable SNMP polling
- Prometheus metrics endpoint
- Optional discovery
- Optional trap listener
- Supports explicit device definitions
- Supports discovery-based configuration
- Ansible Vault friendly
- Molecule test suite
- Idempotent

---

# Architecture

```
               SNMP

         Routers
         Switches
         Firewalls
         Servers
         UPS
         Printers
         IoT

              │

              ▼

        ktranslate Collector

              │

      Prometheus Endpoint
        http://:8082/metrics

              │

     Prometheus / Alloy

              │

          Grafana
```

---

# Directory Layout

```
roles/

└── anro_ktranslate/
    ├── defaults/
    ├── files/
    ├── handlers/
    ├── meta/
    ├── molecule/
    ├── tasks/
    ├── templates/
    ├── vars/
    └── README.md
```

---

# Requirements

Ubuntu

- 22.04
- 24.04

Ansible

- 2.15+

Python

- 3.10+

---

# Role Variables

## Installation

```yaml
anro_ktranslate_enabled: true

anro_ktranslate_version: "2.2.37"

anro_ktranslate_install_method: package_url

anro_ktranslate_package_url: ""

anro_ktranslate_package_checksum: ""
```

---

## Users

```yaml
anro_ktranslate_user: ktranslate

anro_ktranslate_group: ktranslate
```

---

## Configuration

```yaml
anro_ktranslate_config_dir: /etc/ktranslate

anro_ktranslate_snmp_config_path: /etc/ktranslate/snmp.yaml

anro_ktranslate_binary_path: /usr/bin/ktranslate
```

---

## Prometheus

```yaml
anro_ktranslate_prometheus_sink_enabled: true

anro_ktranslate_prometheus_listen: 0.0.0.0:8082
```

---

## Logging

```yaml
anro_ktranslate_log_level: info
```

---

## Example Playbook

```yaml
---
- hosts: monitoring

  become: true

  roles:

    - role: anro_ktranslate
```

---

# SNMP Configuration

The role renders

```
/etc/ktranslate/snmp.yaml
```

directly from

```yaml
anro_ktranslate_snmp_config
```

Example

```yaml
anro_ktranslate_snmp_config:

  devices: {}

  trap:

    listen: "127.0.0.1:1620"

    community: "{{ vault_trap_community }}"

  discovery:

    cidrs:

      - 10.10.0.0/24

    default_communities:

      - "{{ vault_snmp_community }}"

    threads: 8

  global:

    poll_time_sec: 60

    timeout_ms: 5000

    retries: 1

    response_time: true

    mibs_enabled:

      - IF-MIB
```

---

# Prometheus Scrape

Example scrape job

```yaml
scrape_configs:

- job_name: ktranslate

  scrape_interval: 60s

  static_configs:

    - targets:

      - collector01:8082

      - collector02:8082
```

---

# Service

```
systemctl status ktranslate
```

Logs

```
journalctl -u ktranslate -f
```

Metrics

```
curl http://localhost:8082/metrics
```

---

# Molecule Testing

The role includes a complete Molecule test suite for validating changes before deployment.

## Test Scenarios

```
molecule/default
```

Tests:

- Configuration rendering
- Systemd unit
- Service startup
- Prometheus endpoint
- Idempotence

```
molecule/package_install
```

Tests:

- Package installation
- Binary installation
- Configuration
- Service startup
- Endpoint validation

---

# Installing Molecule

Create a virtual environment

```bash
python3 -m venv .venv
```

Activate it

```bash
source .venv/bin/activate
```

Install requirements

```bash
pip install \
    molecule \
    molecule-plugins[docker] \
    docker \
    ansible-lint \
    yamllint \
    pytest
```

Install required Ansible collections

```bash
ansible-galaxy collection install \
    community.docker
```

Verify installation

```bash
molecule --version
```

---

# Running Tests

Run the default scenario

```bash
molecule test
```

Run a specific scenario

```bash
molecule test -s default
```

Run package installation tests

```bash
molecule test -s package_install
```

Run only convergence

```bash
molecule converge
```

Run only verification

```bash
molecule verify
```

Check idempotence

```bash
molecule idempotence
```

Run syntax checks

```bash
molecule syntax
```

Run linting

```bash
molecule lint
```

Destroy test containers

```bash
molecule destroy
```

---

# Interactive Debugging

One of the biggest advantages of Molecule is being able to stop after convergence and inspect the running container.

Create the environment

```bash
molecule create
```

Prepare it

```bash
molecule prepare
```

Apply the role

```bash
molecule converge
```

Login to the container

```bash
molecule login
```

Once inside the container

```
systemctl status ktranslate

journalctl -u ktranslate -f

cat /etc/ktranslate/snmp.yaml

cat /etc/default/ktranslate

cat /etc/systemd/system/ktranslate.service

curl http://localhost:8082/metrics
```

Exit the container

```
exit
```

Run verification

```bash
molecule verify
```

Destroy the environment

```bash
molecule destroy
```

---

# Development Workflow

Typical development cycle

```bash
source .venv/bin/activate

molecule create

molecule converge

molecule login

# Make changes

molecule converge

molecule verify

molecule idempotence

molecule destroy
```

For rapid iteration you generally do **not** need to run `molecule test` after every change. `test` destroys and recreates the environment each time. During development, use `converge`, `verify`, and `idempotence`, then run `molecule test` before committing changes.

---

# Validation Checklist

Before merging changes ensure:

- ✓ YAML renders correctly
- ✓ Ansible lint passes
- ✓ Yamllint passes
- ✓ Molecule converge passes
- ✓ Molecule verify passes
- ✓ Molecule idempotence passes
- ✓ Service starts
- ✓ `/metrics` returns HTTP 200
- ✓ Systemd unit reloads correctly
- ✓ Configuration changes trigger service restart only when necessary

---

# Production Rollout Strategy

Deploy incrementally.

1. Deploy to a development collector.
2. Validate `/metrics` output.
3. Add the collector to Prometheus or Alloy.
4. Verify metrics appear in Grafana.
5. Monitor CPU, memory, poll duration, and SNMP timeout rates.
6. Roll out to one production collector.
7. Partition devices across collectors by site, region, or network reachability.
8. Complete deployment across all monitoring collectors using the same role.

This approach keeps deployments predictable, repeatable, and easy to troubleshoot while providing a standardized configuration and test framework for future enhancements.
