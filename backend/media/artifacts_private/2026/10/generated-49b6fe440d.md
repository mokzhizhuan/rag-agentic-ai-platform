# Technical Architecture for a Django, React, Keycloak, and PostgreSQL RAG Application with Ollama and Optional OpenAI

## Overview, Scope, and Configuration-Assurance Conventions

# 1. Overview, Scope, and Configuration-Assurance Conventions

This document describes a reference technical architecture for a retrieval-augmented generation (RAG) application built with Django, React, Keycloak, PostgreSQL, Ollama, and optionally OpenAI-compatible model services. The application accepts user documents, extracts and segments their content, generates embeddings, stores searchable representations, retrieves relevant context, and produces conversational responses grounded in the indexed material. It also addresses authentication, authorization, asynchronous processing, observability, deployment, security, and operational troubleshooting.

The scope covers the principal runtime and data flows from the browser through the Django application and supporting services. It includes the React user interface, Django API and business logic, Keycloak identity and access management, PostgreSQL persistence, vector-search responsibilities, document-processing workflows, background artifact jobs, local Ollama inference, and optional external OpenAI providers. It also considers deployment configuration, service health, logging, failure handling, and controls for protecting documents, credentials, tokens, prompts, and generated responses.

The architecture is intentionally implementation-oriented without asserting project-specific facts that have not been verified. Exact Django applications, URL routes, model names, database extensions, queue technologies, container definitions, environment-variable names, model identifiers, resource limits, and deployment topology must be confirmed against the target repository and runtime environment. Where this document uses a concrete value or pattern as an example, it is illustrative rather than a claim about the deployed system.

Configuration assurance follows three classifications:

- **Verified:** directly confirmed from authoritative project artifacts, deployment manifests, runtime inspection, or documented operational evidence.
- **Illustrative:** a recommended or plausible implementation pattern used to explain architecture; it requires validation before adoption.
- **Required decision:** an unresolved design or operational choice that must be explicitly selected, documented, and tested.

These classifications should be applied to configuration snippets, service dependencies, security controls, and operational procedures. A setting should not be treated as verified merely because it is conventional for Django, React, PostgreSQL, Keycloak, Ollama, or OpenAI. For example, the presence of PostgreSQL does not by itself establish that vector search is implemented through a particular extension, schema, index type, or external vector database.

The document assumes that sensitive values such as database passwords, client secrets, signing keys, API keys, and administrator credentials are supplied through protected secret-management mechanisms rather than committed to source control. Environment variables and example configuration fragments should use placeholders and should be reviewed for secure defaults. Production readiness additionally requires confirmation of authentication flows, authorization boundaries, backup and recovery procedures, provider connectivity, model availability, data-retention requirements, and resource capacity under representative workloads.

## System Architecture and Text-Based Request/Data Flow

## 2. System Architecture and Text-Based Request/Data Flow

The application is organized as a web-based retrieval-augmented generation (RAG) system with separate presentation, application, identity, persistence, retrieval, and model-serving responsibilities. A React client provides the user interface, while Django exposes authenticated API endpoints and coordinates document management, conversational requests, retrieval, and background-job submission. Keycloak provides identity and token issuance, PostgreSQL stores application records and, where configured, vector representations, and Ollama or an optional OpenAI provider supplies embedding and chat-generation capabilities. The exact deployment topology may vary; the flow below is an architectural model rather than a claim about verified project settings.

The primary synchronous request path begins when a user authenticates through Keycloak and the React application receives an access token. The client includes that token in subsequent API requests to Django. Django validates the token according to the configured Keycloak integration, applies application-level authorization, and identifies the requesting user, tenant, or workspace as applicable. For a chat request, Django validates the input, determines the permitted document scope, creates an embedding for the query, and searches the configured vector store. Retrieved chunks and their metadata are assembled into a prompt context. Django then sends the controlled prompt to Ollama or, when explicitly configured, to an OpenAI-compatible provider. The generated answer and relevant metadata are returned to React and may also be recorded for auditing or conversation history.

