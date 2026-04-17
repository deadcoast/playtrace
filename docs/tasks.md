# Implementation Plan: Incomplete Modules Implementation

## Overview

This plan implements nine incomplete modules across four packages (utils, normalize, config, store) following the dependency order: utils → normalize → config → store. Each module includes implementation tasks with property-based tests for universal correctness properties and unit tests for specific examples. The implementation follows Python 3.12 conventions with typed interfaces, dataclasses with slots, and comprehensive error handling.

Status: Verified complete against the recovery branch source on 2026-04-17.
Validation: `uv run pytest` (`92 passed`) and the documented-scope targeted suite (`47 passed`).

## Tasks

- [x] 1. Implement Clock utilities (utils/clock.py)
  - [x] 1.1 Create Clock class with timezone-aware datetime operations
    - Implement `utc_now()` returning current UTC time with timezone info
    - Implement `to_utc()` converting naive/aware datetimes to UTC
    - Implement `parse_iso8601()` parsing ISO 8601 strings to timezone-aware datetime
    - Implement `format_iso8601()` formatting datetime as ISO 8601 with UTC offset
    - Handle None inputs gracefully (return None for null-safe operations)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  
  - [x] 1.2 Write property test for naive datetime to UTC conversion
    - **Property 25: Clock Naive DateTime to UTC**
    - **Validates: Requirements 7.2**
    - Generate arbitrary naive datetimes, verify conversion adds UTC timezone
  
  - [x] 1.3 Write property test for aware datetime to UTC conversion
    - **Property 26: Clock Aware DateTime to UTC**
    - **Validates: Requirements 7.3**
    - Generate arbitrary timezone-aware datetimes, verify UTC conversion preserves instant
  
  - [x] 1.4 Write property test for ISO 8601 parsing
    - **Property 27: Clock ISO 8601 Parsing**
    - **Validates: Requirements 7.4**
    - Generate valid ISO 8601 strings, verify parsing produces timezone-aware datetime
  
  - [x] 1.5 Write property test for ISO 8601 formatting
    - **Property 28: Clock ISO 8601 Formatting**
    - **Validates: Requirements 7.5**
    - Generate arbitrary datetimes, verify formatting produces valid ISO 8601 with UTC offset
  
  - [x] 1.6 Write property test for datetime round-trip preservation
    - **Property 29: Clock Round-Trip Preservation**
    - **Validates: Requirements 7.7**
    - Generate timezone-aware datetimes, verify to_utc → format → parse produces equivalent datetime

- [x] 2. Implement Hasher utilities (utils/hashing.py)
  - [x] 2.1 Create Hasher class with SHA-1 hash computation
    - Implement `hash_file()` computing SHA-1 of file contents with 64KB streaming chunks
    - Implement `hash_string()` computing SHA-1 of UTF-8 encoded string
    - Return lowercase hexadecimal strings for all hashes
    - Return None for missing/unreadable files without raising exceptions
    - Handle IOError and PermissionError gracefully
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  
  - [x] 2.2 Write property test for file hash computation
    - **Property 30: Hasher File Hash Computation**
    - **Validates: Requirements 8.1, 8.5**
    - Generate temporary files with random content, verify SHA-1 hash is lowercase hex
  
  - [x] 2.3 Write property test for string hash computation
    - **Property 31: Hasher String Hash Computation**
    - **Validates: Requirements 8.2, 8.5**
    - Generate arbitrary strings, verify SHA-1 hash is lowercase hex
  
  - [x] 2.4 Write property test for hash idempotence
    - **Property 32: Hasher Idempotence**
    - **Validates: Requirements 8.7**
    - Generate files, verify computing hash twice produces identical results

- [x] 3. Implement Platform Detector utilities (utils/platform.py)
  - [x] 3.1 Create PlatformInfo dataclass and PlatformDetector class
    - Define PlatformInfo with windows_version, system_directory, program_files, user_profile fields
    - Implement `detect()` class method with caching in class variable
    - Implement `_detect_windows_version()` using platform.win32_ver()
    - Implement `_get_system_directory()` using %SystemRoot% environment variable
    - Implement `_get_program_files()` using %ProgramFiles% environment variable
    - Implement `_get_user_profile()` using %USERPROFILE% environment variable
    - Return None for all paths on non-Windows platforms
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_
  
  - [x] 3.2 Write property test for platform detection caching
    - **Property 33: Platform Detector Caching**
    - **Validates: Requirements 9.6**
    - Call detect() multiple times, verify same cached instance is returned
  
  - [x] 3.3 Write property test for platform detection idempotence
    - **Property 34: Platform Detector Idempotence**
    - **Validates: Requirements 9.7**
    - Call detect() twice, verify identical PlatformInfo values

