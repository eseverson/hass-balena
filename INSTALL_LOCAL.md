# 🏠 Local Installation Guide

This guide will help you install the Balena Cloud integration directly to your Home Assistant instance without using HACS.

## 📋 Prerequisites

- Home Assistant instance (OS, Supervised, Core, or Container)
- Access to your Home Assistant configuration directory
- Linux/macOS/WSL environment (for automated installation) OR
- File browser access (for manual installation)

## 🚀 Quick Installation (Recommended)

### **Automated Installation Script**

The installation script includes comprehensive error handling, permission checking, and troubleshooting guidance.

```bash
# 1. Download or clone this repository
git clone <repository-url>
cd hass-balena

# 2. Run the installation script
./install_local.sh
```

#### **Script Features:**
- ✅ **Automatic directory detection** - Finds your HA config automatically
- ✅ **Permission checking** - Tests write permissions before attempting installation
- ✅ **Detailed error messages** - Clear explanations when things go wrong
- ✅ **Step-by-step progress** - Shows exactly what the script is doing
- ✅ **Installation verification** - Confirms all files were copied correctly
- ✅ **Colored output** - Easy-to-read status messages

#### **Getting Help:**
```bash
# View script help and options
./install_local.sh --help
```

## 🛠️ Permission Issues? No Problem!

The script detects permission issues and provides specific guidance:

### **Common Permission Solutions:**

```bash
# Option 1: Run with sudo (if safe)
sudo ./install_local.sh

# Option 2: Fix directory ownership
sudo chown -R $(whoami) /path/to/homeassistant/config

# Option 3: For Home Assistant Core users
sudo chown -R homeassistant:homeassistant ~/.homeassistant
```

#### **Docker/Container:**
```bash
# Copy files into running container
docker exec -it homeassistant bash
cd /config
# Then follow manual installation steps inside container
```

## 📁 Manual Installation

### **Step 1: Locate Your Home Assistant Configuration Directory**

Find your Home Assistant config directory based on your installation type:

| Installation Type | Default Path |
|-------------------|--------------|
| **Home Assistant OS** | `/config/` |
| **Home Assistant Supervised** | `/usr/share/hassio/homeassistant/` |
| **Home Assistant Core** | `~/.homeassistant/` or `~/.config/homeassistant/` |
| **Home Assistant Container** | Your mounted `/config` volume |
| **Windows (WSL)** | Follow WSL path conventions |

### **Step 2: Create Directory Structure**

In your Home Assistant config directory, create:
```
config/
└── custom_components/
    └── balena_cloud/
```

### **Step 3: Copy Integration Files**

Copy all files from this repository's `custom_components/balena_cloud/` directory to your newly created `config/custom_components/balena_cloud/` directory.

**Required files:**
- `__init__.py` - Main integration setup
- `manifest.json` - Integration metadata
- `config_flow.py` - Configuration wizard
- `const.py` - Constants and configuration
- `api.py` - Balena Cloud API client
- `models.py` - Data models
- `coordinator.py` - Data update coordinator
- `sensor.py` - Sensor entities
- `binary_sensor.py` - Binary sensor entities
- `button.py` - Button entities
- `device_card.py` - Device dashboard cards
- `fleet_overview.py` - Fleet overview components
- `services.py` - Service handlers

## 🔧 Installation Methods by Home Assistant Type

### **Home Assistant OS/Supervised**

#### **Method 1: SSH + SCP**
```bash
# Copy files via SCP
scp -r ./custom_components/balena_cloud/ root@your-ha-ip:/config/custom_components/
```

#### **Method 2: File Editor Add-on**
1. Install "File Editor" add-on
2. Navigate to `/config/custom_components/`
3. Create `balena_cloud` folder
4. Create each file and copy/paste contents

#### **Method 3: Samba Share**
1. Install "Samba share" add-on
2. Access `\\your-ha-ip\config` from your computer
3. Copy the `balena_cloud` folder to `custom_components/`

### **Home Assistant Core**

#### **Direct Copy:**
```bash
# Navigate to your HA config directory
cd ~/.homeassistant
# OR
cd ~/.config/homeassistant

# Create custom_components if it doesn't exist
mkdir -p custom_components

# Copy the integration
cp -r /path/to/hass-balena/custom_components/balena_cloud custom_components/
```

### **Home Assistant Container (Docker)**

#### **Volume Mount Method:**
```bash
# If you have a volume mounted to /config
docker cp ./custom_components/balena_cloud/ homeassistant:/config/custom_components/
```

#### **Docker Compose:**
```yaml
# Add to your docker-compose.yml volumes section
volumes:
  - ./config:/config
  - ./custom_components:/config/custom_components  # Add this line
```

### **Windows Users**

#### **Using WSL (Recommended):**
```bash
# In WSL
cd /mnt/c/path/to/hass-balena
./install_local.sh
```