Document processing generally separates the upload transaction from computationally intensive artifact creation. Django accepts and records the document, stores the source through the configured file-storage mechanism, and submits a background job. A worker parses the source, normalizes text, divides it into chunks, generates embeddings, and persists chunk metadata and vectors. Job state is updated as each stage completes, allowing the API and user interface to report pending, successful, or failed processing without blocking the upload request.

Text-based request and data flow:

User → React UI → Keycloak authentication  
React UI → Django API: bearer-token request  
Django API → Keycloak: token validation or verification  
Django API → PostgreSQL: users, documents, permissions, conversations, job state  
Django API → Embedding provider: query embedding  
Django API → PostgreSQL/vector store: similarity search  
Vector store → Django API: ranked chunks and metadata  
Django API → Ollama or optional OpenAI provider: grounded prompt  
Model provider → Django API: generated response  
Django API → React UI: answer, citations or source references, and status

For ingestion, the corresponding flow is:

React UI → Django API → file storage and PostgreSQL → background queue → worker → parser/chunker → embedding provider → vector storage

Network boundaries, queue technology, storage backends, and model endpoints should be treated as configurable deployment concerns and documented from the actual environment configuration.

## Component Responsibilities and Service Boundaries

## 3. Component Responsibilities and Service Boundaries

The application is organized around a Django backend, a React user interface, Keycloak for identity management, PostgreSQL for durable application and retrieval data, and model providers for embedding and chat generation. Each component owns a defined responsibility and communicates through explicit interfaces rather than sharing internal implementation details. This separation supports independent configuration, testing, replacement, and operational diagnosis.

**React frontend.** The React application presents authentication-aware screens for document management, ingestion status, search, and conversational interaction. It obtains and refreshes user tokens through the configured Keycloak client, attaches access tokens to API requests, and renders authorization failures without attempting to enforce server-side permissions itself. The frontend may track request and job identifiers returned by the backend, but it should not directly access PostgreSQL, model providers, filesystem storage, or administrative Keycloak interfaces.

**Django application and API layer.** Django is the system’s primary application boundary. It validates request schemas, authenticates bearer tokens, applies authorization rules, manages domain entities, and exposes APIs consumed by React. It coordinates document ingestion, retrieval, chat orchestration, and background-job submission. Django is responsible for business decisions such as whether a user may view a document or use a conversation, while delegated services perform specialized work. API responses should expose stable domain-level contracts rather than database-specific structures or provider-specific response formats.

**Persistence layer.** PostgreSQL is the system of record for users’ application metadata, document records, processing state, chunks, embeddings where supported by the selected database design, conversations, messages, and job status. Database access is mediated by Django models, repositories, or service functions. The database does not call Keycloak or model providers, and external services must not receive unrestricted database credentials. Transactions should protect state transitions and ensure that partially completed ingestion or job operations remain observable and recoverable.

**Keycloak.** Keycloak owns identity lifecycle functions, credential handling, token issuance, realm and client configuration, and optionally group or role claims. Django treats validated token claims as authentication input, then maps subjects, roles, groups, or other claims to application permissions. Keycloak is not the authority for document ownership or application workflow state; those decisions remain in Django and PostgreSQL.

**Model-provider boundary.** Ollama and the optional OpenAI integration are accessed through a provider abstraction owned by the backend. This abstraction normalizes chat and embedding operations, configuration lookup, timeouts, errors, and response handling. Provider credentials and endpoints remain server-side. The application should be able to select a provider without requiring React or domain code to understand provider-specific protocols.

**Background workers and operational services.** Long-running parsing, embedding, artifact generation, or cleanup operations should execute outside synchronous HTTP requests through the configured queue and worker process. Workers use the same domain services and persistence rules as the API, while job state remains visible through Django APIs. Logging, metrics, health checks, and tracing observe component interactions without becoming a substitute for authorization or workflow control.

## Authentication, Authorization, and Keycloak Integration Flow

