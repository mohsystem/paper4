# Representative security findings
<!-- \label{app:validated_examples} -->

This appendix presents representative samples from the security review report. The examples are selected to illustrate recurring weakness patterns across the major CWE families observed in the study, covering both pre-training and post-training submissions. Each example includes the code fragment as confirmed by the reviewers, a description of the security issue, and the recommended mitigation. All samples are anonymized.

## A.1 Authentication and Access Control

**Example 1: Global permit-all security rule (CWE-306, pre-training, Critical)**

Multiple pre-training submissions configured Spring Security with a catch-all rule that left every endpoint in the application publicly reachable without authentication. This pattern was the single most frequent Critical finding in the study and meant that administrative endpoints, credential-management flows, and user-data routes were all accessible to anonymous callers.

```java
http.authorizeHttpRequests(auth -> auth
    .anyRequest().permitAll()
);
```

*Impact.* Any unauthenticated caller can invoke every route in the application, including admin operations and credential endpoints.
*Mitigation.* Replace `.anyRequest().permitAll()` with `.anyRequest().authenticated()` and explicitly allow only routes that are intended to be public.

**Example 2: Caller-controlled user identifier in password change flow (CWE-639, pre-training, Critical)**

A password-change endpoint accepted a user identifier from a client-supplied HTTP header rather than deriving it from the authenticated session. This allowed any caller to change any account's password by manipulating the header value, enabling direct account takeover without authentication.

```java
@PostMapping("/change-password")
public ResponseEntity<?> changePassword(
    @RequestHeader("X-USER-ID") Long userId,
    @RequestBody ChangePasswordRequest request) {
```

*Impact.* Any network-reachable caller can reset any user's password by supplying an arbitrary `X-USER-ID` header value.
*Mitigation.* Derive the user identifier from the authenticated principal (session or token), never from a client-supplied header.

**Example 3: Publicly reachable API-key management endpoints (CWE-639, pre-training, Critical)**

API-key issuance, listing, and revocation endpoints were placed under a `permitAll()` rule. Because no ownership check was performed, an unauthenticated caller could issue, list, or revoke API keys belonging to arbitrary users.

```java
.requestMatchers("/api/auth/api-keys/**").permitAll()
```

*Impact.* Unauthenticated manipulation of any user's API keys, enabling unauthorized external-system access.
*Mitigation.* Require authentication; derive the owner from the authenticated principal; verify key ownership before any operation.

## A.2 Credential and Secret Handling

**Example 1: Password-reset token returned in the HTTP response (CWE-201, pre-training, Critical)**

The password-reset request endpoint returned a live reset token directly in the API response body. This token should be delivered only through an out-of-band channel (\eg email); including it in the response exposes the credential to any client or intermediary.

```java
return new ResetRequestResponse("RESET_REQUESTED", tokenValue);
```

*Impact.* Any caller who triggers a reset request obtains a valid token that can be used to reset the target account's password.
*Mitigation.* Never include reset tokens in API responses; deliver them only through the intended out-of-band recovery channel.

**Example 2: Session tokens stored in plaintext (CWE-312, pre-training, High)**

The session-token entity stored the raw token string in a database column. A database breach would expose all valid session tokens, enabling session hijacking for every active user.

```java
@Column(nullable = false, unique = true, length = 64)
private String token;
```

*Impact.* Database compromise yields all valid session tokens; attacker can impersonate any active user.
*Mitigation.* Hash tokens before storage (\eg SHA-256) and compare the hash on lookup.

**Example 3: Hard-coded JWT signing secret (CWE-321, post-training, Critical)**

The JWT signing secret was a hard-coded placeholder value committed in application properties and used directly for signing and verifying tokens. An attacker who reads the source can forge arbitrary JWT tokens.

```properties
app.security.jwt.secret=CHANGE_ME_TO_A_LONG_RANDOM_SECRET_AT_LEAST_32_CHARS
```

*Impact.* Attacker with access to the source can forge valid JWTs and impersonate any user.
*Mitigation.* Load the JWT signing key from a protected secret source and fail startup if a default or placeholder value is present.

## A.3 Logging and Information Exposure

**Example 1: Plaintext request logging of secrets to a flat file (CWE-312, post-training, High)**

A request-logging filter persisted partially redacted request bodies to a flat file. Because the redaction was incomplete, bootstrap secrets and credential values appeared in the log, creating a secondary exposure channel.

