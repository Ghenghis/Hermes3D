# Blender MCP Provider Manager

## Providers
1. ahujasid/blender-mcp — default practical provider.
2. VxASI/blender-mcp-vxai — experimental provider.
3. llm-use/Blender-MCP-Server — experimental larger surface.
4. official/custom provider slot.

## Required capabilities
- scene info
- object info or equivalent
- viewport screenshot
- safe Python execution
- 3MF export path validation

## Validation sequence
1. Detect Blender binary.
2. Detect MCP registration.
3. Launch/connect Blender.
4. Query scene info.
5. Capture viewport screenshot.
6. Execute harmless Python snippet.
7. Validate 3MF add-on/operator availability.
8. Export test 3MF to allowed temp directory.
9. Verify file exists and opens as zip/XML.

## Update flow
```text
check provider updates -> install to staging -> validate -> compare capabilities -> promote -> keep rollback
```

## Safety rules
- Block `os.system`, `subprocess`, network imports, arbitrary file writes outside allowed dirs.
- Enforce execution timeout.
- Log every code string hash.
- Store screenshots in proof bundle.
