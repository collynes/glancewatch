#!/bin/bash
# GlanceWatch Installation Script
# Usage: curl -sSL https://raw.githubusercontent.com/collynes/glancewatch/main/scripts/install-pip.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║   ██████╗ ██╗      █████╗ ███╗   ██╗ ██████╗███████╗      ║"
echo "║  ██╔════╝ ██║     ██╔══██╗████╗  ██║██╔════╝██╔════╝      ║"
echo "║  ██║  ███╗██║     ███████║██╔██╗ ██║██║     █████╗        ║"
echo "║  ██║   ██║██║     ██╔══██║██║╚██╗██║██║     ██╔══╝        ║"
echo "║  ╚██████╔╝███████╗██║  ██║██║ ╚████║╚██████╗███████╗      ║"
echo "║   ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝      ║"
echo "║                    WATCH                                  ║"
echo "║                                                           ║"
echo "║          Lightweight Monitoring Adapter                   ║"
echo "║       Glances + Uptime Kuma Integration                   ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Running as root. Consider using a non-root user.${NC}"
fi

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            echo "debian"
        elif [ -f /etc/redhat-release ]; then
            echo "redhat"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo -e "${BLUE}Detected OS: ${OS}${NC}"

# Check for Python 3
echo -e "\n${BLUE}[1/4] Checking Python installation...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"
else
    echo -e "${RED}✗ Python 3 not found${NC}"
    echo -e "${YELLOW}Please install Python 3.8 or later:${NC}"
    case $OS in
        debian)
            echo "  sudo apt update && sudo apt install -y python3 python3-pip"
            ;;
        redhat)
            echo "  sudo dnf install -y python3 python3-pip"
            ;;
        macos)
            echo "  brew install python3"
            ;;
        *)
            echo "  Visit https://www.python.org/downloads/"
            ;;
    esac
    exit 1
fi

# Check for pip
echo -e "\n${BLUE}[2/4] Checking pip installation...${NC}"
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✓ pip3 found${NC}"
    PIP_CMD="pip3"
elif python3 -m pip --version &> /dev/null; then
    echo -e "${GREEN}✓ pip module found${NC}"
    PIP_CMD="python3 -m pip"
else
    echo -e "${YELLOW}Installing pip...${NC}"
    case $OS in
        debian)
            sudo apt update && sudo apt install -y python3-pip
            ;;
        redhat)
            sudo dnf install -y python3-pip
            ;;
        macos)
            python3 -m ensurepip --upgrade
            ;;
        *)
            curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
            python3 get-pip.py
            rm get-pip.py
            ;;
    esac
    PIP_CMD="pip3"
fi

# Install GlanceWatch
echo -e "\n${BLUE}[3/4] Installing GlanceWatch...${NC}"
$PIP_CMD install --upgrade glancewatch

# Verify installation
echo -e "\n${BLUE}[4/4] Verifying installation...${NC}"
if command -v glancewatch &> /dev/null; then
    GLANCEWATCH_VERSION=$(glancewatch --version 2>&1 || echo "installed")
    echo -e "${GREEN}✓ GlanceWatch installed successfully${NC}"
else
    # Check if installed but not in PATH
    GLANCEWATCH_PATH=$(python3 -c "import site; print(site.USER_BASE + '/bin/glancewatch')" 2>/dev/null)
    if [ -f "$GLANCEWATCH_PATH" ]; then
        echo -e "${YELLOW}⚠ GlanceWatch installed but not in PATH${NC}"
        echo -e "${YELLOW}Add this to your shell profile (~/.bashrc or ~/.zshrc):${NC}"
        echo -e "  export PATH=\"\$PATH:$(dirname $GLANCEWATCH_PATH)\""
    else
        echo -e "${GREEN}✓ GlanceWatch installed via pip${NC}"
    fi
fi

# Ask about systemd service (Linux only)
if [[ "$OS" == "debian" || "$OS" == "redhat" || "$OS" == "linux" ]]; then
    echo -e "\n${BLUE}Would you like to install GlanceWatch as a systemd service? (y/N)${NC}"
    read -r INSTALL_SERVICE
    
    if [[ "$INSTALL_SERVICE" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Installing systemd service...${NC}"
        
        # Create systemd service file
        GLANCEWATCH_BIN=$(command -v glancewatch || python3 -c "import site; print(site.USER_BASE + '/bin/glancewatch')")
        
        sudo tee /etc/systemd/system/glancewatch.service > /dev/null << EOF
[Unit]
Description=GlanceWatch - Glances + Uptime Kuma Monitoring Adapter
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=$GLANCEWATCH_BIN
Restart=always
RestartSec=10
WorkingDirectory=$HOME

[Install]
WantedBy=multi-user.target
EOF
        
        # Enable and start service
        sudo systemctl daemon-reload
        sudo systemctl enable glancewatch
        sudo systemctl start glancewatch
        
        echo -e "${GREEN}✓ GlanceWatch service installed and started${NC}"
        echo -e "${BLUE}Service commands:${NC}"
        echo "  sudo systemctl status glancewatch  # Check status"
        echo "  sudo systemctl restart glancewatch # Restart"
        echo "  sudo systemctl stop glancewatch    # Stop"
        echo "  sudo journalctl -u glancewatch -f  # View logs"
    fi
fi

# Print success message
echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Installation Complete! 🎉                        ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Quick Start:${NC}"
echo "  glancewatch              # Start GlanceWatch"
echo "  glancewatch --help       # Show help"
echo ""
echo -e "${BLUE}Web Interface:${NC}"
echo "  Dashboard:    http://localhost:8000"
echo "  API Docs:     http://localhost:8000/api"
echo "  Health Check: http://localhost:8000/health"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo "  https://github.com/collynes/glancewatch"
echo ""
echo -e "${GREEN}Happy monitoring! 📊${NC}"
