# AI Agent Setup Instructions for Graphiti

> **For AI Agents**: These are step-by-step instructions to configure Graphiti environment variables interactively with the user.
>
> **⚠️ SECURITY WARNING**: When updating this document or creating examples, NEVER include real credentials (passwords, API keys, instance IDs, URIs with actual instance IDs). Always use placeholders like `YOUR_PASSWORD_HERE`, `YOUR_INSTANCE_ID`, `neo4j+s://YOUR_INSTANCE_ID.databases.neo4j.io`.

## Overview

You are helping the user set up environment variables for the Graphiti MCP server to connect to Neo4j Aura. This process involves:

1. Obtaining Neo4j Aura credentials (from file or user)
2. Detecting if running in a VM (fix URI scheme if needed)
3. Setting system-level environment variables
4. Validating the configuration

## Prerequisites Check

Before starting, verify platform-specific requirements:

### Step 0.1: Check PowerShell Script Execution Policy (Windows Only)

**Action**: Check if PowerShell scripts can be executed.

```powershell
Get-ExecutionPolicy
```

**Expected values**:
- `RemoteSigned` - ✅ OK (allows local scripts)
- `Unrestricted` - ✅ OK (allows all scripts)
- `Bypass` - ✅ OK (allows all scripts without prompts)
- `Restricted` - ❌ BLOCKED (default Windows setting - blocks all scripts)
- `AllSigned` - ⚠️ May work (only signed scripts)

**If policy is `Restricted`**:

**Inform user**:
```
Your PowerShell execution policy is set to 'Restricted', which prevents running
the automated setup script. I need to enable script execution.

I'll need to run a command as Administrator to change this policy.
```

**Set execution policy** (requires admin):
```powershell
# Run this in an Administrator PowerShell window
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

**If unable to set policy**:
```
Unable to change PowerShell execution policy. This might be due to:
1. Group Policy restrictions (corporate/enterprise environment)
2. Insufficient permissions
3. System security settings

FALLBACK: I'll collect your credentials and create a credentials.txt file,
then guide you to run the setup manually with admin privileges.
```

→ **Proceed to Step 1B** (credential elicitation) and skip Step 5 automation

### Step 0.2: Check Administrator Privilege Capability (Windows Only)

**Action**: Verify we can elevate to Administrator privileges.

**Test 1 - Check current privileges**:
```powershell
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
```

**Result**:
- `True` - ✅ Already running as Administrator
- `False` - Need to test elevation capability

**Test 2 - Test elevation (if not already admin)**:

**Inform user**:
```
I need to verify I can elevate to Administrator privileges for setting
system environment variables. This will create a temporary test file.
```

**Test elevation**:
```powershell
# Create a temporary test script
$testScript = "$env:TEMP\graphiti-admin-test.ps1"
Set-Content -Path $testScript -Value @"
Write-Host 'Admin test successful'
New-Item -Path `"`$env:TEMP\graphiti-admin-check.tmp`" -ItemType File -Force
"@

# Try to run it elevated
Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$testScript`"" -Verb RunAs -Wait

# Check if test file was created
Test-Path "$env:TEMP\graphiti-admin-check.tmp"
```

**If test succeeds** (file exists):
```powershell
# Clean up test files
Remove-Item "$env:TEMP\graphiti-admin-check.tmp" -Force -ErrorAction SilentlyContinue
Remove-Item "$env:TEMP\graphiti-admin-test.ps1" -Force -ErrorAction SilentlyContinue
```
✅ **Elevation works** - Proceed with automated setup

**If test fails** (file doesn't exist or error occurs):
```
Unable to verify Administrator privilege elevation. This might be due to:
1. UAC (User Account Control) is disabled
2. Running in a restricted environment
3. User cancelled the elevation prompt
4. System policy prevents elevation

FALLBACK: I'll collect your credentials and create a credentials.txt file.
You'll need to manually run the setup script with admin privileges.
```

**Tell user**:
```
I've created credentials.txt with your Neo4j Aura credentials.