```java
Files.writeString(LOG_FILE, sb.toString(),
    StandardCharsets.UTF_8,
    StandardOpenOption.CREATE,
    StandardOpenOption.APPEND);
```

*Impact.* Sensitive credentials and secrets accumulate in a flat file accessible to anyone with filesystem read access.
*Mitigation.* Exclude request bodies from persistent logging, or implement complete redaction of sensitive fields before writing.

<!--
**Example 2: SQL statement logging enabled in configuration (CWE-532, pre-training, Low)**

Hibernate SQL statement logging was enabled in the application configuration. In a deployment context, this can place query text containing user data or sensitive parameters into application logs or stdout.

```properties
spring.jpa.show-sql=true
```

*Impact.* Queries containing user data or sensitive values appear in application logs.
*Mitigation.* Disable SQL statement logging outside development environments by creating a ready to use profile for production.
-->

## A.4 External Integration and Parser Safety

**Example 1: LDAP injection via unsanitized domain component (CWE-90, pre-training, High)**

The enterprise directory lookup endpoint concatenated a caller-supplied domain-component parameter directly into an LDAP base DN string without validation or escaping. An attacker can inject LDAP metacharacters to redirect the search to an arbitrary directory context or extract additional records.

```java
StringBuilder sb = new StringBuilder();
sb.append("dc=").append(dc);
```

*Impact.* Attacker-controlled LDAP query redirects the directory search, potentially exposing unauthorized directory entries.
*Mitigation.* Validate and allowlist the `dc` parameter; reject values with LDAP metacharacters; apply RFC~4514 DN escaping.

**Example 2: XML external entity processing not disabled (CWE-611, pre-training, Critical)**

The legacy XML user-import endpoint parsed user-uploaded XML using Jackson's `XmlMapper` without explicitly disabling external entity processing. An attacker can craft an XML payload that reads local files or triggers server-side request forgery.

```java
XmlMapper xmlMapper = XmlMapper.builder().build();
```

*Impact.* Attacker-controlled XML can read arbitrary server files or initiate outbound requests.
*Mitigation.* Explicitly configure the XML parser to disable DTD processing and external entity resolution.

**Example 3: Weak PRNG for generated passwords (CWE-338, post-training, High)**

A legacy user-import service generated temporary passwords using `SplittableRandom` seeded with the current system time in milliseconds. An attacker who knows the approximate import time can predict the generated passwords.

```java
SplittableRandom rnd = new SplittableRandom(
    Instant.now().toEpochMilli());
```

*Impact.* Predictable temporary passwords for all imported user accounts.
*Mitigation.* Replace `SplittableRandom` with `SecureRandom` for all password and secret generation.

## A.5 Configuration and Operational Hardening

<!--
**Example 4: H2 database console enabled and publicly reachable (CWE-489, pre-training, Critical)**

The H2 web console was enabled in the application configuration while the security configuration broadly permitted all requests. This exposed a development/debug database interface to any network-reachable caller.

```properties
spring.h2.console.enabled=true
```

*Impact.* Any caller can browse and modify the application database through the H2 web console.
*Mitigation.* Disable the H2 console outside local development; if retained, isolate it behind a development-only profile and restrict access to localhost.
-->

**Example 1: CSRF protection disabled without stateless compensation (CWE-352, pre-training, High)**

CSRF protection was explicitly disabled for all endpoints without configuring a stateless session policy to compensate. This leaves state-changing endpoints vulnerable to cross-site request forgery attacks when session cookies are used.

```java
.csrf(csrf -> csrf.disable())
```

*Impact.* Authenticated users can be tricked into performing unintended state-changing actions via malicious cross-site requests.
*Mitigation.* Enable CSRF protection for state-changing endpoints, or enforce a stateless session policy with SameSite-Strict cookies.

**Example 2: No brute-force protection on login endpoint (CWE-307, pre-training, High)**

The login endpoint performed credential verification with no rate limiting, account lockout, or delay mechanism. An attacker can submit unlimited authentication attempts to brute-force user passwords.

```java
if (!passwordEncoder.matches(password,
        user.getPasswordHash())) {
    throw new BadCredentialsException("Invalid");
}
```

*Impact.* Unlimited login attempts allow offline or online password brute-forcing without detection or restriction.
*Mitigation.* Implement per-IP or per-username rate limiting and temporary account lockout after a configurable number of consecutive failures.
