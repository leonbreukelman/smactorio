<!--
SYNC IMPACT REPORT
==================

Version Change: Template → 1.0.0 (Initial Release)

Principles Created:
-------------------
ARCHITECTURE PRINCIPLES (3):
1. Design for Simplicity
   - Charter-style tenet focused on minimal, comprehensible infrastructure
   - Baseline: Single-region, single-AZ, serverless-first for dev environment
   - Enhanced: Multi-zone with managed services for future production

2. Optimize for Frugality
   - Charter-style tenet focused on consumption-based pricing and scale-to-zero
   - Baseline: Serverless resources (Lambda, DynamoDB On-Demand, S3), lifecycle policies
   - Enhanced: Reserved capacity + serverless hybrid, right-sizing based on monitoring

3. Establish Security Foundations
   - Charter-style tenet focused on baseline security without development friction
   - Baseline: Encryption (transit/rest), IAM least privilege, Secrets Manager, security scans
   - Enhanced: GuardDuty, CloudTrail, WAF, comprehensive monitoring, MFA

CODE PRINCIPLES (3):
1. Prioritize Code Reuse
   - Favor terraform-aws-modules and existing components over new implementations
   - Embed cost-aware patterns (serverless, scale-to-zero) in reusable modules
   - Enforce via code reviews, linters (tflint), security scans (Checkov, tfsec), cost validation (Infracost)

2. Validate Infrastructure Continuously
   - Automated validation at every stage (syntax, formatting, security, cost)
   - Progressive: Manual commands (Baseline) → CI/CD automation (Enhanced)

3. Structure for Maintainability
   - Consistent file organization, centralized variables, module boundaries
   - Progressive: Simple files + local state (Baseline) → Modules + remote state (Enhanced)

IMPLEMENTATION APPROACHES (2):
1. Development-First Simplicity
   - Serverless by default, single-region/AZ, minimal networking, local state
   - Specific to Smactorio's development phase with AWS/Terraform

2. Progressive Cost Optimization
   - Measurement first, scale-to-zero patterns, incremental capability
   - Cost gates in CI/CD (Infracost integration)

Templates Requiring Updates:
----------------------------
✅ plan-template.md - Already aligned with Baseline/Enhanced patterns and Principles Check section
✅ spec-template.md - Already aligned with cost optimization and requirements approach
✅ tasks-template.md - Already aligned with tier-based approach and validation checkpoints

Command Files Requiring Updates:
--------------------------------
✅ iac.principles.prompt.md - This file (principles management workflow)
✅ iac.analyze.prompt.md - No updates needed (generic analysis workflow)
✅ iac.checklist.prompt.md - No updates needed (checklist generation workflow)
✅ iac.clarify.prompt.md - No updates needed (requirements clarification workflow)
✅ iac.implement.prompt.md - No updates needed (implementation workflow)
✅ iac.plan.prompt.md - No updates needed (planning workflow)
✅ iac.specify.prompt.md - No updates needed (specification workflow)
✅ iac.tasks.prompt.md - No updates needed (task breakdown workflow)

Deferred Items / TODOs:
-----------------------
None - All placeholders filled with concrete values

Technology Decisions:
--------------------
- Cloud Provider: AWS (serverless-first, frugal architecture)
- IaC Tool: Terraform with terraform-aws-modules
- Environment: Development only (Baseline patterns)
- Security: Baseline controls (encryption, IAM, Secrets Manager, security scans)
- Observability: Standard monitoring (CloudWatch, no enhanced managed services)
- Availability: Single-region, single-AZ (no HA/DR patterns)

Ratification:
-------------
Version: 1.0.0
Ratified: 2025-11-27
Last Amended: 2025-11-27
-->

# Smactorio Infrastructure Principles

## Cloud Architecture Principles

### Design for Simplicity

Infrastructure must remain minimal and comprehensible to accelerate development velocity and reduce cognitive overhead. For Smactorio's development environment, simplicity means avoiding unnecessary complexity that slows experimentation and learning.

