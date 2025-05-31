# 🚀 Quick Installation Guide

## Easy Installation (Recommended)

### **Step 1: Download the Integration**
```bash
git clone <repository-url>
cd hass-balena
```

### **Step 2: Run the Installation Script**
```bash
./install_local.sh
```

#### **If you get permission errors:**
```bash
# Try with sudo
sudo ./install_local.sh

# Or fix permissions first
sudo chown -R $(whoami) ~/.config/homeassistant
./install_local.sh
```

### **Step 3: Restart Home Assistant**
- **Home Assistant OS**: Settings > System > Hardware > Restart
- **Home Assistant Core**: `sudo systemctl restart home-assistant@homeassistant`
- **Docker**: `docker restart homeassistant`

### **Step 4: Add the Integration**
1. Go to Settings > Devices & Services
2. Click "+ Add Integration"
3. Search for "Balena Cloud"
4. Enter your Balena Cloud API token
5. Select your fleets
6. Complete setup

## What the Script Does

✅ **Automatically finds** your Home Assistant config directory
✅ **Checks permissions** before attempting installation
✅ **Creates directories** as needed
✅ **Copies integration files** safely
✅ **Sets proper permissions** and ownership
✅ **Verifies installation** completeness
✅ **Provides clear feedback** on success or failure

## Troubleshooting

### **"Permission denied" errors**
```bash
# Option 1: Run with sudo
sudo ./install_local.sh

# Option 2: Fix ownership
sudo chown -R $(whoami) /path/to/homeassistant/config
```

### **"Directory not found" errors**
The script will prompt you to manually enter your Home Assistant config path.

Common locations:
- **Home Assistant OS**: `/config/`
- **Home Assistant Core**: `~/.homeassistant/` or `~/.config/homeassistant/`
- **Docker**: Your mounted `/config` volume
- **Windows**: Use WSL or manual installation

### **Integration not appearing**
1. Verify files were copied to `config/custom_components/balena_cloud/`
2. Restart Home Assistant completely (not just reload)
3. Check Home Assistant logs for errors

## Windows Users

For Windows users, we recommend:
1. **Use WSL (Windows Subsystem for Linux)** - Run the bash script in WSL
2. **Manual Installation** - Follow the detailed manual steps in [INSTALL_LOCAL.md](INSTALL_LOCAL.md)

## Manual Installation (If Script Fails)

If the automated script doesn't work, see [INSTALL_LOCAL.md](INSTALL_LOCAL.md) for detailed manual installation instructions.

## Need Help?

Run the script with `--help` for more information:
```bash
./install_local.sh --help
```

The script provides detailed error messages and suggestions when issues occur.