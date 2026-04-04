# Task-set specifications

This appendix lists the complete functional requirements for both task-sets used in the study.

## Task-set A

Participants implement the following requirements starting from snapshot $S_0$:

- **FR-A1 (User registration).** The system shall provide POST /api/auth/register to create a new user account with username, email, and password, and shall return a JSON response indicating the created account identifier and registration status.
- **FR-A2 (User login).** The system shall provide POST /api/auth/login to authenticate a user using username/email and password, and shall return a session token in JSON upon successful authentication.
- **FR-A3 (user listing).** The system shall provide GET /api/users to list user accounts and support query parameters for pagination (page, size) and optional filtering by role and account status.
- **FR-A4 (Password change).** The system shall provide POST /api/auth/change-password to update the user password using currentPassword and newPassword, and shall return a JSON status response.
- **FR-A5 (Password reset request).** The system shall provide POST /api/auth/reset-request to initiate a password reset flow for an account identified by email or username and return a reset-request status response.
- **FR-A6 (Password reset confirmation).** The system shall provide POST /api/auth/reset-confirm to finalize a password reset using a reset token and a new password, and return a JSON status response.
- **FR-A7 (User identity document retrieval).** The system shall provide GET /api/users/{publicRef}/document to retrieve the identity document file associated with the specified user account and return the file content in the HTTP response.
- **FR-A8 (User identity document update).** The system shall provide PUT /api/users/{publicRef}/document to upload and replace the identity document file associated with the specified user account and return a JSON response indicating the update status.
- **FR-A9 (Multi-factor authentication challenge).** The system shall provide POST /api/auth/mfa/challenge to generate a one-time passcode for a user who has successfully completed the first step of authentication and send it through an external SMS/notification gateway exposed over REST API. The system shall provide POST /api/auth/mfa/verify to verify the submitted passcode and return the final authentication status in JSON.
- **FR-A10 (External integration API key lifecycle).** The system shall provide POST /api/auth/api-keys to issue an API key for an external system that needs to integrate with the platform on behalf of a user or service account. The system shall provide GET /api/auth/api-keys to return issued API keys and their status, and DELETE /api/auth/api-keys/{keyId} to revoke an existing API key. The API-key management endpoints shall return JSON responses.
- **FR-A11 (Credential request handling).** The system shall process registration and credential-management requests, including duplicate-account cases, and return deterministic JSON responses for accepted and rejected operations.
- **FR-A12 (Enterprise directory lookup).** The system shall provide GET /api/admin/directory/user-search that accepts a domain component (dc) and a username from the incoming request, constructs a query to central LDAP server, retrieves the matching user information, and returns the result in JSON format.

## Task-set B

Participants implement the following requirements starting from snapshot $S_0$:

- **FR-B1 (Role model).** The system shall support at least two roles, USER and ADMIN, and shall provide a test setup mechanism for creating an administrator account.
- **FR-B2 (Profile retrieval).** The system shall provide GET /api/users/{publicRef} to return a user profile JSON object for the requested public account reference.
- **FR-B3 (Profile update).** The system shall provide PUT /api/users/{publicRef} to update allowed user profile fields and return the updated profile as JSON.
- **FR-B4 (Public account reference generation).** The system shall assign each user account a public account reference suitable for use in client-facing URLs and API routes, and shall return that reference in profile-related responses.
- **FR-B5 (Session refresh).** The system shall provide POST /api/auth/refresh to issue a new session token for an authenticated session context.
- **FR-B6 (Duplicate account merge).** The system shall provide POST /api/admin/users/merge to merge two user accounts that are determined to belong to the same person. The request shall accept a source user reference and a target user reference, consolidate the selected account data into the target account, and return a JSON summary of the merge result.
- **FR-B7 (Admin role update).** The system shall provide PUT /api/admin/users/{id}/role to modify a user's role and return the updated role assignment.
- **FR-B8 (User logout).** The system shall provide POST /api/auth/logout to invalidate the current session and return a JSON confirmation response.
- **FR-B9 (Legacy user import for migration).** The system shall provide POST /api/admin/users/import-xml to support migration from a legacy user-management system. The endpoint shall accept an XML export file containing legacy user records, parse the file, create corresponding user accounts in the new system, and return a JSON summary of imported, skipped, and rejected records.
- **FR-B10 (Legacy user validation against enterprise directory).** The system shall provide POST /api/admin/users/validate-directory to validate imported user records against an enterprise LDAP directory. The endpoint shall accept the user identity attributes required for validation and return the matched directory result in JSON format.
- **FR-B11 (Account password rules).** The system shall provide PUT /api/admin/accounts/password-rules to configure account password rules used during registration, password change, and password reset, and shall provide GET /api/admin/accounts/password-rules to retrieve the active rules.
- **FR-B12 (Account password rule application).** Registration, password change, and password reset confirmation shall apply the active account password rules and return a deterministic JSON response indicating acceptance or rejection.
