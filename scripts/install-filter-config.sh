#!/bin/bash
# Install Graphiti filter configuration to global Claude directory

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Installing Graphiti Filter Configuration...${NC}"
echo ""

# Detect platform
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    CLAUDE_DIR="$HOME/.claude"
    PLATFORM="Windows (MSYS)"
else
    CLAUDE_DIR="$HOME/.claude"
    PLATFORM="Unix/macOS"
fi

echo "Platform: $PLATFORM"
echo "Target directory: $CLAUDE_DIR"
echo ""

# Create .claude directory if it doesn't exist
mkdir -p "$CLAUDE_DIR"
echo -e "${GREEN}✅ Created/verified directory: $CLAUDE_DIR${NC}"

# Copy filter config
if [ -f "graphiti-filter.config.json" ]; then
    cp graphiti-filter.config.json "$CLAUDE_DIR/graphiti-filter.config.json"
    echo -e "${GREEN}✅ Deployed filter config to: $CLAUDE_DIR/graphiti-filter.config.json${NC}"
else
    echo -e "${YELLOW}⚠️  graphiti-filter.config.json not found in current directory${NC}"
    echo "Please run this script from the graphiti project root"
    exit 1
fi

# Verify API keys are set
echo ""
echo -e "${BLUE}🔑 Checking API keys...${NC}"

OPENAI_SET=false
ANTHROPIC_SET=false

if [ -n "$OPENAI_API_KEY" ]; then
    echo -e "${GREEN}✅ OPENAI_API_KEY is set${NC}"
    OPENAI_SET=true
else
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY not set (OpenAI provider will be disabled)${NC}"
fi

if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo -e "${GREEN}✅ ANTHROPIC_API_KEY is set${NC}"
    ANTHROPIC_SET=true
else
    echo -e "${YELLOW}⚠️  ANTHROPIC_API_KEY not set (Anthropic provider will be disabled)${NC}"
fi

echo ""

if [ "$OPENAI_SET" = false ] && [ "$ANTHROPIC_SET" = false ]; then
    echo -e "${YELLOW}⚠️  WARNING: No API keys are set!${NC}"
    echo "Memory filtering will be disabled until you configure at least one provider."
    echo ""
fi

echo -e "${GREEN}✨ Installation complete!${NC}"
echo ""
echo "📝 Next steps:"
echo ""

if [ "$OPENAI_SET" = false ] || [ "$ANTHROPIC_SET" = false ]; then
    echo "1. Set API keys in your shell profile (~/.bashrc, ~/.zshrc, or ~/.profile):"
    if [ "$OPENAI_SET" = false ]; then
        echo "   export OPENAI_API_KEY=sk-..."
    fi
    if [ "$ANTHROPIC_SET" = false ]; then
        echo "   export ANTHROPIC_API_KEY=sk-ant-..."
    fi
    echo ""
    echo "2. Restart your shell or run: source ~/.bashrc"
    echo ""
    echo "3. Restart your Graphiti MCP server"
else
    echo "1. Restart your Graphiti MCP server for changes to take effect"
fi

echo ""
echo "📖 Configuration file location:"
echo "   $CLAUDE_DIR/graphiti-filter.config.json"
echo ""
echo "You can edit this file to customize filter settings (providers, models, etc.)"
