#!/bin/bash

# Balena Cloud Integration Local Installation Script
# This script helps install the integration to a local Home Assistant instance

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }

echo -e "${BLUE}🏠 Balena Cloud Integration - Local Installation${NC}"
echo "================================================="

# Default Home Assistant configuration paths
DEFAULT_PATHS=(
    "/config"
    "$HOME/.homeassistant"
    "$HOME/.config/homeassistant"
    "/home/homeassistant/.homeassistant"
    "/usr/share/hassio/homeassistant"
)

# Function to find Home Assistant config directory
find_ha_config() {
    print_info "Looking for Home Assistant configuration directory..." >&2

    for path in "${DEFAULT_PATHS[@]}"; do
        if [ -d "$path" ] && [ -f "$path/configuration.yaml" ]; then
            print_success "Found Home Assistant config at: $path" >&2
            echo "$path"
            return 0
        fi
    done

    print_error "Could not automatically find Home Assistant configuration directory." >&2
    echo "" >&2
    echo "Common locations:" >&2
    echo "  - /config (Home Assistant OS/Supervised)" >&2
    echo "  - ~/.homeassistant (Home Assistant Core)" >&2
    echo "  - ~/.config/homeassistant (Alternative Core location)" >&2
    echo "" >&2
    read -p "Enter full path to your HA config directory: " manual_path

    if [ -d "$manual_path" ] && [ -f "$manual_path/configuration.yaml" ]; then
        print_success "Using specified path: $manual_path" >&2
        echo "$manual_path"
        return 0
    else
        print_error "Invalid path or configuration.yaml not found" >&2
        exit 1
    fi
}

# Function to check write permissions
check_write_permission() {
    local dir="$1"

    if [ ! -d "$dir" ]; then
        if ! mkdir -p "$dir" 2>/dev/null; then
            print_error "Cannot create directory: $dir"
            print_error "Permission denied. Try running with sudo or fix permissions."
            return 1
        fi
    fi

    local test_file="$dir/.write_test_$$"
    if ! touch "$test_file" 2>/dev/null; then
        print_error "No write permission to: $dir"
        print_error "Current user: $(whoami)"
        print_error "Try: sudo chown -R \$(whoami) \"$dir\""
        return 1
    fi

    rm -f "$test_file" 2>/dev/null
    return 0
}

# Main installation process
main() {
    # Check if we're in the right directory
    if [ ! -d "./custom_components/balena_cloud" ]; then
        print_error "This script must be run from the project root directory."
        print_error "Make sure you're in the directory containing 'custom_components/balena_cloud/'"
        exit 1
    fi

    # Find Home Assistant configuration directory (call only once!)
    CONFIG_DIR=$(find_ha_config)

    if [ -z "$CONFIG_DIR" ]; then
        print_error "Failed to determine config directory"
        exit 1
    fi

    CUSTOM_COMPONENTS_DIR="$CONFIG_DIR/custom_components"
    TARGET_DIR="$CUSTOM_COMPONENTS_DIR/balena_cloud"

    # Confirm installation
    echo ""
    print_info "Installation target: $TARGET_DIR"
    print_warning "This will replace any existing Balena Cloud integration"
    echo ""
    read -p "❓ Continue with installation? (y/N): " confirm

    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_warning "Installation cancelled by user."
        exit 0
    fi

    echo ""
    print_info "🚀 Starting installation..."
    echo ""

    # Step 1: Check permissions
    print_info "Step 1: Checking permissions..."
    if ! check_write_permission "$CONFIG_DIR"; then
        print_error "Cannot write to Home Assistant config directory"
        echo ""
        echo "Solutions:"
        echo "  1. Run with sudo: sudo ./install_local_fixed.sh"
        echo "  2. Fix permissions: sudo chown -R \$(whoami) \"$CONFIG_DIR\""
        exit 1
    fi
    print_success "Write permissions confirmed"

    # Step 2: Create custom_components directory
    print_info "Step 2: Creating custom_components directory..."
    if ! mkdir -p "$CUSTOM_COMPONENTS_DIR" 2>/dev/null; then
        print_error "Failed to create custom_components directory"
        exit 1
    fi
    print_success "Custom components directory ready"

    # Step 3: Remove existing installation
    print_info "Step 3: Removing existing installation (if any)..."
    if [ -d "$TARGET_DIR" ]; then
        if ! rm -rf "$TARGET_DIR" 2>/dev/null; then
            print_error "Failed to remove existing installation"
            exit 1
        fi
        print_success "Removed existing installation"
    else
        print_info "No existing installation found"
    fi

    # Step 4: Copy integration files
    print_info "Step 4: Copying integration files..."
    if ! cp -r "./custom_components/balena_cloud" "$TARGET_DIR" 2>/dev/null; then
        print_error "Failed to copy integration files"
        print_error "Source: ./custom_components/balena_cloud"
        print_error "Target: $TARGET_DIR"
        exit 1
    fi
    print_success "Integration files copied successfully"

    # Step 5: Set permissions
    print_info "Step 5: Setting permissions..."
    if ! chmod -R 755 "$TARGET_DIR" 2>/dev/null; then
        print_warning "Could not set permissions (integration may still work)"
    else
        print_success "Permissions set successfully"
    fi

    # Step 6: Set ownership (if possible)
    print_info "Step 6: Setting ownership..."
    local ha_user=""
    if id "homeassistant" &>/dev/null; then
        ha_user="homeassistant"
    elif id "hass" &>/dev/null; then
        ha_user="hass"
    fi

    if [ -n "$ha_user" ]; then
        if chown -R "$ha_user:$ha_user" "$TARGET_DIR" 2>/dev/null; then
            print_success "Ownership set to $ha_user"
        else
            print_warning "Could not set ownership (integration may still work)"
        fi
    else
        print_info "Home Assistant user not found, keeping current ownership"
    fi

    # Step 7: Verify installation
    print_info "Step 7: Verifying installation..."

    local required_files=("manifest.json" "__init__.py" "config_flow.py" "const.py" "api.py")
    local missing_files=()

    for file in "${required_files[@]}"; do
        if [ ! -f "$TARGET_DIR/$file" ]; then
            missing_files+=("$file")
        fi
    done

    if [ ${#missing_files[@]} -gt 0 ]; then
        print_error "Installation verification failed - missing files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        exit 1
    fi

    print_success "Installation verification passed"

    # Installation complete
    echo ""
    print_success "🎉 Balena Cloud integration installed successfully!"
    echo ""
    print_info "Installation details:"
    echo "  Location: $TARGET_DIR"
    echo "  Files: $(find "$TARGET_DIR" -type f | wc -l) files installed"
    echo "  Size: $(du -sh "$TARGET_DIR" | cut -f1)"
    echo ""
    print_info "Next steps:"
    echo "  1. Restart Home Assistant completely"
    echo "  2. Go to Settings > Devices & Services"
    echo "  3. Click 'Add Integration'"
    echo "  4. Search for 'Balena Cloud'"
    echo "  5. Follow the configuration wizard"
    echo ""
    print_warning "⚠️ Important: Restart Home Assistant to complete the installation"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Balena Cloud Integration Local Installation Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo ""
        echo "This script will:"
        echo "  1. Find your Home Assistant configuration directory"
        echo "  2. Create custom_components folder if needed"
        echo "  3. Copy the Balena Cloud integration files"
        echo "  4. Set appropriate permissions"
        echo "  5. Verify the installation"
        echo ""
        exit 0
        ;;
esac

# Run main function
main "$@"