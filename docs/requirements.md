# Requirements Document

## Introduction

This document specifies requirements for implementing nine incomplete modules in the playtrace project. These modules provide essential functionality for metadata extraction, path normalization, configuration management, database migrations, repository pattern implementation, and utility functions for time, hashing, and platform detection. The implementation follows the evidence-first architecture where artifacts are collected, parsed into evidence, normalized, and rebuilt into executables, sessions, and titles.

## Glossary

- **Normalizer**: Component that transforms raw evidence into canonical forms
- **Metadata_Extractor**: Component that extracts version info and file properties from Windows executables
- **Path_Normalizer**: Component that converts Windows paths to canonical lowercase forms
- **Config_Loader**: Component that loads and validates configuration from TOML files
- **Config_Model**: Dataclass representing validated configuration structure
- **Migration_Engine**: Component that applies schema version upgrades to SQLite databases
- **Repository**: Component that encapsulates database queries for a specific entity type
- **Clock**: Component that provides timezone-aware datetime operations
- **Hasher**: Component that computes cryptographic hashes for files and strings
- **Platform_Detector**: Component that identifies Windows version and system paths
- **Evidence_Record**: Typed record containing parsed artifact data with source and timestamp
- **Executable_Identity**: Normalized representation of a Windows executable with metadata
- **Database**: SQLite connection manager with schema bootstrap and CRUD operations

## Requirements

### Requirement 1: Extract Metadata from Windows Executables

**User Story:** As a developer, I want to extract version information and file properties from Windows executables, so that I can populate ExecutableIdentity fields with product_name, original_filename, file_description, company_name, and signer.

#### Acceptance Criteria

1. WHEN a valid Windows PE file path is provided, THE Metadata_Extractor SHALL extract version info fields (ProductName, OriginalFilename, FileDescription, CompanyName)
2. WHEN a valid Windows PE file path is provided, THE Metadata_Extractor SHALL extract digital signature information (signer name)
3. WHEN an invalid or non-PE file path is provided, THE Metadata_Extractor SHALL return None for all metadata fields without raising exceptions
4. WHEN a PE file lacks version info resources, THE Metadata_Extractor SHALL return None for missing fields
5. THE Metadata_Extractor SHALL normalize extracted strings by stripping whitespace and returning None for empty values
6. FOR ALL valid PE files, extracting metadata twice SHALL produce identical results (idempotence)

### Requirement 2: Normalize Windows Paths to Canonical Form

**User Story:** As a developer, I want to normalize Windows paths to a canonical lowercase form, so that path-based executable identity keys remain consistent across different evidence sources.

#### Acceptance Criteria

1. WHEN a Windows path with mixed case is provided, THE Path_Normalizer SHALL convert it to lowercase
2. WHEN a Windows path contains forward slashes, THE Path_Normalizer SHALL convert them to backslashes
3. WHEN a Windows path is wrapped in quotes, THE Path_Normalizer SHALL strip the quotes
4. WHEN a Windows path contains environment variables like %ProgramFiles%, THE Path_Normalizer SHALL expand them to absolute paths
5. WHEN a relative Windows path is provided, THE Path_Normalizer SHALL resolve it to an absolute path
6. WHEN None or empty string is provided, THE Path_Normalizer SHALL return None
7. FOR ALL valid Windows paths, normalizing then normalizing again SHALL produce the same result (idempotence)

### Requirement 3: Load Configuration from TOML Files

**User Story:** As a developer, I want to load configuration from TOML files, so that users can customize scan behavior, session merge windows, and classification rules without modifying code.

#### Acceptance Criteria

1. WHEN a valid TOML config file path is provided, THE Config_Loader SHALL parse it into a Config_Model instance
2. WHEN a config file path does not exist, THE Config_Loader SHALL return a default Config_Model with sensible defaults
3. WHEN a config file contains invalid TOML syntax, THE Config_Loader SHALL raise a descriptive error
4. WHEN a config file contains unknown fields, THE Config_Loader SHALL ignore them without raising errors
5. WHEN a config file omits optional fields, THE Config_Loader SHALL populate them with default values
6. THE Config_Model SHALL include fields for session_merge_dedupe_window_minutes, default_sources, and classification_overrides
7. FOR ALL valid config files, loading then serializing then loading SHALL produce an equivalent Config_Model (round-trip property)

### Requirement 4: Define Configuration Data Model

**User Story:** As a developer, I want a typed configuration data model, so that configuration values are validated and accessible with type safety throughout the application.

#### Acceptance Criteria