## 4. Authentication, Authorization, and Keycloak Integration Flow

Keycloak provides centralized identity and access management for the React client and Django API. The recommended integration uses OpenID Connect (OIDC) with the Authorization Code flow and Proof Key for Code Exchange (PKCE). React acts as a public client and therefore must not contain a client secret. Django acts as a protected resource server, validating access tokens issued by the configured Keycloak realm before serving API requests.

A typical login sequence is:

1. The user selects **Sign in** in the React application.
2. React redirects the browser to Keycloak’s authorization endpoint with the client identifier, redirect URI, requested scopes, state value, nonce, and PKCE challenge.
3. Keycloak authenticates the user and applies configured realm policies, including password, multifactor, or external identity-provider requirements.
4. Keycloak redirects the browser back to React with an authorization code.
5. React exchanges the code and PKCE verifier through the OIDC client library and receives tokens.
6. React sends the access token in the `Authorization: Bearer <token>` header for API requests.
7. Django validates the token signature and claims using Keycloak’s OIDC discovery metadata and published JSON Web Key Set (JWKS).
8. Django maps the authenticated subject and approved claims to application permissions, then processes or rejects the request.

The access token should be short-lived and used only for API authorization. Refresh-token handling should follow the selected OIDC library’s secure storage and rotation behavior; browser storage choices must be evaluated against cross-site scripting risk. The application should not place client secrets, refresh tokens, or administrative credentials in React source code or build-time public variables. Logout should terminate the local application session and, where required by policy, redirect the user through Keycloak’s end-session endpoint.

Django authorization should be enforced server-side, independently of UI visibility. Token validation normally includes the signature, issuer, expiration, not-before time, and intended audience or authorized-party claims. The API should also verify that the token uses an accepted algorithm and reject malformed, unsigned, or incorrectly issued tokens. A token proving identity is not automatically sufficient to access every document, conversation, or administrative endpoint.

Keycloak roles and groups can represent coarse-grained permissions such as user, analyst, or administrator. Django may read realm roles, client roles, or group claims and translate them into application-level permissions. Resource-level checks remain necessary: for example, a user may be allowed to query the system but not retrieve another user’s private documents. Authorization decisions should be made from the validated token and server-side ownership or tenancy records, not from client-supplied user identifiers.

Illustrative configuration values include the Keycloak issuer URL, realm name, OIDC client ID, permitted redirect URIs, post-logout redirect URIs, API audience, and role claim paths. These values are deployment-specific and must be aligned between Keycloak, React, Django, and any reverse proxy. Exact names, claim mappings, and token lifetimes should be verified against the deployed realm rather than assumed from this architecture.

## Document Ingestion, Parsing, Chunking, and Metadata Management

## 5. Document Ingestion, Parsing, Chunking, and Metadata Management

Document ingestion converts user-supplied files into normalized text and structured records that can be embedded and retrieved. The ingestion boundary should accept only explicitly supported formats, validate file size and content type, assign a document identifier, and associate the document with its owning user, tenant, or permission scope. Upload metadata should be recorded before processing begins so that failed or incomplete operations remain observable. The application should treat client-provided filenames and MIME types as untrusted values; detected file characteristics and server-side validation must determine how the content is processed.

A typical ingestion flow is: React submits the file to a Django API; Django authenticates the request and creates a document record; the original file is stored in the configured file store; a background job parses and normalizes the content; the resulting text is segmented into chunks; and each chunk is sent for embedding and persistence. Parsing should occur outside the synchronous request path for large files or computationally expensive formats. The document record should expose explicit lifecycle states such as pending, processing, ready, and failed, with an error field suitable for diagnostics without disclosing sensitive content.

Format-specific parsers should preserve meaningful structure where possible. Plain text and Markdown can generally be normalized directly, while PDF, word-processing, spreadsheet, and HTML inputs may require dedicated extraction and cleanup logic. The parser should remove irrelevant control characters, normalize line endings and whitespace, and preserve headings, page or section boundaries, tables, and source locations when these improve citation or retrieval context. Malformed, encrypted, password-protected, or unsupported files should fail predictably and should not be silently indexed as empty documents.