- [x] 4. Checkpoint - Ensure all utils tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Path Normalizer (normalize/pathing.py)
  - [x] 5.1 Create PathNormalizer class with Windows path normalization
    - Implement `normalize()` converting Windows paths to canonical lowercase form
    - Implement `_strip_quotes()` removing surrounding quotes
    - Implement `_expand_variables()` expanding environment variables with os.path.expandvars
    - Implement `_to_absolute()` converting relative to absolute paths
    - Implement `_to_backslashes()` converting forward slashes to backslashes
    - Return None for None or empty input
    - Use PureWindowsPath for consistent Windows path handling
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
  
  - [x] 5.2 Write property test for path case normalization
    - **Property 4: Path Case Normalization**
    - **Validates: Requirements 2.1**
    - Generate Windows paths with mixed case, verify conversion to lowercase
  
  - [x] 5.3 Write property test for path slash conversion
    - **Property 5: Path Slash Conversion**
    - **Validates: Requirements 2.2**
    - Generate paths with forward slashes, verify conversion to backslashes
  
  - [x] 5.4 Write property test for environment variable expansion
    - **Property 6: Path Environment Variable Expansion**
    - **Validates: Requirements 2.3**
    - Generate paths with environment variables, verify expansion to absolute paths
  
  - [x] 5.5 Write property test for relative to absolute conversion
    - **Property 7: Path Relative to Absolute Conversion**
    - **Validates: Requirements 2.4**
    - Generate relative paths, verify resolution to absolute paths
  
  - [x] 5.6 Write property test for quote stripping
    - **Property 8: Path Quote Stripping**
    - **Validates: Requirements 2.3**
    - Generate quoted paths, verify surrounding quotes are stripped
  
  - [x] 5.7 Write property test for path normalization idempotence
    - **Property 9: Path Normalization Idempotence**
    - **Validates: Requirements 2.7**
    - Generate paths, verify normalizing twice produces same result as once

- [x] 6. Implement Metadata Extractor (normalize/metadata.py)
  - [x] 6.1 Create ExecutableMetadata dataclass and MetadataExtractor class
    - Define ExecutableMetadata with product_name, original_filename, file_description, company_name, signer fields
    - Implement `extract()` extracting metadata from PE files, returning None for invalid files
    - Implement `_extract_version_info()` extracting StringFileInfo from version resources
    - Implement `_extract_signature()` extracting digital signature signer (Windows only)
    - Implement `_normalize_field()` stripping whitespace and returning None for empty strings
    - Use pefile library for PE parsing
    - Use win32security.CryptQueryObject for signature extraction on Windows
    - Catch all exceptions during parsing, return None for all fields on failure
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [x] 6.2 Write property test for metadata extraction error handling
    - **Property 1: Metadata Extraction Error Handling**
    - **Validates: Requirements 1.3**
    - Generate invalid file paths and non-PE files, verify None returned without exceptions
  
  - [x] 6.3 Write property test for metadata string normalization
    - **Property 2: Metadata String Normalization**
    - **Validates: Requirements 1.5**
    - Generate strings with whitespace, verify stripping and None for empty strings
  
  - [x] 6.4 Write property test for metadata extraction idempotence
    - **Property 3: Metadata Extraction Idempotence**
    - **Validates: Requirements 1.6**
    - Use PE file fixtures, verify extracting twice produces identical results
  
  - [x] 6.5 Write unit tests for metadata extraction with real PE files
    - Test extraction from signed PE file fixture
    - Test extraction from unsigned PE file fixture
    - Test extraction from PE file without version info
    - Test handling of missing files
    - _Requirements: 1.1, 1.2, 1.4_