To complete setup:
1. Right-click PowerShell and select "Run as Administrator"
2. Navigate to: [repository root path]
3. Run: .\setup-graphiti-env.ps1
4. Restart Claude Code after setup completes

This will set the system environment variables with admin privileges.
```

→ **Skip Step 5** (automated environment variable setting)
→ **Create credentials.txt instead** for manual script execution

### Step 0.3: Verify User Requirements

After platform checks, confirm:
- [ ] User has created a Neo4j Aura instance (or is willing to create one)
- [ ] User has OpenAI API key (or knows they need to get one)
- [ ] **Windows**: PowerShell execution policy allows scripts
- [ ] **Windows**: Administrator elevation capability verified OR user understands manual process
- [ ] **macOS/Linux**: User has sudo access

## Step 1: Check for Credentials File

**Action**: Check if `credentials.txt` exists in the repository root.

```bash
# Check for credentials file
ls credentials.txt
```

**If file exists**: Proceed to Step 2 (Parse Credentials from File)

**If file NOT found**: Ask user how to proceed

### Step 1A: Ask User for Credential Source (If No File Found)

**Say to user**:
```
I couldn't find a credentials.txt file in the repository.

I can obtain your Neo4j Aura credentials in two ways:

1. I can ask you for your credentials interactively, or
2. I can check if you already have Neo4j credentials set in your system environment variables

Which would you prefer?
```

**Present options**:
- **Option 1**: "Elicit credentials from me interactively"
- **Option 2**: "Check for existing environment variables"

**If user chooses Option 1**: Proceed to Step 1B (Elicit Credentials)
**If user chooses Option 2**: Proceed to Step 1C (Check Existing Environment Variables)

### Step 1B: Elicit Credentials from User

**Say to user**:
```
I couldn't find a credentials.txt file in the repository. I'll need your Neo4j Aura
credentials to set up the environment variables.

Do you have Neo4j Aura credentials available? If not, you can create a free instance at:
https://console.neo4j.io

Please provide the following information:
```

**Prompt user for**:
1. **Neo4j URI** (e.g., `neo4j+s://xxxxx.databases.neo4j.io`)
   - Ask: "What is your Neo4j Aura connection URI?"
   - Validate: Should start with `neo4j+s://` or `neo4j+ssc://`

2. **Neo4j Username** (usually `neo4j`)
   - Ask: "What is your Neo4j username? (typically 'neo4j')"

3. **Neo4j Password**
   - Ask: "What is your Neo4j password? (the one generated when you created the Aura instance)"
   - Note: This will be stored as a system environment variable

4. **Neo4j Database** (usually `neo4j`)
   - Ask: "What is your Neo4j database name? (typically 'neo4j', press Enter for default)"
   - Default to `neo4j` if user presses Enter

**Store credentials** in variables for later use:
```python
credentials = {
    'NEO4J_URI': user_provided_uri,
    'NEO4J_USERNAME': user_provided_username,
    'NEO4J_PASSWORD': user_provided_password,
    'NEO4J_DATABASE': user_provided_database or 'neo4j'
}
```

**If using fallback mode** (from Step 0 failures):

**Create credentials.txt file**:
```bash
# Write credentials to file for manual script execution
cat > credentials.txt << EOF
# Neo4j Aura Credentials
NEO4J_URI=${credentials['NEO4J_URI']}
NEO4J_USERNAME=${credentials['NEO4J_USERNAME']}
NEO4J_PASSWORD=${credentials['NEO4J_PASSWORD']}
NEO4J_DATABASE=${credentials['NEO4J_DATABASE']}
EOF
```

**Inform user**:
```
I've created credentials.txt with your Neo4j Aura credentials.

Since automated setup cannot proceed (due to privilege or policy restrictions),
please complete the setup manually:

1. Open PowerShell as Administrator:
   - Right-click PowerShell
   - Select "Run as Administrator"

2. Navigate to the repository:
   cd C:\Users\Admin\Documents\GitHub\graphiti

3. Run the setup script:
   .\setup-graphiti-env.ps1

4. Restart Claude Code after the script completes

The script will automatically:
- Read your credentials from credentials.txt
- Detect if you're in a VM and fix the URI scheme if needed
- Set all required system environment variables
- Validate the configuration
```