Chunking should balance retrieval precision against sufficient context for generation. A configurable strategy may split by headings and paragraphs first, then apply a maximum character or token limit with controlled overlap. The limits, overlap, tokenizer, and separator rules are deployment configuration rather than universal constants and should be documented as illustrative unless verified against the implementation. Each chunk should retain its document identifier, sequence number, text, and location information, such as page, heading, or character range. Stable chunk identifiers support reprocessing, deletion, and deduplication.

Metadata must be consistent across relational records, vector records, and job payloads. Recommended fields include tenant or owner scope, document status, source filename, media type, content hash, parser version, chunking version, creation and update timestamps, and optional business labels. Access-control metadata must be applied as a retrieval filter, not merely displayed after search. Re-ingestion should either replace the prior version atomically or maintain explicit document versions, preventing stale chunks from remaining searchable after an update or deletion. All temporary files and intermediate artifacts should follow defined retention and access-control policies.

## Embedding Generation, Vector Storage, and Retrieval Pipeline

## 6. Embedding Generation, Vector Storage, and Retrieval Pipeline

The embedding pipeline converts document chunks into numerical vectors that support semantic similarity search. After ingestion, each chunk is submitted to the configured embedding provider, such as an Ollama-served embedding model or an optional external provider. The embedding model and dimensionality must remain consistent for all vectors within a collection. Changing either generally requires re-embedding affected documents rather than mixing incompatible vectors.

Embedding generation should be performed asynchronously for sizeable uploads or batch imports. A background job receives the chunk identifier, retrieves the normalized text, invokes the embedding service, and records the resulting vector together with model metadata, source-document identifiers, chunk position, and processing status. Transient provider failures should be retried with bounded backoff. Permanent failures should be retained as explicit job and chunk errors so that incomplete indexing is visible rather than silently treated as successful.

PostgreSQL can provide vector persistence through the `pgvector` extension. A typical logical record includes the chunk text, an embedding column, document and tenant ownership fields, page or section references, token or character counts, and timestamps. Relational metadata remains authoritative for access control and lifecycle operations, while the vector column supports nearest-neighbor search. Index selection and tuning depend on dataset size and workload; approximate indexes such as HNSW or IVFFlat may be considered, but the selected option should be treated as deployment configuration and verified against the installed PostgreSQL and `pgvector` versions.

Retrieval begins when the authenticated user submits a question. The application may normalize the query, apply conversational context, and generate a query embedding using the same embedding configuration used for indexed content. The search query must constrain candidates by authorization scope before or during similarity search. At minimum, filters should enforce tenant, collection, document status, and deletion state. Returning semantically similar content without these predicates creates a data-isolation risk, even when the similarity calculation itself is correct.

The retriever selects a configurable number of candidates, optionally applies a similarity threshold, and may perform metadata filtering, deduplication, or reranking. Results should preserve citations such as document name, page, section, and chunk identifier so the generation layer can present traceable evidence. A no-result outcome should be represented explicitly; the chat service should not infer that missing context proves an answer is unavailable.

Illustrative configuration values—not verified project settings—might include an embedding provider name, model identifier, candidate count, similarity threshold, and reranker toggle. These values should be supplied through environment-specific configuration, recorded with indexing metadata, and reviewed whenever models or database indexes change. Operational logging should capture provider status, job outcomes, query latency, and result counts without logging sensitive document text by default.

## Chat Generation with Ollama and Optional OpenAI Providers

## 7. Chat Generation with Ollama and Optional OpenAI Providers

The chat-generation service converts an authenticated user’s question and retrieved document context into a response. The Django backend should orchestrate this process rather than allowing the React client to call Ollama or OpenAI directly. A typical request includes the conversation identifier, user message, retrieval parameters, and any response-format options. The backend validates authorization, retrieves relevant chunks through the vector-search pipeline, constructs a provider-neutral prompt, and sends the request to the selected language-model provider.

