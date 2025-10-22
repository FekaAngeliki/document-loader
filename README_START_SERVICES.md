# 🚀 Starting Both Services from Same Terminal

## **Option 1: Use the Automated Script (Recommended)**

```bash
# Navigate to project directory
cd /mnt/c/Users/E41297/Documents/NBG/document-loader

# Run the start script
./start-services.sh
```

**What it does:**
- ✅ Starts web service on port 8080
- ✅ Starts dashboard server on port 4200
- ✅ Tests both services are working
- ✅ Shows all URLs and commands
- ✅ Handles Ctrl+C to stop both services cleanly

---

## **Option 2: Quick Start Script**

```bash
# Navigate to project directory
cd /mnt/c/Users/E41297/Documents/NBG/document-loader

# Run quick start
./start-quick.sh
```

**What it does:**
- ✅ Starts both services quickly
- ✅ Shows URLs to access
- ✅ Press Ctrl+C to stop both

---

## **Option 3: One-Line Commands**

### **Background Processes:**
```bash
cd /mnt/c/Users/E41297/Documents/NBG/document-loader && source .venv/bin/activate && cd web_service && python -m app.main & cd ../frontend && python3 -m http.server 4200 &
```

### **Using `&&` chaining:**
```bash
cd /mnt/c/Users/E41297/Documents/NBG/document-loader && source .venv/bin/activate && (cd web_service && python -m app.main &) && (cd frontend && python3 -m http.server 4200)
```

### **Using `screen` or `tmux`:**
```bash
# Install screen if not available
sudo apt update && sudo apt install screen -y

# Start with screen
screen -dm -S webservice bash -c 'cd /mnt/c/Users/E41297/Documents/NBG/document-loader/web_service && source ../.venv/bin/activate && python -m app.main'
screen -dm -S dashboard bash -c 'cd /mnt/c/Users/E41297/Documents/NBG/document-loader/frontend && python3 -m http.server 4200'

# View sessions
screen -ls

# Attach to session
screen -r webservice   # or dashboard
```

---

## **Option 4: Create Simple Aliases**

Add to your `~/.bashrc`:

```bash
# Add these lines to ~/.bashrc
alias start-document-loader='cd /mnt/c/Users/E41297/Documents/NBG/document-loader && ./start-services.sh'
alias start-dl-quick='cd /mnt/c/Users/E41297/Documents/NBG/document-loader && ./start-quick.sh'

# Reload bashrc
source ~/.bashrc

# Then just run:
start-document-loader
# or
start-dl-quick
```

---

## **Option 5: Using Process Substitution**

```bash
cd /mnt/c/Users/E41297/Documents/NBG/document-loader

# Start both and show output from both
source .venv/bin/activate && \
(cd web_service && python -m app.main 2>&1 | sed 's/^/[WEB] /' &) && \
(cd frontend && python3 -m http.server 4200 2>&1 | sed 's/^/[DASH] /' &) && \
wait
```

---

## **🎯 Recommended Approach:**

**Use the automated script:**
```bash
./start-services.sh
```

**Why it's best:**
- ✅ **Easy**: Single command
- ✅ **Safe**: Proper cleanup on exit
- ✅ **Informative**: Shows all URLs and status
- ✅ **Tested**: Verifies services are actually running
- ✅ **User-friendly**: Clear instructions and error handling

---

## **🔧 Troubleshooting:**

### **If script won't run:**
```bash
# Make executable
chmod +x start-services.sh start-quick.sh

# Run directly
bash start-services.sh
```

### **If ports are busy:**
```bash
# Check what's using the ports
sudo netstat -tulpn | grep :8080
sudo netstat -tulpn | grep :4200

# Kill processes on those ports
sudo fuser -k 8080/tcp
sudo fuser -k 4200/tcp
```

### **If virtual environment issues:**
```bash
# Recreate virtual environment
cd /mnt/c/Users/E41297/Documents/NBG/document-loader
python3 -m venv .venv
source .venv/bin/activate
uv sync
```

---

## **⚡ Quick Access URLs:**

Once services are running:

- **🏢 Main Dashboard:** http://localhost:4200/real-dashboard.html
- **🐛 Debug Dashboard:** http://localhost:4200/debug-dashboard.html  
- **🔌 API Health:** http://localhost:8080/health
- **📚 API Docs:** http://localhost:8080/docs
- **⚙️ Scheduler API:** http://localhost:8080/api/v1/scheduler/status

**🎯 The automated script is the easiest way - just run `./start-services.sh` and you're ready to go!**