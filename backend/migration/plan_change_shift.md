# Plan Change: Package Structure Shift

## Context

During Phase 2 implementation, we identified that `polyplexity_agent` should be treated as a proper installable Python package rather than just a module directory. This change aligns with Python packaging best practices and provides better separation between the agent library and the FastAPI application.

## What Changed

### Original Approach
- `polyplexity_agent` was treated as a regular module directory
- `main.py` imported directly from the local source: `from polyplexity_agent import ...`
- No package installation required
- File paths referenced full backend path: `polyplexity/backend/polyplexity_agent/`

### New Approach
- `polyplexity_agent` is now an installable Python package
- Package configuration: `polyplexity_agent/pyproject.toml` (at package root)
- Package must be installed in editable mode: `cd polyplexity_agent && pip install -e .`
- `main.py` imports from installed package: `from polyplexity_agent import ...`
- File paths are relative to package root: `polyplexity_agent/` (not full backend path)
- Tests can import from installed package or local source (fallback pattern)

## Key Changes Made

### 1. Package Configuration
- **File**: `polyplexity_agent/pyproject.toml`
- **Change**: Fixed `where = [".."]` to `where = ["."]` (package root)
- **Impact**: Package now correctly identifies itself as `polyplexity-agent`

### 2. Installation Requirement
- **New Step**: Package must be installed before running `main.py` or tests
- **Command**: `cd polyplexity_agent && pip install -e .`
- **Benefit**: Editable install allows code changes without reinstalling

### 3. Import Patterns
- **Before**: Direct imports from local source
- **After**: Imports from installed package
- **Example**: `from polyplexity_agent.config import Settings`

### 4. Documentation Updates
- **MIGRATION_PLAN.md**: Added "Package Structure" and "Prerequisites" sections
- **phase_1.md**: Added package context and installation requirements
- **phase_2.md**: Added package context and updated import examples
- **main.py**: Added installation documentation in docstring

### 5. File Path References
- **Before**: `polyplexity/backend/polyplexity_agent/config/settings.py`
- **After**: `config/settings.py` (relative to package root)
- **Clarification**: All paths in migration docs are now relative to `polyplexity_agent/` unless specified as backend root

## Why This Change Was Made

1. **Better Separation**: Clear distinction between library (`polyplexity_agent`) and application (`main.py`)
2. **Standard Practice**: Follows Python packaging conventions
3. **Versioning**: Enables independent versioning of the agent package
4. **Distribution**: Makes it easier to distribute the agent as a separate package
5. **Development**: Editable install allows development without reinstalling
6. **Testing**: Tests can import from installed package, matching production behavior

## Impact on Migration Plan

### Phases Already Completed
- **Phase 1**: No code changes needed - structure already correct
- **Phase 2**: All imports already use package imports - no changes needed

### Future Phases
- All future phases will use package imports: `from polyplexity_agent.module import ...`
- File paths in documentation are relative to `polyplexity_agent/` package root
- Installation step added to prerequisites for all phases

### Testing Impact
- Tests can import from installed package (preferred)
- Fallback pattern allows tests to work with local source if package not installed
- Test patterns updated to show both approaches

## Migration Steps for Existing Setup

If you have an existing setup and need to adopt this change:

1. **Install the package**:
   ```bash
   cd polyplexity/backend/polyplexity_agent
   pip install -e .
   ```

2. **Verify installation**:
   ```bash
   python -c "from polyplexity_agent.config import Settings; print('Package installed correctly')"
   ```

3. **Update any scripts** that reference full paths to use package imports instead

4. **Run tests** to verify everything still works:
   ```bash
   cd polyplexity/backend
   pytest tests/ -vv
   ```

## Benefits

1. **Cleaner Architecture**: Clear separation between library and application
2. **Better Imports**: Standard Python package imports throughout
3. **Easier Development**: Editable install means changes are immediately available
4. **Production Ready**: Package can be built and distributed independently
5. **Standard Practice**: Follows Python packaging best practices

## Notes

- This change is **non-breaking** for existing code - all imports already use package-style imports
- The `pyproject.toml` fix ensures the package is correctly identified
- Editable install (`-e`) is essential for development workflow
- Tests support both installed and local imports for flexibility

## Date of Change

This change was implemented after Phase 2 completion, updating the migration plan and Phase 1/2 documentation to reflect the package structure approach.