Ollama is the default local or self-hosted provider when data-residency, cost, or offline operation is important. The application communicates with the Ollama HTTP API through a configurable internal endpoint. The selected model name, request timeout, maximum output size, temperature, and context-window assumptions should be supplied through deployment configuration rather than hard-coded. Ollama model availability is an operational prerequisite; a configured model name does not guarantee that the model has been downloaded or is compatible with the requested context size.

An optional OpenAI provider can be enabled for deployments that require hosted model access or additional model capabilities. Its API key must remain server-side, preferably in a secrets manager or protected environment variable, and must never be returned to the browser or written to application logs. Provider selection should be controlled by an allow-listed configuration value, such as `ollama` or `openai`, with explicit behavior when the selected provider is unavailable. A fallback from one provider to another should not occur silently when privacy, cost, or jurisdictional constraints apply; it should be an explicit policy with auditable logging.

The prompt builder should separate system instructions, conversation history, retrieved context, and the current question. Retrieved text should be labeled as untrusted reference material so that instructions embedded in documents cannot override application rules. The system prompt should require the model to ground factual answers in the supplied context, identify insufficient evidence, and preserve document references or chunk identifiers needed for citations. Conversation history should be bounded or summarized to avoid exhausting the model context window. Sensitive content should be minimized before transmission to an external provider, subject to the deployment’s privacy policy.

Generation responses should be normalized into a provider-independent structure containing the answer, citations, model/provider metadata, token or usage information when available, and finish status. Streaming may be exposed through an authenticated Django endpoint, but partial output must still be associated with the requesting conversation and terminated when authorization, timeout, or provider checks fail. The backend should apply timeouts, bounded retries for transient failures, rate limits, and cancellation handling. Provider errors should produce a safe user-facing message while preserving correlation identifiers and diagnostic details in protected logs. Configuration values in this section are illustrative unless verified against the deployed project.

## Background Artifact Jobs, Queues, Scheduling, and Job State Management

## 8. Background Artifact Jobs, Queues, Scheduling, and Job State Management

Background processing separates time-consuming artifact generation from synchronous HTTP requests. Typical artifacts include parsed document content, normalized metadata, text chunks, embeddings, vector-store records, previews, and cleanup results. The Django application should accept and validate the request, create a durable job record, enqueue work, and return a job identifier. Workers then execute the task independently while the React client retrieves status through an authenticated endpoint or receives an application-level notification where such functionality is configured.

A queue broker and worker system should be treated as deployment dependencies rather than as components implicitly provided by Django. The selected implementation may use a task library with a broker and result backend, but the exact broker, worker command, retry policy, and persistence model must be confirmed from the project configuration. Queue messages should contain stable identifiers and operation parameters, not large document payloads or credentials. Workers should retrieve source files and related database records using those identifiers, which reduces message size and allows authorization and existence checks to remain centralized.

Job state should be represented explicitly and durably. A practical lifecycle is `queued`, `running`, `succeeded`, `failed`, `cancel_requested`, and `cancelled`, with optional `retrying` or `partially_succeeded` states for multi-stage workflows. Each job should record its operation type, subject or document identifier, creation and update timestamps, attempt count, worker-visible error information, and a safe progress value when progress can be calculated reliably. State transitions should be constrained so that stale workers cannot overwrite a terminal result with an earlier state. Database transactions should cover job creation and any related ownership or document updates that must remain consistent.

Artifact workflows should be idempotent. A retry may occur after a worker completes an external operation but before its acknowledgment reaches the queue, so rerunning the task must not create duplicate chunks, embeddings, or artifact records. Deterministic keys, unique database constraints, upsert behavior, and stage-level completion markers provide protection. External model calls should use bounded timeouts, controlled retry counts, and backoff. Permanent failures should preserve a diagnostic summary without exposing provider secrets or document contents through the API.