**Baseline (Development)**: Use single-region, single-availability-zone architectures. Favor serverless services (AWS Lambda, API Gateway, DynamoDB) that eliminate infrastructure management. Avoid multi-tier networking, complex routing, or high-availability patterns unless specifically testing those features. Accept single points of failure in exchange for faster iteration.

**Enhanced (Future Production)**: Maintain architectural clarity while adding multi-zone deployment, load balancing, and auto-scaling. Prefer managed services over self-managed infrastructure. Document complexity trade-offs and justify each additional layer.

### Optimize for Frugality

Infrastructure costs must align with usage patterns, leveraging consumption-based pricing and scale-to-zero capabilities to minimize waste. For development workloads, frugality means aggressive cost optimization through serverless architectures and automatic resource cleanup.

**Baseline (Development)**: Prioritize serverless resources that bill only during execution (Lambda, DynamoDB On-Demand, S3). Configure auto-shutdown schedules for non-serverless resources. Use minimal instance sizes and storage tiers. Implement lifecycle policies to transition data to cost-effective storage classes (S3 Glacier for archives). Track costs with AWS Budgets and alerts.

**Enhanced (Future Production)**: Balance cost optimization with availability requirements. Use Reserved Instances or Savings Plans for baseline capacity, serverless for variable load. Implement right-sizing based on monitoring data. Maintain cost-aware defaults in reusable Terraform modules (e.g., smallest viable Lambda memory configuration, DynamoDB On-Demand vs Provisioned decisions).

### Establish Security Foundations

Security controls must protect infrastructure and data without creating friction in development workflows. For Smactorio's development environment, baseline security ensures safe experimentation while avoiding unnecessary complexity.

**Baseline (Development)**: Enforce encryption in transit (TLS 1.2+) and at rest (AES-256) for all data stores. Use AWS IAM with principle of least privilege for service-to-service communication. Store secrets in AWS Secrets Manager or Parameter Store, never in code. Implement basic network segmentation (public subnets for API Gateway, private subnets for Lambda if needed). Run security scans (Checkov, tfsec) to catch common misconfigurations. No hardcoded credentials in infrastructure code.

**Enhanced (Future Production)**: Add comprehensive security monitoring (AWS GuardDuty, CloudTrail with alerts), VPC Flow Logs, WAF for public endpoints, and automated compliance checks. Implement fine-grained IAM policies, multi-factor authentication for administrative access, and audit logging with immutable storage.

## IaC Code Principles

### Prioritize Code Reuse

Infrastructure code must favor reusing existing, tested components over creating new implementations from scratch. For Smactorio's Terraform-based AWS infrastructure, reuse accelerates development, reduces errors, and embeds cost-aware patterns into reusable modules.

**Rationale**: Code reuse enhances efficiency by reducing redundancy, minimizes errors through battle-tested components, improves maintainability via centralized updates, and accelerates development. In cost-optimized AWS environments, reuse supports consumption-based models by embedding frugal defaults (scale-to-zero, serverless-first architectures), aligning with the AWS Well-Architected Cost Optimization pillar.

**Application**:
- **Assess First**: Before writing new Terraform resources, search the Terraform Registry for `terraform-aws-modules` (e.g., `terraform-aws-modules/lambda/aws`, `terraform-aws-modules/dynamodb-table/aws`), AWS-managed services, and existing project modules.
- **Document Reuse**: Capture reused elements in module documentation, including cost implications via Infracost estimates for transparency and ease of updates.
- **Balance with Modularity**: Incorporate conditional provisioning (e.g., `count` or `for_each` for environment-specific resources) to enable scale-to-zero patterns and frugality. Avoid blind copy-paste; adapt modules to project needs.
- **Serverless Priority**: Prioritize serverless modules (Lambda, API Gateway, DynamoDB, S3) in reusable patterns to minimize idle costs and align with Smactorio's frugal philosophy.

**Examples**:
- Reuse `terraform-aws-modules/s3-bucket/aws` with lifecycle policies transitioning objects to Intelligent-Tiering or Glacier after 90 days.
- Leverage `terraform-aws-modules/lambda/aws` for serverless compute with optimized memory configurations (start at 128MB, scale as needed).
- Adapt shared utility modules for API Gateway + Lambda integrations that scale to zero between invocations.

