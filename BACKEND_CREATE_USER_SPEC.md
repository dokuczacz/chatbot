# Backend Implementation Spec: Create User Endpoint

## Overview
This document specifies the `create_user` endpoint that should be implemented in the **omniflow-agent-backend** repository.

## Endpoint Details

### Function Name
`create_user`

### HTTP Method
`POST`

### URL
`/api/create_user`

### Request Headers
- `X-User-Id`: (Optional) Admin user ID performing the creation
- `Content-Type`: `application/json`

### Request Body
```json
{
  "user_id": "string (required)",
  "create_default_files": "boolean (optional, default: true)"
}
```

### Response - Success (200)
```json
{
  "status": "success",
  "user_id": "alice_123",
  "message": "User 'alice_123' created successfully",
  "files_created": [
    "users/alice_123/tasks.json",
    "users/alice_123/ideas.json",
    "users/alice_123/notes.json"
  ],
  "timestamp": "2025-12-11T16:30:00Z"
}
```

### Response - Error (400)
```json
{
  "status": "error",
  "error": "Invalid user_id format",
  "message": "User ID must be 3-64 characters, alphanumeric with _, -, or ."
}
```

### Response - Error (409)
```json
{
  "status": "error",
  "error": "User already exists",
  "message": "User 'alice_123' already has files in the system"
}
```

## Implementation Details

### Default Files to Create

1. **tasks.json** - Task management
```json
{
  "tasks": [
    {
      "id": "welcome_task_1",
      "title": "Welcome to OmniFlow!",
      "description": "This is your first task. You can add, update, or remove tasks.",
      "status": "open",
      "priority": "medium",
      "created_at": "2025-12-11T16:30:00Z"
    }
  ]
}
```

2. **ideas.json** - Ideas and brainstorming
```json
{
  "ideas": [
    {
      "id": "welcome_idea_1",
      "content": "Store your ideas here for future reference",
      "category": "general",
      "created_at": "2025-12-11T16:30:00Z"
    }
  ]
}
```

3. **notes.json** - General notes
```json
{
  "notes": [
    {
      "id": "welcome_note_1",
      "content": "Welcome to OmniFlow! Use this space for notes.",
      "tags": ["welcome"],
      "created_at": "2025-12-11T16:30:00Z"
    }
  ]
}
```

### Validation Rules

- **user_id** must match pattern: `^[a-zA-Z0-9._-]{3,64}$`
- User must not already have files in the system
- All default files should be created atomically (all or none)

### Integration with Existing System

This function should:
1. Use `shared/user_manager.py` for user ID validation
2. Use `shared/azure_client.py` for blob operations
3. Use `UserNamespace.get_user_blob_name()` for proper file naming
4. Log operations for audit trail

### Example Implementation Location

Create new function in: `omniflow-agent-backend/create_user/__init__.py`

### Function Configuration

File: `omniflow-agent-backend/create_user/function.json`
```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "authLevel": "function",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": ["post"]
    },
    {
      "type": "http",
      "direction": "out",
      "name": "$return"
    }
  ]
}
```

## Testing

### Test Case 1: Create User with Default Files
```bash
curl -X POST https://agentbackendservice.azurewebsites.net/api/create_user?code=xxx \
  -H "Content-Type: application/json" \
  -H "X-User-Id: admin" \
  -d '{
    "user_id": "test_user_123",
    "create_default_files": true
  }'
```

Expected: 200, files created

### Test Case 2: Invalid User ID
```bash
curl -X POST https://agentbackendservice.azurewebsites.net/api/create_user?code=xxx \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "ab",
    "create_default_files": true
  }'
```

Expected: 400, error message

### Test Case 3: Duplicate User
```bash
# Create same user twice
curl -X POST https://agentbackendservice.azurewebsites.net/api/create_user?code=xxx \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "existing_user",
    "create_default_files": true
  }'
```

Expected: First call 200, second call 409

## UI Integration

The chatbot UI (`streamlit_app.py`) already includes:
- `create_new_user()` function to call this endpoint
- UI checkbox to enable/disable default file creation
- Error handling for missing endpoint (404)
- Success/error messages display

## Notes

- This endpoint should be idempotent where possible
- Consider rate limiting for user creation
- Add admin authentication in production
- Log all user creation events for audit
- Consider adding webhook/notification for user creation