Scheduling is appropriate for periodic maintenance rather than request-specific work. Examples include removing expired temporary files, reconciling incomplete jobs, pruning obsolete embeddings, and checking queue or provider health. Scheduled tasks require protection against overlapping executions, especially when multiple application instances are deployed. A lock, database lease, or scheduler guarantee should be selected and documented.

The API should expose only job information authorized for the requesting user or tenant. Status polling should distinguish “not found” from unauthorized access without leaking object existence where that distinction is sensitive. Administrative retry and cancellation operations require separate authorization. Worker logs should include correlation identifiers and job identifiers, while avoiding full prompts, source text, tokens, and secrets. Configuration values for queue endpoints, concurrency, schedules, retry limits, and timeouts are deployment-specific and should be documented as illustrative until verified in the target environment.

## Monitoring, Logging, Tracing, Health Checks, and Operational Metrics

## 9. Monitoring, Logging, Tracing, Health Checks, and Operational Metrics

Operational visibility should cover the full request path: React interactions, Django API requests, Keycloak authentication, PostgreSQL and vector-store access, document-processing jobs, embedding generation, and chat-generation providers such as Ollama or OpenAI. Monitoring configuration should be environment-specific and should distinguish illustrative settings from verified project behavior. Production systems should define retention, access control, alert ownership, and escalation procedures before enabling detailed telemetry.

Application logs should be structured, preferably as JSON, so that events can be searched and aggregated consistently. Each request should include a correlation or request identifier, timestamp, severity, route, authenticated subject identifier where appropriate, response status, and duration. Logs for ingestion and artifact jobs should additionally record document or job identifiers, current state, attempt number, queue or worker context, and a concise failure category. Provider interactions should record the provider name, model configuration identifier, operation type, latency, and outcome, but not prompt contents, retrieved document text, access tokens, or sensitive metadata. Exception logs should include stack traces in controlled environments while avoiding duplicate reporting across middleware and worker boundaries.

Metrics should describe both system health and user-visible behavior. Useful counters include HTTP responses by status class, authentication failures, document-processing outcomes, embedding failures, retrieval failures, generation failures, queue retries, and dead-lettered or permanently failed jobs. Histograms should measure API latency, database queries where supported, queue wait and execution time, embedding duration, retrieval duration, and model response duration. Gauges can represent active workers, queue depth, in-progress jobs, database connection utilization, and provider availability. Token or request usage metrics may be collected for cost and capacity planning when supported, subject to privacy requirements. Labels must remain bounded; identifiers such as document IDs or user IDs should not be used as unrestricted metric labels.

Distributed tracing is valuable for correlating a browser request with Django views, database operations, background jobs, and external model calls. Trace propagation should continue across queue boundaries when the job system supports it. Spans should identify major stages—authentication, retrieval, prompt construction, generation, persistence, and artifact creation—without storing confidential payloads by default. Sampling should be configurable, with temporary increases during incident investigation.

Health endpoints should distinguish liveness from readiness. Liveness should indicate that the process is responsive and should not depend on external services. Readiness should verify required dependencies, such as PostgreSQL, the vector store, Keycloak discovery or token-validation prerequisites, and the configured model provider, using bounded timeouts. Optional providers should not make the service unavailable when they are intentionally disabled. Alerts should focus on sustained error rates, latency degradation, failed readiness checks, growing queue depth, repeated job failures, storage exhaustion, and provider unavailability, with runbooks linked to each alert.

## Security, Privacy, Data Protection, and Threat Mitigations

## 10. Security, Privacy, Data Protection, and Threat Mitigations

Security controls should be applied across the React client, Django API, Keycloak identity provider, PostgreSQL database, vector-search components, background workers, and model providers. The deployment should use TLS for browser-to-API, API-to-Keycloak, database, and externally hosted model-provider connections where supported. Secrets, signing keys, database credentials, and provider API keys must be supplied through a managed secret store or protected environment configuration rather than committed to source control, embedded in frontend assets, or written to application logs.