- [x] 7. Checkpoint - Ensure all normalize tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement Config Model (config/models.py)
  - [x] 8.1 Create Config_Model dataclass with validation
    - Define Config_Model with session_merge_dedupe_window_minutes (default 2), default_sources (default []), classification_overrides (default {})
    - Use @dataclass(slots=True) following project conventions
    - Implement `__post_init__()` for field validation
    - Implement `_validate_merge_window()` ensuring positive integer
    - Implement `_validate_sources()` ensuring valid SourceName enum values
    - Raise ValueError with descriptive messages on validation failure
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [x] 8.2 Write property test for positive integer validation
    - **Property 15: Config Positive Integer Validation**
    - **Validates: Requirements 4.5**
    - Generate zero and negative integers, verify ValueError raised for session_merge_dedupe_window_minutes
  
  - [x] 8.3 Write property test for valid source names validation
    - **Property 16: Config Valid Source Names Validation**
    - **Validates: Requirements 4.6**
    - Generate invalid source names, verify ValueError raised for default_sources
  
  - [x] 8.4 Write property test for invalid values raising errors
    - **Property 17: Config Invalid Values Raise Errors**
    - **Validates: Requirements 4.7**
    - Generate invalid field values, verify validation errors during construction

- [x] 9. Implement Config Loader (config/loader.py)
  - [x] 9.1 Create ConfigLoader class with TOML parsing
    - Implement `load()` loading config from TOML file or returning defaults
    - Implement `_parse_toml()` parsing TOML file with tomllib
    - Implement `_apply_defaults()` filling missing fields with default values
    - Return default Config_Model if path is None or doesn't exist
    - Catch tomllib.TOMLDecodeError and raise descriptive error
    - Ignore unknown fields (only extract known config keys)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  
  - [x] 9.2 Write property test for TOML parsing
    - **Property 10: Config TOML Parsing**
    - **Validates: Requirements 3.1**
    - Generate valid TOML config files, verify successful parsing into Config_Model
  
  - [x] 9.3 Write property test for invalid TOML error handling
    - **Property 11: Config Invalid TOML Error Handling**
    - **Validates: Requirements 3.3**
    - Generate invalid TOML syntax, verify TOMLDecodeError raised
  
  - [x] 9.4 Write property test for unknown fields ignored
    - **Property 12: Config Unknown Fields Ignored**
    - **Validates: Requirements 3.4**
    - Generate TOML with unknown fields, verify no errors raised
  
  - [x] 9.5 Write property test for default values applied
    - **Property 13: Config Default Values Applied**
    - **Validates: Requirements 3.5**
    - Generate TOML omitting optional fields, verify defaults populated
  
  - [x] 9.6 Write property test for config round-trip preservation
    - **Property 14: Config Round-Trip Preservation**
    - **Validates: Requirements 3.7**
    - Generate Config_Model instances, verify serialize → load produces equivalent model
  
  - [x] 9.7 Write unit tests for config loading scenarios
    - Test loading valid TOML with all fields
    - Test loading minimal TOML with defaults
    - Test loading from non-existent path returns defaults
    - Test loading invalid TOML raises error
    - _Requirements: 3.1, 3.2, 3.3, 3.5_

- [x] 10. Checkpoint - Ensure all config tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement Migration Engine (store/migrations.py)
  - [x] 11.1 Create Migration dataclass and MigrationEngine class
    - Define Migration with version, description, sql fields
    - Implement `__init__()` accepting Database connection
    - Implement `current_version()` querying schema_version table
    - Implement `apply_migrations()` applying migrations from current to target version
    - Implement `_ensure_version_table()` creating schema_version table if missing
    - Implement `_apply_migration()` applying single migration in transaction
    - Implement `_record_migration()` recording version, timestamp, description
    - Implement `migrations` property returning list of available migrations
    - Create schema_version table with version, applied_at, description columns
    - Raise error if current version exceeds target (database from newer version)
    - Wrap each migration in transaction with rollback on failure
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  
  - [x] 11.2 Write property test for migration application sequence
    - **Property 18: Migration Application Sequence**
    - **Validates: Requirements 5.2**
    - Generate databases with various schema versions, verify intermediate migrations applied in order
  
  - [x] 11.3 Write property test for migration transaction rollback
    - **Property 19: Migration Transaction Rollback**
    - **Validates: Requirements 5.5**
    - Generate failing migrations, verify transaction rollback leaves database unchanged
  
  - [x] 11.4 Write property test for migration recording
    - **Property 20: Migration Recording**
    - **Validates: Requirements 5.6**
    - Apply migrations, verify version, timestamp, description recorded in schema_version table
  
  - [x] 11.5 Write property test for migration version invariant
    - **Property 21: Migration Version Invariant**
    - **Validates: Requirements 5.7**
    - Apply migration sequences, verify checking version shows target version
  
  - [x] 11.6 Write unit tests for migration engine scenarios
    - Test creating schema_version table when missing
    - Test no-op when current version equals target
    - Test error when current version exceeds target
    - Test applying single migration
    - Test applying multiple migrations in sequence
    - _Requirements: 5.1, 5.3, 5.4_