1. THE Config_Model SHALL be a dataclass with slots=True following project conventions
2. THE Config_Model SHALL include a session_merge_dedupe_window_minutes field with default value 2
3. THE Config_Model SHALL include a default_sources field as a list of strings with default empty list
4. THE Config_Model SHALL include a classification_overrides field as a dict mapping paths to classifications
5. THE Config_Model SHALL validate that session_merge_dedupe_window_minutes is a positive integer
6. THE Config_Model SHALL validate that default_sources contains only valid SourceName enum values
7. WHEN invalid field values are provided, THE Config_Model SHALL raise a validation error during construction

### Requirement 5: Apply Database Schema Migrations

**User Story:** As a developer, I want to apply schema migrations to existing databases, so that users can upgrade from older playtrace versions without losing data.

#### Acceptance Criteria

1. WHEN a database lacks a schema_version table, THE Migration_Engine SHALL create it and set version to 1
2. WHEN a database schema_version is less than the current version, THE Migration_Engine SHALL apply all intermediate migrations in order
3. WHEN a database schema_version equals the current version, THE Migration_Engine SHALL perform no operations
4. WHEN a database schema_version exceeds the current version, THE Migration_Engine SHALL raise an error indicating the database is from a newer version
5. THE Migration_Engine SHALL execute each migration in a transaction and rollback on failure
6. THE Migration_Engine SHALL record the applied migration version and timestamp in the schema_version table
7. FOR ALL migration sequences, applying migrations then checking version SHALL show the current version (invariant)

### Requirement 6: Implement Repository Pattern for Database Access

**User Story:** As a developer, I want repository classes that encapsulate database queries, so that database access logic is separated from business logic and easier to test.

#### Acceptance Criteria

1. THE Repository SHALL provide a base class with common query methods (find_by_id, find_all, save, delete)
2. WHEN a repository method is called, THE Repository SHALL use the Database connection manager
3. WHEN a repository save operation succeeds, THE Repository SHALL return the saved entity with any generated fields populated
4. WHEN a repository find_by_id receives a non-existent id, THE Repository SHALL return None
5. THE Repository SHALL support specialized repositories for Executables, Sessions, Titles, and Mappings
6. THE Repository SHALL convert database rows to typed dataclass instances automatically
7. FOR ALL entities, saving then finding by id SHALL return an equivalent entity (round-trip property)

### Requirement 7: Provide Timezone-Aware Clock Operations

**User Story:** As a developer, I want timezone-aware datetime utilities, so that all timestamps are stored in UTC and timezone conversions are handled consistently.

#### Acceptance Criteria

1. THE Clock SHALL provide a utc_now method that returns the current time in UTC with timezone info
2. WHEN a naive datetime is provided, THE Clock SHALL convert it to UTC by assuming it is already UTC
3. WHEN a timezone-aware datetime is provided, THE Clock SHALL convert it to UTC preserving the instant
4. THE Clock SHALL provide a method to parse ISO 8601 strings into timezone-aware datetimes
5. THE Clock SHALL provide a method to format datetimes as ISO 8601 strings with UTC offset
6. WHEN None is provided to conversion methods, THE Clock SHALL return None
7. FOR ALL timezone-aware datetimes, converting to UTC then formatting then parsing SHALL produce an equivalent datetime (round-trip property)

### Requirement 8: Compute Cryptographic Hashes

**User Story:** As a developer, I want to compute SHA-1 hashes for files and strings, so that executable identity can be based on content hashes when available.

#### Acceptance Criteria

1. WHEN a valid file path is provided, THE Hasher SHALL compute the SHA-1 hash of the file contents
2. WHEN a string is provided, THE Hasher SHALL compute the SHA-1 hash of the UTF-8 encoded bytes
3. WHEN a file path does not exist, THE Hasher SHALL return None without raising exceptions
4. WHEN a file cannot be read due to permissions, THE Hasher SHALL return None without raising exceptions
5. THE Hasher SHALL return hash values as lowercase hexadecimal strings
6. THE Hasher SHALL handle large files efficiently using streaming reads
7. FOR ALL files, computing the hash twice SHALL produce identical results (idempotence)

### Requirement 9: Detect Windows Platform Information

**User Story:** As a developer, I want to detect Windows version and system paths, so that collectors can locate artifact files in the correct system directories.

#### Acceptance Criteria

1. THE Platform_Detector SHALL detect the Windows version (10, 11, Server 2019, etc.)
2. THE Platform_Detector SHALL return the Windows system directory path (typically C:\Windows\System32)
3. THE Platform_Detector SHALL return the Program Files directory path
4. THE Platform_Detector SHALL return the user profile directory path for the current user
5. WHEN running on a non-Windows platform, THE Platform_Detector SHALL return None for all Windows-specific paths
6. THE Platform_Detector SHALL cache detected values to avoid repeated system calls
7. FOR ALL Windows systems, detecting platform info twice SHALL produce identical results (idempotence)