Authentication should be delegated to Keycloak using a supported OpenID Connect flow. Access tokens must be validated for issuer, signature, audience, expiry, and required claims before a request is authorized. Django endpoints should enforce authorization independently of the user interface; hiding a React control is not an access-control mechanism. Roles, groups, or claims should be mapped to explicit application permissions, including document upload, document deletion, administration, chat access, and access to tenant- or project-specific data. Authorization checks must also be applied to retrieved chunks and generated artifacts so that a user cannot infer or cite documents outside their permitted scope.

Document content is potentially sensitive and should be treated as untrusted data. Upload endpoints should enforce authenticated access, permitted file types, size and quantity limits, safe filenames, and request-rate limits. Files should be stored outside executable paths with restrictive permissions, and parsing should occur in an isolated worker where feasible. Parsers and converters should be kept current, and malformed files, decompression bombs, embedded scripts, macros, and unexpected external references should be handled defensively. Content extracted from documents must not be treated as instructions to the application, system prompt, tools, or model; prompt-injection resistance requires separating trusted instructions from retrieved text and limiting model-enabled actions.

Data protection should cover original files, extracted text, metadata, embeddings, chat prompts, responses, job records, and operational logs. Retention periods should be defined for each category, with deletion procedures that address database rows, object storage, vector records, caches, queues, backups, and derived artifacts. Logs should exclude document text, tokens, credentials, and unnecessary personal data. Where application requirements permit, identifiers should be pseudonymized, and database and storage encryption should be enabled according to the hosting environment. Data sent to Ollama or an optional OpenAI provider must be governed by an explicit provider policy, including approval, contractual requirements, regional constraints, retention behavior, and whether prompts or documents may leave the deployment boundary.

Threat mitigations should include CSRF protection where cookie-based authentication is used, strict CORS and security headers, output encoding, parameterized database queries, dependency and image scanning, and controlled administrative access. Model responses should be presented as untrusted output, with citations or source references validated against authorized retrieved material. Security events such as repeated authentication failures, privilege changes, suspicious uploads, unauthorized access attempts, and abnormal job activity should be auditable without exposing protected content. Regular reviews should confirm that configuration, permissions, provider settings, and deletion behavior remain consistent with organizational privacy and security requirements.

## Deployment Architecture, Environment Configuration, and Deployment Checklist

## 11. Deployment Architecture, Environment Configuration, and Deployment Checklist

The application should be deployed as separately managed web, worker, data, and identity services. A typical production topology places a reverse proxy or ingress controller at the public boundary, forwarding requests to the Django API and serving or routing the React frontend. Django communicates with PostgreSQL for application data and vector metadata, Keycloak for identity and token validation, and Ollama or an optional OpenAI-compatible provider for embedding and chat generation. Background workers process ingestion and artifact jobs without blocking API requests. A queue or broker is required when asynchronous execution is enabled. Exact container names, ports, scaling rules, and orchestration manifests are project-specific and must be verified against the deployment repository.