**Enforcement**: In code reviews, flag unnecessary duplication and suggest reusable alternatives from Terraform Registry or project modules. Integrate Terraform linters (`terraform fmt`, `tflint`), security scanners (Checkov, tfsec), and cost validation (Infracost) to verify reuse aligns with frugality and security principles.

### Validate Infrastructure Continuously

Infrastructure code must be validated automatically at every stage to catch errors, misconfigurations, and security issues before deployment. For Terraform-based AWS infrastructure, continuous validation ensures code quality and prevents costly production incidents.

**Rationale**: Early validation reduces debugging time, prevents deployment failures, and enforces security and cost policies. Automated checks maintain consistent quality standards across team members and catch issues that manual reviews miss.

**Application**:
- **Syntax Validation**: Run `terraform validate` after every file modification to catch syntax errors immediately.
- **Formatting Standards**: Enforce `terraform fmt` for consistent code style across the project.
- **Security Scanning**: Integrate Checkov or tfsec in pre-commit hooks to identify security misconfigurations (unencrypted storage, overly permissive IAM policies, public S3 buckets).
- **Cost Estimation**: Run Infracost on pull requests to surface cost implications of infrastructure changes before merge.
- **Plan Review**: Generate `terraform plan` output for peer review, especially for changes affecting stateful resources (databases, storage).

**Progressive Application**:
- **Baseline**: Manual validation commands (`terraform validate`, `terraform plan`) run before commits.
- **Enhanced**: Automated validation in CI/CD pipeline with quality gates (e.g., fail build on HIGH/CRITICAL security findings, flag cost increases >20%).

### Structure for Maintainability

Infrastructure code must follow consistent organizational patterns that enhance readability, enable efficient collaboration, and prevent configuration drift. For Smactorio's development-focused Terraform codebase, structure must remain lightweight while supporting future growth.

**Rationale**: Well-structured code reduces cognitive load, accelerates onboarding, enables parallel development, and prevents conflicts. Clear organization makes it easier to locate resources, understand dependencies, and troubleshoot issues.

**Application**:
- **File Organization**: Group related resources logically (e.g., `lambda.tf` for Lambda functions, `dynamodb.tf` for DynamoDB tables, `s3.tf` for S3 buckets, `iam.tf` for IAM policies).
- **Variable Management**: Centralize variable declarations in `variables.tf` with descriptions and validation rules. Use `terraform.tfvars` for environment-specific values (avoid hardcoding in `.tf` files).
- **Module Boundaries**: Extract reusable patterns into modules under `modules/` directory when the same resource pattern appears 3+ times or serves multiple environments.
- **State Management**: Use local state for solo development; migrate to S3 backend with DynamoDB locking when collaborating or moving toward production.
- **Documentation**: Maintain `README.md` with provisioning instructions, architecture overview, and module usage examples. Use inline comments for non-obvious configurations.

**Progressive Application**:
- **Baseline (Current)**: Simple file organization (one file per resource type), local state acceptable for solo development, basic README with setup instructions.
- **Enhanced (Future)**: Module-based architecture for reusable components, remote state backend (S3 + DynamoDB), comprehensive documentation with architecture diagrams, cost estimates per module.

## Implementation Approaches

### Development-First Simplicity

Smactorio's infrastructure prioritizes rapid experimentation and learning over production-grade complexity. Development environments should enable fast iteration cycles while establishing patterns that can evolve toward production readiness.

**Decision Framework**:
- **Serverless by Default**: Choose Lambda, DynamoDB, API Gateway, and S3 unless specific requirements demand alternatives. Serverless resources scale to zero, minimize costs, and eliminate infrastructure management overhead.
- **Single-Region, Single-AZ**: Deploy to `us-east-1` (or lowest-cost region) in a single availability zone. Avoid multi-zone architectures unless testing high-availability patterns.
- **Minimal Networking**: Use VPC only when required for private resources. Leverage API Gateway and Lambda@Edge for public-facing APIs without complex load balancer setups.
- **Local State for Solo Work**: Use local Terraform state during initial development; migrate to S3 backend only when collaborating or stabilizing infrastructure.
- **Cost-Aware Defaults**: Configure smallest viable resource sizes (Lambda 128MB memory, DynamoDB On-Demand mode, S3 Intelligent-Tiering for infrequent access patterns).

