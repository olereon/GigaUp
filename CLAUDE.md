# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Guidelines

### Python Guidelines
- USE python3.11 not python or python3 when working with Python based project or files.

### Git Commit Guidelines
- Make new git commits only when prompted by the user or after major code changes, such as, added new feature or verified fix of a serious bug.

### UI Automation Guidelines
- Always consider types of the controls and their relative position against other UI controls
- Many interactive controls do not have a TITLE or their TITLE is matching their current value
- When designing search methods for controls, use position-based detection when titles are unreliable
- Verify current values before setting new ones to avoid unnecessary operations

[... rest of the existing content remains unchanged ...]