→ **STOP HERE** - Do not proceed to Step 5 (manual environment variable setting)

### Step 1C: Check Existing Environment Variables

**Say to user**:
```
Checking for existing Neo4j environment variables...
```

**Windows**:
```powershell
[Environment]::GetEnvironmentVariable('NEO4J_URI', 'Machine')
[Environment]::GetEnvironmentVariable('NEO4J_USER', 'Machine')
[Environment]::GetEnvironmentVariable('NEO4J_PASSWORD', 'Machine')
[Environment]::GetEnvironmentVariable('NEO4J_DATABASE', 'Machine')
```

**macOS/Linux**:
```bash
echo $NEO4J_URI
echo $NEO4J_USER
echo $NEO4J_PASSWORD
echo $NEO4J_DATABASE
```

**If all required variables found** (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD):
```
Found existing Neo4j environment variables:
✓ NEO4J_URI = [show URI]
✓ NEO4J_USER = [show username]
✓ NEO4J_PASSWORD = [masked - show first 10 chars]***
✓ NEO4J_DATABASE = [show database or 'neo4j' default]
```

**Store in credentials dictionary**:
```python
credentials = {
    'NEO4J_URI': env_neo4j_uri,
    'NEO4J_USERNAME': env_neo4j_user,
    'NEO4J_PASSWORD': env_neo4j_password,
    'NEO4J_DATABASE': env_neo4j_database or 'neo4j'
}
```

→ Proceed to Step 3 (Detect VM Environment)

**If any required variables missing**:
```
Some required environment variables are missing:
[List which ones are missing]

These credentials haven't been set up yet. Would you like me to collect
your credentials interactively?
```

**If user says yes**: Proceed to Step 1B (Elicit Credentials)
**If user says no**: Inform user they need to set up credentials first and STOP

## Step 2: Parse Credentials from File

**If from file**:
```bash
# Read and parse credentials.txt
cat credentials.txt
```

Parse the file looking for these keys:
- `NEO4J_URI=...`
- `NEO4J_USERNAME=...`
- `NEO4J_PASSWORD=...`
- `NEO4J_DATABASE=...` (optional)

**Extract values** into a credentials dictionary.

**Validate** all required fields are present:
- NEO4J_URI (required)
- NEO4J_USERNAME (required)
- NEO4J_PASSWORD (required)

**If missing required fields**:
```
Error: credentials.txt is missing required fields: [list missing fields]

Please update credentials.txt to include all required information, or let me
collect the credentials interactively.

Would you like me to collect the credentials from you instead? (yes/no)
```

If yes → Go to Step 1B

## Step 3: Detect VM Environment

**Action**: Determine if the user is running in a Virtual Machine.

**Ask user**:
```
Are you running this on a Virtual Machine (like Proxmox, VMware, VirtualBox,
Hyper-V, or WSL2)? (yes/no)
```

**Store answer** as `is_vm` boolean.

**Alternative**: Try to detect automatically (platform-specific):

**Windows**:
```powershell
Get-WmiObject -Class Win32_ComputerSystem | Select-Object Model
```
Check if Model contains: `Virtual`, `VMware`, `VirtualBox`, `QEMU`, `Hyper-V`, `Proxmox`

**Linux/Mac**:
```bash
# Check for VM indicators
sudo dmidecode -s system-product-name
# Or
hostnamectl | grep Chassis
```

## Step 4: Fix URI Scheme for VMs

**If `is_vm == true`** AND **URI starts with `neo4j+s://`**:

**Inform user**:
```
I detected you're running in a VM. I'm going to change the URI scheme from
neo4j+s:// to neo4j+ssc:// to prevent SSL certificate routing errors.

This is a known issue where Neo4j Aura's self-signed certificates don't work
with the neo4j+s:// scheme in VM environments.

Original URI: [show original]
Fixed URI:    [show with neo4j+ssc://]

This change maintains full encryption while using the correct certificate validation.
```