Configuration should be supplied through environment variables or a managed secrets store rather than committed files. Illustrative settings include `DJANGO_SETTINGS_MODULE`, `DJANGO_SECRET_KEY`, `DATABASE_URL`, `KEYCLOAK_ISSUER_URL`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`, `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBEDDING_MODEL`, and an optional `OPENAI_API_KEY`. Provider selection, model identifiers, chunking parameters, retrieval limits, allowed origins, cookie security, logging levels, and worker concurrency should also be configurable. Development defaults must not be reused in production: disable Django debug mode, restrict hosts and CORS origins, enforce HTTPS, use secure cookies, and configure appropriate proxy-header handling.

PostgreSQL should use persistent, access-controlled storage and a documented backup and restore process. Ollama requires sufficient compute and persistent model storage; model availability should be validated during deployment rather than assumed. Keycloak configuration must include the correct realm, client type, redirect origins, audience or issuer validation, and service-account permissions where applicable. External OpenAI usage should be explicitly enabled, with outbound network access, credential rotation, provider policy, and data-handling implications reviewed.

Deployment should proceed in controlled stages:

1. Confirm supported runtime, container images, dependency locks, migration procedures, and required model names.
2. Provision private network connectivity among Django, workers, PostgreSQL, Keycloak, the queue, and model providers.
3. Create production secrets in the approved secret-management system and verify file or environment permissions.
4. Initialize PostgreSQL, apply Django migrations, and create only the required administrative accounts.
5. Configure Keycloak clients, redirect URIs, scopes, claims, and role mappings; test token validation against the deployed issuer.
6. Start the API, frontend, workers, scheduler, and reverse proxy with persistent volumes where data or models require them.
7. Verify readiness and liveness endpoints, database connectivity, queue consumption, model reachability, document ingestion, retrieval, and chat responses.
8. Confirm logs and metrics exclude tokens, document contents, API keys, and other sensitive data.
9. Exercise backup, restore, rollback, and graceful shutdown procedures before production traffic is enabled.
10. Record the deployed image versions, configuration source, migrations, model revisions, and operational owner for audit and future troubleshooting.

## Troubleshooting Guide, Failure Modes, and Diagnostic Procedures

## 12. Troubleshooting Guide, Failure Modes, and Diagnostic Procedures

Troubleshooting should proceed from the outside inward: confirm service availability, verify configuration and authentication, inspect request and job state, and then examine data or model-specific behavior. Begin by identifying the affected path—browser-to-API, API-to-PostgreSQL, API-to-Keycloak, ingestion, retrieval, generation, or background processing. Record the request or job identifier, timestamp, authenticated subject, document identifier, and relevant deployment version before changing configuration or retrying operations.

**Frontend or API availability failures** commonly result from incorrect API URLs, reverse-proxy routing, CORS policy, expired browser tokens, or unavailable Django workers. Check browser network errors and the API health endpoint, then inspect proxy access logs and Django application logs using the same correlation identifier where available. A successful frontend load does not demonstrate API availability. If requests return `401` or `403`, distinguish token expiration from missing roles or permissions; decode tokens only in a controlled diagnostic context and never log access or refresh tokens. For `404` or `405` responses, verify URL prefixes, HTTP methods, and proxy path rewriting.

**Keycloak authentication failures** should be investigated by checking issuer URL, realm, client identifier, redirect URI, audience, and clock synchronization. Confirm that the API validates tokens against the intended realm and that users or service accounts possess the roles expected by the application. A valid login can still produce authorization failures when role mappings, scopes, or audience claims are incorrect. Review Keycloak event logs and Django authentication logs without exposing token contents.

**Database and ingestion failures** may appear as connection errors, transaction rollbacks, duplicate records, unsupported file types, parser exceptions, or incomplete metadata. Verify database reachability, credentials, migrations, available storage, and connection-pool limits. For a failed document, inspect its persisted status and error detail, confirm whether a transaction left partial records, and determine whether retrying is safe. Reprocessing should be idempotent or should explicitly remove and rebuild prior chunks, embeddings, and derived artifacts. Preserve the original file and metadata when possible so parser behavior can be reproduced.

**Retrieval and chat failures** require separating empty retrieval from generation failure. Inspect query normalization, embedding-provider configuration, vector index availability, filtering metadata, returned similarity scores, and the final prompt context. An empty result may indicate missing embeddings, an overly restrictive filter, incompatible embedding dimensions, or a legitimate absence of relevant content. If retrieval succeeds but generation fails, check Ollama availability, model selection, resource capacity, request timeouts, and optional OpenAI credentials and quotas. Do not silently switch providers without recording that behavior.

**Background-job failures** should be diagnosed from queue connectivity, worker logs, job state transitions, retry counts, and dead-letter or failed-job storage. Confirm that scheduled tasks are not duplicated across replicas and that workers use the same environment, database, and storage configuration as the web process. After remediation, retry only jobs whose inputs remain valid, and monitor for repeated failures rather than treating a single successful retry as resolution.