#### **Manual File Copy:**
1. Use Windows File Explorer to navigate to your Home Assistant config
2. Create `custom_components\balena_cloud\` folder
3. Copy all integration files manually

## ✅ Verify Installation

After copying files, verify the installation:

1. **Check file structure:**
   ```
   config/
   └── custom_components/
       └── balena_cloud/
           ├── __init__.py
           ├── manifest.json
           ├── config_flow.py
           └── ... (other files)
   ```

2. **Check Home Assistant logs:**
   ```bash
   # Look for any integration loading errors
   tail -f /config/home-assistant.log | grep balena_cloud
   ```

3. **Use the verification script:**
   ```bash
   # The installation script includes automatic verification
   # Look for "Installation verification passed" message
   ```

## 🔄 Complete Setup Process

### **Step 1: Restart Home Assistant**
After copying files, restart Home Assistant completely:
- **Home Assistant OS/Supervised**: `Settings > System > Hardware > Restart`
- **Home Assistant Core**: `sudo systemctl restart home-assistant@homeassistant`
- **Container**: `docker restart homeassistant`

### **Step 2: Add Integration**
1. Go to `Settings > Devices & Services`
2. Click `+ Add Integration`
3. Search for "Balena Cloud"
4. Click on the integration to start setup

### **Step 3: Configuration**
1. Enter your Balena Cloud API token
2. Select the fleets you want to monitor
3. Configure update intervals and options
4. Complete the setup wizard

### **Step 4: Verify Setup**
- Check that devices appear in `Settings > Devices & Services`
- Verify entities are created in `Developer Tools > States`
- Test device controls and monitoring

## 🛠️ Enhanced Troubleshooting

### **Script-Specific Troubleshooting**

The installation script provides detailed error messages and solutions:

#### **"Permission denied" errors:**
```bash
# The script will show:
❌ No write permission to: /config
❌ Current user: username
❌ Try: sudo chown -R $(whoami) "/config"

# Solutions provided:
1. Run with sudo: sudo ./install_local.sh
2. Fix permissions: sudo chown -R $(whoami) "/config"
3. Use manual installation method
```

#### **"Directory not found" errors:**
```bash
# The script will show:
❌ Could not automatically find Home Assistant configuration directory.

# Common locations:
  - /config (Home Assistant OS/Supervised)
  - ~/.homeassistant (Home Assistant Core)
  - ~/.config/homeassistant (Alternative Core location)
```

### **Integration Not Found**
- ✅ Verify files are in correct location: `config/custom_components/balena_cloud/`
- ✅ Check that `manifest.json` exists and is valid JSON
- ✅ Restart Home Assistant completely (not just reload)
- ✅ Check Home Assistant logs for specific error messages

### **Permission Issues**
```bash
# Linux/macOS - Set correct permissions
chmod -R 755 /config/custom_components/balena_cloud/
chown -R homeassistant:homeassistant /config/custom_components/balena_cloud/
```

### **API Connection Issues**
- ✅ Verify your Balena Cloud API token is valid at [Balena Dashboard](https://dashboard.balena-cloud.com)
- ✅ Check internet connectivity from Home Assistant host
- ✅ Ensure Home Assistant can reach `api.balena-cloud.com`
- ✅ Check firewall settings for outbound HTTPS connections

### **Missing Dependencies**
The integration handles all dependencies automatically, but if you encounter issues:
```bash
# For Home Assistant Core installations
pip install aiohttp>=3.8.0
```

## 📝 Update Process

To update the integration:

1. **Download new version** of the integration files
2. **Run installation script again** (it will replace existing files)
   ```bash
   ./install_local.sh  # Automatically handles updates
   ```
3. **Restart Home Assistant**
4. **Check logs** for any issues

## 🔒 Security Notes

- Store your Balena Cloud API token securely
- The integration uses Home Assistant's built-in credential storage
- All API communications use HTTPS with certificate validation
- No sensitive data is logged in plain text
- The installation script sanitizes and validates all inputs

## 📞 Enhanced Support

The installation script provides comprehensive diagnostics:

1. **Detailed error messages** with specific solutions
2. **Permission analysis** showing ownership and access rights
3. **Path validation** with suggestions for common locations
4. **File verification** ensuring all components are installed correctly

If you still encounter issues:

1. **Check script output** for specific error messages and suggested solutions
2. **Use manual installation** if automated script fails
3. **Check Home Assistant logs** for integration-specific errors

## 🎉 Success!

Once installed successfully, you'll have:

- 📊 **Device monitoring** - CPU, memory, storage, temperature
- 🔄 **Device control** - Restart applications, reboot devices
- 📱 **Dashboard cards** - Rich device status displays
- 🏢 **Fleet management** - Bulk operations and fleet overviews
- 🤖 **Automation support** - Triggers and actions for automations

The installation script ensures a smooth setup process with clear guidance when issues arise.

Happy monitoring! 🚀