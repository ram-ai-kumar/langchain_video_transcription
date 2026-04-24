# Documentation

Central documentation hub for the Video Transcription & Study Material Generator.

For a high-level business or compliance overview, see the [Main README](../README.md).

---

## Architecture (`architecture/`)

System design, security posture, and compliance reference:

| Document                                                                | Contents                                                                                                 |
| ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| [ARCHITECTURE.md](./architecture/ARCHITECTURE.md)                       | Layered architecture, component design, patterns, technology stack                                       |
| [PROCESSING_ARCHITECTURE.md](./architecture/PROCESSING_ARCHITECTURE.md) | Three-pass processing pipeline, sequential processing                                                    |
| [ENTERPRISE_SCALABILITY.md](./architecture/ENTERPRISE_SCALABILITY.md)   | Scalability mechanisms, lazy-loading, hardware sizing guidance                                           |
| [SECURITY.md](./architecture/SECURITY.md)                               | Zero Trust Architecture, input validation, GRC mappings (SOC2 / ISO27001 / NIST / PCI DSS / CIS / OWASP) |
| [OWASP_LLM_TOP_10.md](./architecture/OWASP_LLM_TOP_10.md)               | AI-specific threat mitigations mapped to OWASP LLM Top 10                                                |

## Features (`features/`)

| Document                              | Contents                                                                              |
| ------------------------------------- | ------------------------------------------------------------------------------------- |
| [FEATURES.md](./features/FEATURES.md) | Full feature list including Unicode support, error recovery, mixed media intelligence |

## Setup (`setup/`)

| Document                                     | Contents                                        |
| -------------------------------------------- | ----------------------------------------------- |
| [SETUP.md](./setup/SETUP.md)                 | Installation: virtualenv and Docker options     |
| [PREREQUISITES.md](./setup/PREREQUISITES.md) | System requirements and dependency installation |
| [MIGRATION.md](./setup/MIGRATION.md)         | Upgrade guide for existing deployments          |

## Usage (`usage/`)

| Document                     | Contents                                                                                             |
| ---------------------------- | ---------------------------------------------------------------------------------------------------- |
| [USAGE.md](./usage/USAGE.md) | Supported media types, running the pipeline, CLI options, config file, customization, example output |

## Guides (`guides/`)

| Document                                                            | Contents                                                                    |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| [PERFORMANCE_OPTIMIZATION.md](./guides/PERFORMANCE_OPTIMIZATION.md) | Device selection (CUDA/MPS/CPU), Whisper model selection, enterprise tuning |
| [ENGINEERING_EXCELLENCE.md](./guides/ENGINEERING_EXCELLENCE.md)     | Code quality standards, testing practices, development workflow             |

## Reference (`reference/`)

| Document                             | Contents                                                |
| ------------------------------------ | ------------------------------------------------------- |
| [TODO.md](./reference/TODO.md)       | Planned improvements and open tasks                     |
| [ROADMAP.md](./reference/ROADMAP.md) | Long-term architecture evolution: SOA and DDD proposals |

---

## Quick Start by Role

### Engineering & DevOps

1. [PREREQUISITES.md](./setup/PREREQUISITES.md) — install dependencies
2. [SETUP.md](./setup/SETUP.md) — choose `.venv` or Docker
3. [USAGE.md](./usage/USAGE.md) — run the pipeline

### Enterprise Architects & Security Officers

1. [SECURITY.md](./architecture/SECURITY.md) — full GRC and ZTA reference
2. [OWASP_LLM_TOP_10.md](./architecture/OWASP_LLM_TOP_10.md) — AI threat mitigations
3. [ENTERPRISE_SCALABILITY.md](./architecture/ENTERPRISE_SCALABILITY.md) — scalability and hardware sizing
4. Security testing evidence: [`tests/docs/`](../tests/docs/)

### Performance Tuning

- [PERFORMANCE_OPTIMIZATION.md](./guides/PERFORMANCE_OPTIMIZATION.md) — GPU setup, model selection

---

## Security Testing Evidence

Comprehensive security testing documentation is in [`tests/docs/`](../tests/docs/):

- [SECURITY_TESTING_DOCUMENTATION.md](../tests/docs/SECURITY_TESTING_DOCUMENTATION.md)
- [SECURITY_COMPLIANCE_SUMMARY.md](../tests/docs/SECURITY_COMPLIANCE_SUMMARY.md)
- [TESTING_DOCUMENTATION.md](../tests/docs/TESTING_DOCUMENTATION.md)

**Test coverage**: 48+ passing tests · 41+ security tests · 70+ attack vectors · OWASP 5/10 · CIS 4/18 · PCI DSS 4/12