**When to Apply**: Use this approach for Smactorio's current development phase, prototyping, learning experiments, and short-lived infrastructure tests.

**When to Evolve**: Transition to enhanced patterns when preparing for production, handling real user data, or requiring uptime guarantees beyond 95%.

### Progressive Cost Optimization

Infrastructure must balance frugality with functionality, starting with aggressive cost minimization and selectively adding capability as requirements emerge.

**Decision Framework**:
- **Measurement First**: Implement cost tracking (AWS Cost Explorer, Budgets, Infracost) before optimizing. Tag resources with `Environment=dev`, `Project=smactorio`, `ManagedBy=terraform` for attribution.
- **Scale-to-Zero Patterns**: Prioritize architectures that incur zero cost when idle (Lambda instead of EC2, DynamoDB On-Demand instead of provisioned capacity, S3 lifecycle policies to Glacier).
- **Incremental Capability**: Start with minimal resource configurations; scale up based on monitoring data rather than predictions. Use Lambda memory tuning, DynamoDB auto-scaling, and S3 Intelligent-Tiering to adapt to actual usage.
- **Time-Boxed Experiments**: Configure automatic resource cleanup (Lambda lifecycle policies, CloudWatch scheduled events) for experimental infrastructure to prevent cost accumulation.
- **Cost Gates in CI/CD**: Integrate Infracost into pull request workflows to surface cost implications of infrastructure changes before merge.

**When to Apply**: Use this approach throughout Smactorio's development lifecycle. Cost optimization remains relevant regardless of environment maturity.

**Trade-offs**: Accept potential performance constraints (cold starts, eventual consistency) in exchange for lower costs. Re-evaluate trade-offs when application requirements demand guaranteed performance or availability.

## Governance

**Authority and Precedence**: These principles represent the foundational governance for all Smactorio infrastructure development. They supersede individual preferences, tactical decisions, and conflicting guidance. When architectural or implementation decisions are ambiguous, these principles provide the deciding framework.

**Compliance and Accountability**: All infrastructure specifications, implementation plans, and generated Terraform code must demonstrate alignment with these principles. Code reviews verify adherence to reuse, validation, and structure principles. Automated checks (Checkov, tfsec, Infracost) enforce security and cost principles.

**Justification for Complexity**: Architectural decisions that extend beyond Baseline patterns require documented justification explaining the business or technical need. For Smactorio's development environment, complexity must serve learning objectives or specific feature validation—avoid production patterns (multi-zone, managed monitoring services, high-availability) unless explicitly testing those capabilities.

**Deviation and Exception Process**: Deviations from these principles require explicit acknowledgment and documented rationale. For solo development, self-document exceptions in code comments or ADR files. For collaborative work, deviations require peer review. Track exceptions in `docs/adr/` (Architecture Decision Records) when deviating from reuse, simplicity, or frugality principles.

**Amendment and Evolution**: These principles evolve as Smactorio's requirements, AWS capabilities, and Terraform ecosystem mature. Amendments follow semantic versioning:
- **MAJOR** (e.g., 2.0.0): Backward-incompatible changes (removing principles, redefining core philosophies)
- **MINOR** (e.g., 1.1.0): New principles added, materially expanded guidance, new implementation approaches
- **PATCH** (e.g., 1.0.1): Clarifications, wording improvements, typo fixes, non-semantic refinements

Amendments require updates to dependent templates (`plan-template.md`, `spec-template.md`, `tasks-template.md`) and command files (`iac.*.prompt.md`) to maintain consistency.

**Relationship to Operational Guidance**: These principles establish WHAT outcomes infrastructure achieves (Architecture Principles) and HOW code is written (IaC Code Principles). Operational guidance in `.github/prompts/iac.*.prompt.md` addresses day-to-day execution (planning, implementation, validation workflows). Principles remain stable across project lifecycle; operational guidance adapts to tooling updates and process refinements.

**Version**: 1.0.0 | **Ratified**: 2025-11-27 | **Last Amended**: 2025-11-27