**Update URI**:
```python
if is_vm and credentials['NEO4J_URI'].startswith('neo4j+s://'):
    credentials['NEO4J_URI'] = credentials['NEO4J_URI'].replace('neo4j+s://', 'neo4j+ssc://')
```

## Step 5: Test Connection to Neo4j Aura

**IMPORTANT**: Before setting environment variables, validate the credentials by testing the connection.

**Say to user**:
```
Testing connection to Neo4j Aura with your credentials...
```

**Test connection using Python**:
```python
# Test Neo4j connection
from neo4j import GraphDatabase
import sys

uri = credentials['NEO4J_URI']
username = credentials['NEO4J_USERNAME']
password = credentials['NEO4J_PASSWORD']

try:
    driver = GraphDatabase.driver(uri, auth=(username, password))
    driver.verify_connectivity()
    print("✓ Connection successful!")
    driver.close()
except Exception as e:
    print(f"✗ Connection failed: {e}")
    sys.exit(1)
```

### If Connection Succeeds

**Say to user**:
```
✓ Successfully connected to Neo4j Aura!
  Database: [show URI without credentials]
  User: [show username]

Your credentials are valid. Proceeding with environment variable setup...
```

→ Proceed to Step 6 (Set Environment Variables)

### If Connection Fails - Diagnose and Report

**Analyze the error** and categorize it:

#### Error Type 1: Authentication Failure

**Error contains**: `AuthError`, `Unauthorized`, `authentication failed`, `invalid credentials`

**Say to user**:
```
✗ Authentication Failed

The credentials appear to be incorrect. Common causes:
- Wrong password (passwords are case-sensitive)
- Wrong username (should typically be 'neo4j')
- Password was recently changed in Neo4j Aura console

Please double-check your credentials from the Neo4j Aura console:
https://console.neo4j.io

Would you like to:
1. Re-enter your credentials
2. Check Neo4j Aura console and try again
```

**If user chooses option 1**: Go back to Step 1B (Elicit Credentials)
**If user chooses option 2**: STOP and wait for user to verify credentials

#### Error Type 2: Network/Connection Failure

**Error contains**: `ServiceUnavailable`, `Unable to retrieve routing information`, `Connection refused`, `timeout`, `no route to host`

**Say to user**:
```
✗ Network Connection Failed

Cannot reach Neo4j Aura. Possible causes:

1. **Instance not running**: Check https://console.neo4j.io
   - Ensure instance status is "Running" (not "Stopped" or "Paused")

2. **Firewall blocking**: Your network may block outbound HTTPS (port 7687)
   - Check firewall/antivirus settings

3. **URI scheme issue**: [show current URI scheme]
   - You're using: [neo4j+s:// or neo4j+ssc://]
   - Running in VM: [yes/no]

Would you like me to try fixing the URI scheme automatically?
(This will change neo4j+s:// to neo4j+ssc:// if you're in a VM)
```

**If user says yes**:
- If in VM and using `neo4j+s://`: Change to `neo4j+ssc://` and retry connection test
- If already using `neo4j+ssc://` or not in VM:
  ```
  The URI scheme looks correct. This is likely a firewall or instance issue.
  Please check:
  1. Neo4j Aura instance is running
  2. Your firewall allows outbound connections on port 7687
  ```

**If user says no**: STOP and report issue for user to resolve

#### Error Type 3: SSL/Certificate Error

**Error contains**: `SSLError`, `certificate verify failed`, `SSL handshake`

**Say to user**:
```
✗ SSL Certificate Error

The SSL certificate validation failed. This typically happens in VM environments.

Current URI: [show URI]
Running in VM: [yes/no]

Would you like me to fix this by changing to neo4j+ssc://
(which accepts self-signed certificates)?
```

**If user says yes**: Change URI to `neo4j+ssc://` and retry connection test
**If user says no**: STOP and report issue

