#!/bin/bash
# End-to-end test script for Strawberry AI
# Tests the full flow: Spoke -> Hub -> LLM -> Spoke

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== Strawberry AI End-to-End Test ===${NC}"
echo ""

# Check if Hub is running
echo -e "${YELLOW}Step 1: Check Hub status${NC}"
if curl -s http://localhost:8000/health | grep -q '"status":"healthy"'; then
    echo -e "${GREEN}✓ Hub is running${NC}"
else
    echo -e "${RED}✗ Hub is not running${NC}"
    echo -e "Start Hub with: cd ai-hub && source .venv/bin/activate && strawberry-hub"
    exit 1
fi
echo ""

# Create/login user, then create device token
echo -e "${YELLOW}Step 2: Create/login user and create device token${NC}"
USER_COUNT=$(curl -s http://localhost:8000/api/users/count)

if [ "$USER_COUNT" = "0" ]; then
    echo -e "${CYAN}No users found. Creating initial admin user...${NC}"
    USER_TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/users/setup \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "password"}')
else
    echo -e "${CYAN}Users exist. Logging in...${NC}"
    USER_TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/users/login \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "password"}')
fi

if echo "$USER_TOKEN_RESPONSE" | grep -q '"access_token"'; then
    USER_TOKEN=$(echo "$USER_TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
else
    echo -e "${RED}✗ Failed to create/login user${NC}"
    echo "$USER_TOKEN_RESPONSE"
    exit 1
fi

DEVICE_TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/devices/token \
    -H "Authorization: Bearer $USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name": "E2E Test Device"}')

if echo "$DEVICE_TOKEN_RESPONSE" | grep -q '"token"'; then
    DEVICE_TOKEN=$(echo "$DEVICE_TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")
    echo -e "${GREEN}✓ Device token created${NC}"
    echo -e "  Token: ${DEVICE_TOKEN:0:20}..."
else
    echo -e "${RED}✗ Failed to create device token${NC}"
    echo "$DEVICE_TOKEN_RESPONSE"
    exit 1
fi
echo ""

# Test auth/me endpoint
echo -e "${YELLOW}Step 3: Verify authentication${NC}"
ME_RESPONSE=$(curl -s http://localhost:8000/auth/me \
    -H "Authorization: Bearer $DEVICE_TOKEN")

if echo "$ME_RESPONSE" | grep -q '"name":"E2E Test Device"'; then
    echo -e "${GREEN}✓ Authentication working${NC}"
else
    echo -e "${RED}✗ Authentication failed${NC}"
    echo "$ME_RESPONSE"
    exit 1
fi
echo ""

# Test chat endpoint (if LLM configured)
echo -e "${YELLOW}Step 4: Test chat endpoint${NC}"
CHAT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/chat/completions \
    -H "Authorization: Bearer $DEVICE_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"messages": [{"role": "user", "content": "Say hello in exactly 5 words."}]}' \
    --max-time 30)

if echo "$CHAT_RESPONSE" | grep -q '"choices"'; then
    CONTENT=$(echo "$CHAT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['choices'][0]['message']['content'][:50])" 2>/dev/null || echo "Parse error")
    echo -e "${GREEN}✓ Chat endpoint working${NC}"
    echo -e "  Response: $CONTENT..."
else
    echo -e "${YELLOW}⚠ Chat endpoint returned error (LLM may not be configured)${NC}"
    echo "  $CHAT_RESPONSE"
fi
echo ""

# Test skill registration
echo -e "${YELLOW}Step 5: Test skill registration${NC}"
SKILL_RESPONSE=$(curl -s -X POST http://localhost:8000/skills/register \
    -H "Authorization: Bearer $DEVICE_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"skills": [{"class_name": "TestSkill", "function_name": "test_func", "signature": "test_func() -> str", "docstring": "A test function"}]}')

if echo "$SKILL_RESPONSE" | grep -q '"message"'; then
    echo -e "${GREEN}✓ Skill registration working${NC}"
else
    echo -e "${RED}✗ Skill registration failed${NC}"
    echo "$SKILL_RESPONSE"
    exit 1
fi
echo ""

# List skills
echo -e "${YELLOW}Step 6: List skills${NC}"
LIST_RESPONSE=$(curl -s http://localhost:8000/skills \
    -H "Authorization: Bearer $DEVICE_TOKEN")

if echo "$LIST_RESPONSE" | grep -q '"skills"'; then
    TOTAL=$(echo "$LIST_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "?")
    echo -e "${GREEN}✓ Skill listing working ($TOTAL skills)${NC}"
else
    echo -e "${RED}✗ Skill listing failed${NC}"
    echo "$LIST_RESPONSE"
    exit 1
fi
echo ""

echo -e "${CYAN}=== All Tests Passed ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Set HUB_DEVICE_TOKEN=$DEVICE_TOKEN in ai-pc-spoke/.env"
echo "  2. Run Spoke: cd ai-pc-spoke && source .venv/bin/activate && python -m strawberry.main"
echo "  3. Chat with the AI!"