- [x] 12. Implement Repository Pattern (store/repositories.py)
  - [x] 12.1 Create base Repository class with generic CRUD operations
    - Define Repository[T] generic class with type parameter
    - Implement `__init__()` accepting Database and table_name
    - Implement `find_by_id()` finding entity by primary key, returning None if not found
    - Implement `find_all()` finding all entities
    - Implement `save()` inserting or updating entity, returning saved entity
    - Implement `delete()` deleting entity by primary key
    - Define abstract `_row_to_entity()` converting sqlite3.Row to typed entity
    - Use Database.connect() for connection management
    - Use parameterized queries to prevent SQL injection
    - _Requirements: 6.1, 6.2, 6.4_
  
  - [x] 12.2 Create specialized repository classes
    - Implement ExecutableRepository with `find_by_normalized_key()`
    - Implement SessionRepository with `find_by_exe_id()`
    - Implement TitleRepository with `find_by_classification()`
    - Implement MappingRepository with `find_by_target()`
    - Override `_row_to_entity()` in each specialized repository
    - Handle JSON serialization for complex fields (lists, dicts)
    - _Requirements: 6.5_
  
  - [x] 12.3 Write property test for repository save returns entity
    - **Property 22: Repository Save Returns Entity**
    - **Validates: Requirements 6.3**
    - Generate arbitrary entities, verify save returns entity with generated fields
  
  - [x] 12.4 Write property test for repository row conversion
    - **Property 23: Repository Row Conversion**
    - **Validates: Requirements 6.6**
    - Generate database rows, verify automatic conversion to typed dataclass instances
  
  - [x] 12.5 Write property test for repository round-trip preservation
    - **Property 24: Repository Round-Trip Preservation**
    - **Validates: Requirements 6.7**
    - Generate entities, verify save → find_by_id returns equivalent entity
  
  - [x] 12.6 Write unit tests for repository operations
    - Test find_by_id with existing and non-existent IDs
    - Test find_all with empty and populated tables
    - Test save for insert and update operations
    - Test delete with existing and non-existent IDs
    - Test specialized repository query methods
    - _Requirements: 6.1, 6.2, 6.4, 6.5_

- [x] 13. Checkpoint - Ensure all store tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Integration and refactoring
  - [x] 14.1 Refactor normalize/identity.py to use PathNormalizer
    - Update IdentityNormalizer._normalize_path() to use PathNormalizer.normalize()
    - Keep existing logic as fallback for compatibility
    - Add deprecation notice if needed
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [x] 14.2 Refactor store/db.py to use Clock utilities
    - Update Database._utc_now() to use Clock.utc_now()
    - Update datetime parsing/formatting to use Clock methods
    - Ensure backward compatibility with existing database timestamps
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [x] 14.3 Write integration tests for refactored components
    - Test IdentityNormalizer with PathNormalizer integration
    - Test Database with Clock integration
    - Verify backward compatibility with existing data

- [x] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at package boundaries
- Property tests validate universal correctness properties using Hypothesis (100+ iterations)
- Unit tests validate specific examples and edge cases
- Implementation follows dependency order: utils → normalize → config → store
- All modules follow Python 3.12 conventions: `from __future__ import annotations`, `@dataclass(slots=True)`, typed interfaces
- Test files should be organized in `tests/` mirroring the package structure
- Use `pytest.tmp_path` for temporary files and in-memory SQLite (`:memory:`) for fast tests
- PE file fixtures should be placed in `tests/fixtures/` directory