#### Error Type 4: Database Not Found

**Error contains**: `database does not exist`, `DatabaseNotFound`

**Say to user**:
```
✗ Database Not Found

The database '[show database name]' doesn't exist in your Neo4j Aura instance.

Common causes:
- Typo in database name
- Database name should typically be 'neo4j' for Aura free tier

Would you like me to:
1. Try using the default database name 'neo4j'
2. Let you specify a different database name
```

**Handle based on user choice**

#### Error Type 5: Unknown Error

**Say to user**:
```
✗ Connection Test Failed

An unexpected error occurred:
[Show full error message]

This doesn't match any known error patterns. Please:
1. Verify your Neo4j Aura instance is running at https://console.neo4j.io
2. Check that your credentials are correct
3. Ensure you have network connectivity

Would you like to:
1. Re-enter credentials and try again
2. Skip connection test and proceed with setup (not recommended)
```

**Important**: Do NOT automatically proceed if connection test fails. Always report to user first and get their decision.

## Step 6: Set Environment Variables

**Environment variables to set**:
```
NEO4J_URI = <from credentials>
NEO4J_USER = <from credentials['NEO4J_USERNAME']>
NEO4J_PASSWORD = <from credentials>
NEO4J_DATABASE = <from credentials, or 'neo4j'>
```

### Platform-Specific Commands:

**Windows (PowerShell - requires Admin)**:
```powershell
# Must be run as Administrator
[Environment]::SetEnvironmentVariable('NEO4J_URI', 'value_here', 'Machine')
[Environment]::SetEnvironmentVariable('NEO4J_USER', 'value_here', 'Machine')
[Environment]::SetEnvironmentVariable('NEO4J_PASSWORD', 'value_here', 'Machine')
```

**macOS/Linux (add to shell profile)**:
```bash
# Add to ~/.bashrc or ~/.zshrc
export NEO4J_URI="value_here"
export NEO4J_USER="value_here"
export NEO4J_PASSWORD="value_here"

# Then reload
source ~/.bashrc  # or ~/.zshrc
```

**For each variable set**:
- Display confirmation: `[OK] NEO4J_URI = neo4j+ssc://...`
- For password, mask it: `[OK] NEO4J_PASSWORD = GgY-tiSw3N***`

**If user doesn't have admin/sudo**:
```
Warning: Setting system-level environment variables requires Administrator/sudo access.

Would you like me to:
1. Show you the commands to run manually
2. Guide you through getting admin access
3. Set user-level variables instead (may not work for all applications)
```

## Step 7: Check for OpenAI API Key

**Action**: Verify OPENAI_API_KEY is set.

**Windows**:
```powershell
[Environment]::GetEnvironmentVariable('OPENAI_API_KEY', 'Machine')
```

**macOS/Linux**:
```bash
echo $OPENAI_API_KEY
```

**If NOT set**:
```
Warning: OPENAI_API_KEY environment variable is not set.

Graphiti requires an OpenAI API key for LLM operations. You can:
1. Get an API key from: https://platform.openai.com/api-keys
2. Set it as an environment variable

Would you like to set it now? (yes/no)
```

**If yes**:
- Ask: "Please enter your OpenAI API key (starts with 'sk-'):"
- Set using same method as Step 6

## Step 8: Validation

**Verify each environment variable was set correctly**:

**Windows**:
```powershell
[Environment]::GetEnvironmentVariable('NEO4J_URI', 'Machine')
[Environment]::GetEnvironmentVariable('NEO4J_USER', 'Machine')
[Environment]::GetEnvironmentVariable('NEO4J_PASSWORD', 'Machine')
[Environment]::GetEnvironmentVariable('OPENAI_API_KEY', 'Machine')
```

**macOS/Linux**:
```bash
echo $NEO4J_URI
echo $NEO4J_USER
echo $NEO4J_PASSWORD
echo $OPENAI_API_KEY
```

**For each variable**:
- `[OK] Variable_Name verified` if value matches what was set
- `[FAIL] Variable_Name verification failed` if mismatch

**Display summary**:
```
========================================
 VALIDATION RESULTS
========================================

[OK] NEO4J_URI = neo4j+ssc://xxx.databases.neo4j.io
[OK] NEO4J_USER = neo4j
[OK] NEO4J_PASSWORD = verified
[OK] OPENAI_API_KEY = verified

All environment variables configured successfully!
```

## Step 9: Next Steps Instructions

**Tell the user**:
```
========================================
 SETUP COMPLETE!
========================================

Environment variables have been successfully configured.

NEXT STEPS:

1. Restart Claude Code (or any application that will use these variables)
   - Environment variables are loaded when an application starts
   - Existing instances won't see the new values until restarted

2. Install Graphiti dependencies:
   cd /path/to/graphiti/mcp_server
   uv sync

3. Test the connection:
   The Graphiti MCP server should now connect to Neo4j Aura automatically
   when you restart Claude Code.

4. Test with multiple instances:
   You can now run multiple Claude Code instances simultaneously,
   and they will all connect to the same cloud database.
```

**If VM URI fix was applied**:
```
VM Configuration Note:
Your URI scheme was automatically adjusted to neo4j+ssc:// to prevent SSL
certificate routing errors in Virtual Machine environments. This is the
recommended configuration for VMs.
```

## Troubleshooting Guidance

**If validation fails**:
```
Some environment variables could not be verified. This might be because:

1. On Windows: Environment variables need system restart or new shell session
   → Try opening a new PowerShell window and checking again
   → Or restart your system

2. On macOS/Linux: Shell profile wasn't reloaded
   → Try: source ~/.bashrc (or ~/.zshrc)
   → Or open a new terminal window

3. Insufficient permissions
   → Ensure you're running as Administrator (Windows) or using sudo (Unix)

Would you like me to help diagnose the issue?
```

## Error Handling

### If credentials file is malformed:
```
Error: Could not parse credentials.txt

The file should contain lines in this format:
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

Would you like me to collect the credentials interactively instead?
```

### If environment variable setting fails:
```
Error: Failed to set environment variable [Variable_Name]

This usually means:
- Insufficient permissions (need Administrator/sudo)
- System policy prevents setting environment variables
- Platform-specific issue

Would you like to try a different approach?
```

## Completion Checklist

Before finishing, confirm:
- [ ] All required environment variables are set
- [ ] Variables are set at system/global level (not just session)
- [ ] Password is masked when displayed
- [ ] VM URI scheme fix applied if needed
- [ ] User knows to restart Claude Code
- [ ] User knows next steps (uv sync, testing)

## Example Full Interaction

```
Agent: I'll help you set up environment variables for Graphiti. Let me check for a credentials file...

[checks for credentials.txt]

Agent: I couldn't find credentials.txt. I'll collect your Neo4j Aura credentials interactively.

Do you have Neo4j Aura credentials? If not, create a free instance at: https://console.neo4j.io

User: Yes, I have them

Agent: Great! What is your Neo4j Aura connection URI?

User: neo4j+s://YOUR_INSTANCE_ID.databases.neo4j.io

Agent: What is your Neo4j username? (typically 'neo4j')

User: neo4j

Agent: What is your Neo4j password?

User: YOUR_PASSWORD_HERE

Agent: Are you running this in a Virtual Machine (Proxmox, VMware, etc.)?

User: Yes, Proxmox

Agent: I detected you're in a VM. I'll change the URI scheme to neo4j+ssc:// to prevent routing errors...

[sets environment variables]

Agent: [OK] NEO4J_URI = neo4j+ssc://YOUR_INSTANCE_ID.databases.neo4j.io
[OK] NEO4J_USER = neo4j
[OK] NEO4J_PASSWORD = GgY-tiSw3N***

[validates]

Agent: Setup complete! Next steps: Restart Claude Code and run 'uv sync' in the mcp_server directory.
```

---

**Last Updated**: 2025-10-22
**Maintained By**: AI Agents (Claude)
